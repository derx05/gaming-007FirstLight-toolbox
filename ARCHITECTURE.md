# Repository architecture

```
007Tweak/
├── README.md                  what the mod does, install, technical summary
├── ARCHITECTURE.md            this file
├── .gitignore                 keeps tools and game-derived data out of the repo
├── setup.py                   downloads vgmstream / wwiser / DepotDownloader into external/, pip installs packages
├── rebuild.py                 regenerates every ignored artefact from the installed game (stems, banks, patch, zip, renders)
├── mod/                       ── the release ──
│   ├── restore_fanfare.py     standalone, audio-free builder (needs python3 + lz4)
│   ├── chunk0patch1.rpkg      built patch (RPKG v2, one WBNK resource, raw)          [ignored]
│   └── packagedefinition.txt  game manifest with patchlevel=310 (XTEA-encrypted)     [ignored]
├── release/
│   └── 007FirstLight_LaunchTitleFanfare_v1.0.zip   Runtime/… layout for Nexus         [ignored]
├── tools/                     ── research & build scripts (Python 3.12+, numpy, lz4, soundfile) ──
│   ├── rpkg_index.py          parse an RPKG v2 index (+ patch deletion list) to JSON, no extraction
│   ├── rpkg_read.py           read/decode one resource (XOR key + LZ4), FNV-1 hashing
│   ├── diff_rpkg.py           diff two chunk RPKGs: index level, then byte-exact for audio/UI types
│   ├── after_launch.py        the launch-vs-June diff that found the bank change (expects older/, old/)
│   ├── scan_wwev.py           dump every WWEV event name + FNV-1 id (names bank events)
│   ├── dump_wwev.py           dissect a WWEV: embedded and streamed .wem, resolve WWEM hashes
│   ├── wwev_list.py           compare the media lists of two versions of a WWEV
│   ├── hirc.py                minimal Wwise HIRC object walker (from the first session)
│   ├── bank_diff_files.py     HIRC object diff of two banks (added/removed/changed, hex payloads)
│   ├── make_patch.py          write an RPKG v2 patch from a folder of <hash>.<TYPE> + .meta
│   ├── pkgdef.py              packagedefinition.txt XTEA decrypt/encrypt (byte-exact round trip)
│   ├── render_music_timeline.py  offline Wwise music engine: segments/cues/clips/fades → 24-bit FLAC per state & variant
│   └── media_map.json         menu-music wem id → WWEM hash map (splash + theme stems)
├── render/                    inputs for render_music_timeline.py
│   ├── banks/                 mx_mainmenu_launch.bnk, mx_mainmenu_current.bnk, mx_ioisplash.bnk  [ignored]
│   ├── wem/<decimal id>.wem   the 83 menu-music stems (identical in all builds)                 [ignored]
│   └── wwnames.txt            names for wwiser
├── audio/renders/             FLAC output, one folder per bank version                          [ignored]
├── research/
│   ├── banks/                 launch + current mx_mainmenu WBNK and their wwiser XML dumps
│   └── packagedefinition.txt.original_1.1.x   untouched retail manifest                          [ignored]
├── docs/RESEARCH_LOG.md       the complete investigation log (two sessions), formats, dead ends
├── external/                  third-party tools, not part of the repo                            [ignored]
│   ├── rpkg-cli/              RPKG-Tool CLI, first-light branch CI build (+ 342 MB hash_list.txt)
│   ├── vgmstream/             vgmstream-cli r2117
│   ├── wwiser/wwiser.pyz      wwiser v20260808
│   └── DepotDownloader/       SteamRE DepotDownloader 3.4.0
└── versions/                  one sub-folder per downloaded game build (DepotDownloader output)    [ignored]
    └── launch_2026-05-27_manifest_7322178669849310269/Runtime/chunk0.rpkg  (20 GB)
```

## Data flow

1. **Find the change** – `rpkg_index.py` indexes launch and current `chunk0.rpkg`; `diff_rpkg.py` /
   `after_launch.py` compare every WWEM/WWES/WWEV/WBNK/GFXV entry byte-exactly and extract what differs.
   Result: only `mx_mainmenu` (WBNK `01980B15FE07DD81`) matters for the title music.
2. **Understand it** – `bank_diff_files.py` gives the changed HIRC objects; wwiser `-d xml` on both banks
   names the fields (playlist SegmentID, fBeginTrimOffset, clip automation FadeIn, Volume prop).
3. **Build** – `restore_fanfare.py` re-reads the *user's* bank, swaps the BKHD and the four object
   payloads, verifies MD5s and writes the patch RPKG. `make_patch.py` is the generic equivalent.
   `pkgdef.py` produces the `patchlevel=310` manifest.
4. **Listen** – `render_music_timeline.py` re-implements Wwise interactive-music playback offline (wwiser XML →
   segment timeline with entry/exit cues, pre-entry/post-exit overlap, clip trims, fade automation, hierarchy
   volumes, per-stem resampling) and writes one FLAC per switch state and random variant, launch and current.
   Plain wwiser+vgmstream TXTP rendering is not accurate here: it hard-cuts at exit cues and layers 24 kHz stems
   into 48 kHz mixes without resampling (double speed).

## Formats (all verified on this game)

- **RPKG v2**: `"2KPR"`, 9 bytes `01 00 00 00 <chunkIdx> 00 <patchIdx> 78 78`, `u32 fileCount`,
  `u32 hashTableSize`, `u32 infoTableSize`, patch files: `u32 deletedCount + u64[]`; hash table entries
  `u64 hash, u64 dataOffset, u32 size|flags` (bit 31 = XOR-encrypted with `DC 45 A6 9C D3 72 4C AB`,
  low 30 bits = LZ4-block size, 0 = stored raw); info table entries `char[4] type (reversed),
  u32 refTableSize, u32 dataSize, u32 sysMem, u32 vidMem, [u32 count(low 30 bits), u8 flags[count], u64 hashes[count]]`.
  The engine derives table sizes from the count (a working community patch has bogus size fields).
- **Resource hash** = `"01" + MD5(IOI path)[2:16]`. **Wwise ids** = FNV-1 32-bit of the lowercase name.
- **WBNK** = `00 00` + `u32 bankLength` + standard Wwise `.bnk` (version 150).
- **WWEV** = `u32 nameLen, name\0, u8, f32 -1, u32, u32 nEmbedded, [u32 id, u32 id, u32 size, RIFF]…,
  u32 nStreamed, [u32 dependIdx, u32 id, u32 id, u32 prefetchSize, prefetch]…`; `dependIdx` indexes
  the resource's reference table and yields the WWEM hash.
- **HIRC v150 NodeBaseParams** (Sound after 18 bytes, containers after 4): `u8 fxOverride, u8 numFx,
  [fx…], u8, u8, u32 overrideBusId, u32 directParentId, …`.
- **packagedefinition.txt**: 16-byte header (retail: `b7e2ea00 545b6b87 11bd6fe8 4d6ad4bf`) + `u32 CRC32`
  of the plaintext + XTEA (keys `71482CF0 5FDC4B9F 86CE569D 0509FC1E`, delta `61C88647`, 32 rounds,
  zero-padded to 8). Partitions `super` and `base`, `patchlevel=0` retail.

## Reproducing from scratch

Fresh clone: `python setup.py` then `python rebuild.py "<Runtime>"` (≈1 min, verified byte-identical). Manually:

```
python tools/rpkg_index.py "<Runtime>/chunk0.rpkg" idx/new_chunk0.json         # ~10 s
python tools/diff_rpkg.py versions/<build>/Runtime/chunk0.rpkg "<Runtime>/chunk0.rpkg"    # what changed
python tools/bank_diff_files.py research/banks/mx_mainmenu_launch_2026-05-27.WBNK research/banks/mx_mainmenu_current_since_1.0.x.WBNK full
python mod/restore_fanfare.py "<Runtime>"                                        # build the patch
python tools/render_music_timeline.py                                            # FLAC renders
```

## Adding another game build for comparison

```
external\DepotDownloader\DepotDownloader.exe -app 3768760 -depot 3768761 -manifest <MANIFEST_ID> -qr ^
    -filelist filelist.txt -dir versions\<label>_manifest_<MANIFEST_ID> -max-downloads 8
python tools\after_launch.py versions\<label>_manifest_<MANIFEST_ID>\Runtime\chunk0.rpkg "<Runtime>\chunk0.rpkg" research\extracted
```
`filelist.txt` contains the two lines `Runtime\chunk0.rpkg` and `Runtime\packagedefinition.txt`. Manifest ids
are listed on https://steamdb.info/depot/3768761/manifests/ (launch = 7322178669849310269, 2026-06-11 = 866138554611481703).
