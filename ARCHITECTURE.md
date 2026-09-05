# Repository architecture

```
007Tweak/
├── README.md                  overview, tools, mods, legal, credits
├── ARCHITECTURE.md            this file: layout, data flow, verified formats
├── LICENSE                    MIT (code and docs only)
├── .gitignore                 keeps third-party tools and everything derived from the game out of the repo
├── setup.py                   pip packages + vgmstream / wwiser / DepotDownloader from official releases -> external/
├── extract_menu_music.py      stems + menu soundbank from the installed game, launch bank reconstructed, FLAC renders
├── rebuild.py                 extract_menu_music.py, then every mods/*/build.py (patch, manifest, release zip)
├── filelist.txt               the two files DepotDownloader should fetch from an older build
├── docs/
│   └── DOWNLOAD_OLD_BUILD.md  tutorial: fetch an older build with DepotDownloader, diff it, listen to it
├── tools/                     ── the library (Python 3.12+, numpy, scipy, soundfile, lz4) ──
│   ├── rpkg_index.py          parse an RPKG v2 index (+ patch deletion list) to JSON, no extraction
│   ├── rpkg_read.py           read/decode one resource (XOR key + LZ4), FNV-1 hashing
│   ├── rpkg_extract.py        CLI: extract one resource by hash
│   ├── diff_rpkg.py           diff two chunk RPKGs: index level, then byte-exact for audio/UI types
│   ├── after_launch.py        build-vs-build diff that extracts changed sound resources and converts stems to WAV
│   ├── scan_wwev.py           dump every WWEV event name + FNV-1 id
│   ├── dump_wwev.py           dissect a WWEV: embedded and streamed .wem, resolve WWEM hashes
│   ├── wwev_list.py           compare the media lists of two versions of a WWEV
│   ├── hirc.py                minimal Wwise HIRC object walker
│   ├── bank_diff_files.py     HIRC object diff of two banks (added/removed/changed, hex payloads)
│   ├── make_patch.py          write an RPKG v2 patch from a folder of <hash>.<TYPE> + .meta
│   ├── pkgdef.py              packagedefinition.txt XTEA decrypt/encrypt (byte-exact round trip)
│   ├── render_music_timeline.py  offline Wwise music engine: segments/cues/clips/fades -> 24-bit FLAC per state & variant
│   └── media_map.json         menu-music wem id -> WWEM hash map (splash + theme stems)
├── mods/
│   └── launch-title-fanfare/  ── one folder per mod ──
│       ├── NEXUS_PAGE.md      user-facing description (install, uninstall, exact change table)
│       ├── RESEARCH_LOG.md    the complete investigation log (historical paths)
│       ├── restore_fanfare.py standalone audio-free builder (python3 + lz4): rebuilds the launch bank from the
│       │                      user's chunk0.rpkg, MD5-checked, writes chunk0patch1.rpkg
│       ├── build.py           build(runtime): patch + patchlevel=310 manifest + release zip (called by rebuild.py)
│       ├── chunk0patch1.rpkg  built patch (RPKG v2, one WBNK resource, raw)                    [committed]
│       ├── packagedefinition.txt  manifest with patchlevel=310                                  [committed]
│       ├── packagedefinition.txt.original  backup of the user's retail manifest                [ignored]
│       ├── images/            banner and thumbnail for the mod page
│       └── research/          wwiser XML dumps of launch + current bank (committed), the WBNKs   [WBNK ignored]
├── render/                    inputs of render_music_timeline.py
│   ├── banks/                 mx_mainmenu_current.bnk, mx_mainmenu_launch.bnk (+ wwiser .xml)   [ignored]
│   ├── wem/<decimal id>.wem   the 83 menu-music stems (identical in all builds so far)          [ignored]
│   └── wwnames.txt            names for wwiser
├── audio/renders/             FLAC output, one folder per bank version                          [ignored]
├── release/*.zip              Runtime/… layout for Nexus                                          [ignored]
├── external/                  third-party tools (setup.py)                                       [ignored]
│   ├── vgmstream/             vgmstream-cli
│   ├── wwiser/wwiser.pyz      wwiser
│   ├── DepotDownloader/       SteamRE DepotDownloader
│   └── rpkg-cli/              optional: RPKG-Tool CLI, first-light branch, only for its hash list
└── versions/                  one sub-folder per downloaded game build (DepotDownloader output)    [ignored]
    └── <label>_manifest_<id>/Runtime/chunk0.rpkg  (about 20 GB each)
```

## Data flow

1. **Find a change** – `rpkg_index.py` indexes an older and the current `chunk0.rpkg`; `diff_rpkg.py` /
   `after_launch.py` compare every WWEM/WWES/WWEV/WBNK/GFXV entry byte-exactly and extract what differs.
   For the title music the result was: only `mx_mainmenu` (WBNK `01980B15FE07DD81`) changed, no media did.
2. **Understand it** – `bank_diff_files.py` gives the changed HIRC objects; wwiser `-d xml` on both banks
   names the fields (playlist SegmentID, fBeginTrimOffset, clip automation FadeIn, Volume prop).
3. **Build** – a mod's builder (`restore_fanfare.py`) re-reads the *user's* bank, swaps the changed object
   payloads, verifies MD5s and writes the patch RPKG; `make_patch.py` is the generic equivalent. `pkgdef.py`
   produces the `patchlevel=310` manifest. `build.py` wraps that into the release zip.
4. **Listen** – `extract_menu_music.py` gathers stems and banks; `render_music_timeline.py` re-implements
   Wwise interactive-music playback offline (wwiser XML -> segment timeline with entry/exit cues, pre-entry and
   post-exit overlap, clip trims, fade automation, hierarchy volumes, per-stem resampling) and writes one FLAC
   per switch state and random variant. Plain wwiser+vgmstream TXTP rendering is not accurate for this bank: it
   hard-cuts at exit cues and layers 24 kHz stems into 48 kHz mixes without resampling (double speed).

## Formats (all verified on this game)

- **RPKG v2**: `"2KPR"`, 9 bytes `01 00 00 00 <chunkIdx> 00 <patchIdx> 78 78`, `u32 fileCount`,
  `u32 hashTableSize`, `u32 infoTableSize`, patch files: `u32 deletedCount + u64[]`; hash table entries
  `u64 hash, u64 dataOffset, u32 size|flags` (bit 31 = XOR-encrypted with `DC 45 A6 9C D3 72 4C AB`,
  low 30 bits = LZ4-block size, 0 = stored raw); info table entries `char[4] type (reversed),
  u32 refTableSize, u32 dataSize, u32 sysMem, u32 vidMem, [u32 count(low 30 bits), u8 flags[count], u64 hashes[count]]`.
  The engine derives table sizes from the count. The patch index in the sub-header must match the file name
  (`chunk0patch1.rpkg` -> chunk 0, patch 1) or the game crashes on launch. The game loads `chunkNpatchM.rpkg`
  for `M <= patchlevel`; a resource in a patch overrides the one in `chunkN.rpkg`. IOI itself ships no patch
  files; updates replace `chunkN.rpkg` wholesale.
- **Resource hash** = `"01" + MD5(IOI path)[2:16]`. **Wwise ids** = FNV-1 32-bit of the lowercase name.
- **WBNK** = `00 00` + `u32 bankLength` + standard Wwise `.bnk` (version 150, Wwise 2023.1).
- **WWEV** = `u32 nameLen, name\0, u8, f32 -1, u32, u32 nEmbedded, [u32 id, u32 id, u32 size, RIFF]…,
  u32 nStreamed, [u32 dependIdx, u32 id, u32 id, u32 prefetchSize, prefetch]…`; `dependIdx` indexes
  the resource's reference table and yields the WWEM hash.
- **HIRC v150 NodeBaseParams** (Sound after 18 bytes, containers after 4): `u8 fxOverride, u8 numFx,
  [fx…], u8, u8, u32 overrideBusId, u32 directParentId, …`.
- **Music**: a Music Switch container maps state ids (group `State_MX_MainMenu` = 3931772277; Splash 160038168,
  Landing 2548270042, Loading 3573931707, MainMenu 3604647259) to Random/Sequence containers or segments.
  Segments carry Entry (id 43573010) and Exit (1539036744) cue markers; the next segment's entry cue is placed
  at the previous one's exit cue, pre-entry and post-exit both audible. Clips: audible start = fPlayAt +
  fBeginTrimOffset, source offset = fBeginTrimOffset, length = fSrcDuration - fBeginTrimOffset + fEndTrimOffset.
- **packagedefinition.txt**: 16-byte header (retail: `b7e2ea00 545b6b87 11bd6fe8 4d6ad4bf`, keep verbatim) +
  `u32 CRC32` of the plaintext + XTEA (keys `71482CF0 5FDC4B9F 86CE569D 0509FC1E`, delta `61C88647`,
  32 rounds, zero-padded to 8). Partitions `super` and `base`, `patchlevel=0` retail, mods use 310.

## Reproducing from scratch

Fresh clone: `python setup.py`, then `python rebuild.py "<Runtime>"` (about one minute, verified byte-identical
to the published patch, manifest and renders). Step by step:

```
python extract_menu_music.py "<Runtime>"                       # stems, banks, FLAC renders
python mods/launch-title-fanfare/build.py "<Runtime>"          # patch + manifest + zip
python mods/launch-title-fanfare/restore_fanfare.py "<Runtime>"  # standalone: writes chunk0patch1.rpkg next to chunk0.rpkg
python tools/rpkg_index.py "<Runtime>/chunk0.rpkg" idx.json    # ~10 s
python tools/bank_diff_files.py mods/launch-title-fanfare/research/mx_mainmenu_launch_2026-05-27.WBNK mods/launch-title-fanfare/research/mx_mainmenu_current_since_1.0.x.WBNK full
```

## Comparing against another game build

See [docs/DOWNLOAD_OLD_BUILD.md](docs/DOWNLOAD_OLD_BUILD.md). In short:

```
external\DepotDownloader\DepotDownloader.exe -app 3768760 -depot 3768761 -manifest <MANIFEST_ID> -qr ^
    -filelist filelist.txt -dir versions\<label>_manifest_<MANIFEST_ID> -max-downloads 8
python tools\diff_rpkg.py versions\<label>_manifest_<MANIFEST_ID>\Runtime\chunk0.rpkg "<Runtime>\chunk0.rpkg"
python tools\after_launch.py versions\<label>_manifest_<MANIFEST_ID>\Runtime\chunk0.rpkg "<Runtime>\chunk0.rpkg" research_out
```

Manifest ids are listed on https://steamdb.info/depot/3768761/manifests/ (launch = 7322178669849310269,
2026-06-11 = 866138554611481703).

## Adding a mod

`mods/<name>/` with `build.py` exposing `build(runtime)` and a `NEXUS_PAGE.md`; keep the pattern of a small
standalone patcher that embeds only property values and reads the rest from the user's archive. Whatever the
build produces from the game (WBNK dumps, backups of the manifest) matches the ignore patterns `**/*.WBNK` and
`**/packagedefinition.txt.original*`; add new patterns for other derived data before committing.
