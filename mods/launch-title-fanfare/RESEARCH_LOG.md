# 007 First Light — restore the pre-1.1.0 boot/title fanfare (handoff brief)

> Historical document, kept as written during the investigation. Paths such as `mod/`, `docs/`, `older/`, `old/`,
> `cmp/` refer to the working folders of that time; the repository was restructured afterwards (see `ARCHITECTURE.md`).

Written 2026-09-05 during the first research session. Everything below was verified against the
user's files unless marked "unverified". Read fully before touching anything.

## Goal

1. Identify precisely what update 1.1.0 (2026-07-24) changed about the sound heard when the
   game opens / the title appears, and let the user *hear* old vs new.
2. Build a mod (patch RPKG) that restores the old sound, small enough to publish on Nexus Mods
   **without redistributing any IOI audio** — ideally only Wwise property values.
3. Nice-to-have: an as-heard render of the menu music for the user's archive.

Constraints: no game files or audio may ship inside the published mod
if avoidable; never run tools as admin; tools only from official sources (SteamRE, glacier-modding,
vgmstream, bnnm/wwiser); don't modify the game install except for the final patch file in
`Runtime\`. Steam login via DepotDownloader QR only.

## Environment (Windows 11, PowerShell 5.1 by default — see pitfalls)

| What | Where |
|---|---|
| Game install (current, post-1.1.x) | `D:\SteamLibrary\steamapps\common\007 First Light\Runtime\` — `chunk0.rpkg` 20,695,290,609 B, `chunk1.rpkg` 35,797,838,625 B, `packagedefinition.txt` 35,284 B (XTEA-encrypted like Hitman 3) |
| Old build (App 3768760, depot 3768761, manifest 866138554611481703, 2026-06-11) | `D:\007Tweak\old\Runtime\chunk0.rpkg` 20,670,313,608 B + `packagedefinition.txt`. Only chunk0 was downloaded. Full depot = 57 GB, 73 files, no patch RPKGs in any build (IOI replaces chunkN.rpkg wholesale). |
| DepotDownloader (official SteamRE) | `D:\007Tweak\dd\` — old manifests are NOT blocked by IOI (manifest request code is granted; CDN returns transient 503s, just retry) |
| RPKG-Tool, `first-light` branch CI build (GUI "RPKG V2.34.0" + rpkg-cli) | see glacier-modding/RPKG-Tool PR #103; the release builds crash on this game. Works: import, tree, search, raw extract, hash-list names (Game-Hashes repo). **Broken in this build:** Mass Extract → OGG for WWEM/WWEV (produces nothing, silently); model previews crash the GUI. |
| Raw extractions (RPKG-Tool) | `D:\007Tweak\cmp\old\{WBNK,WWEV}` and `D:\007Tweak\cmp\new\{WBNK,WWEV}` (all of each type, both builds); `D:\007Tweak\cmp2\old\chunk0\WWEM\` (ALL chunk0 WWEM, old build); `D:\007Tweak\cmp2\new\` (frontend TEMP/TBLU). Each file has a `.meta` sidecar. |
| vgmstream | `D:\007Tweak\vgmstream\vgmstream-cli.exe` (works on this game's .wem and unwrapped .bnk) |
| wwiser | `D:\007Tweak\wwiser\wwiser.pyz`, banks `mx_mainmenu.bnk`, `mx_ioisplash.bnk`, `main.bnk` (unwrapped), `wem\` (decimal-named clips), `txtp\`, `render\`. `wwnames.txt` present (first line may be BOM-corrupted). Python 3 installed. |
| Audio | `D:\007Tweak\audio\main_old.bnk`, `main_new.bnk` (unwrapped main bank, both builds); `D:\007Tweak\audio\menu\splash\` (6 clips) and `...\theme\` (83 clips) as `<hexWemId>.wem/.wav` |
| Scripts from the chat | `convert_menu_music.ps1` (raw WWEM → wav by hash list), `pick_menu_music.ps1` (only for OGG mass-extract output — not useful now), `hirc.py`/`graph.py` (bank HIRC parser + diff), `media_map.json` (wem id → RPKG hash for the two menu events) |

## Format knowledge (all verified on this game)

- **Resource hash** = `"01" + MD5(IOI path)[2:16]` (hex, upper). Verified on 3 named resources.
  The WWEM path convention is unknown (brute force of ~500 patterns failed) — but not needed,
  see WWEV depends below.
- **RPKG-Tool `.meta` sidecar**: `hash u64 @0, dataOffset u64 @8, size|flags u32 @16, type char[4] @20,
  refTableSize u32 @24, dataSize u32 @28, sysMem u32 @32, vidMem u32 @36`, then reference table
  @40: `count u32` (low 30 bits), `count` flag bytes (seen 1F/9F/5F), `count` u64 hashes.
- **WBNK** = 6-byte prefix (`00 00` + u32 LE length of the bank) + standard Wwise `.bnk`.
  Bank version 0x96 = 150 (Wwise 2023.1). `main` bank = BKHD + HIRC only (no DIDX/DATA);
  in-memory media live in WWEV resources, streamed media are WWEM.
- **WWEM** = bare `.wem` (RIFF at 0), Wwise Vorbis (fmt 0xFFFF), typically 24 kHz stereo,
  has a 16-byte `hash` chunk. vgmstream converts directly.
- **WWEV** (event resource): `u32 nameLen, name\0, u8 01, f32 -1.0, u32 0, u32 0, u32 nStreamed,
  u32 <?>`; then per streamed clip: `u32 dependIndex (into the .meta reference table), u32 wemId,
  u32 wemId, u32 prefetchSize, prefetch bytes (RIFF head ~800 B)` followed by 4 bytes
  `01 01 00 01`. Embedded in-memory clips appear as full RIFF blobs inside the resource
  (reveal event 014BA8E3D512D129 is 128 KB) — layout of the embedded-clip section is
  **unverified**. `dependIndex → .meta refs[]` gives the WWEM hash for each streamed wem.
- **Wwise IDs** = FNV-1 32-bit of the lowercase name (offset 2166136261, prime 16777619,
  multiply then XOR). Switch/state names are also FNV-1.
- **HIRC v150**: object = `u8 type, u32 size, payload(u32 id, ...)`. Sound (type 2) payload:
  `id u32, pluginId u32 (00040001 = Vorbis), streamType u8 (0 in-memory, 2 streamed), sourceId u32,
  inMemorySize u32, sourceBits u8`, then NodeBaseParams: `fxOverride u8, numFx u8, metaOverride u8,
  numFxMeta u8, attachOverride u8, overrideBusId u32, directParentId u32, bitvector u8,
  props: u8 count, u8 ids[count], f32 values[count]; ranged props: u8 count, ...; positioning u8;
  aux u8 + u32; adv: u8, u8, u16 maxInstances, u8, u8; state chunk; RTPC u16 count`.
  Prop IDs (v150 table): 0x00 Volume, 0x05 MakeUpGain, 0x06 Priority, 0x22 unknown (unchanged).

## Findings

### Archive diff, old (06-11) vs current
- WWEM, WWES: **identical** (counts and bytes). No new audio was shipped.
- WWEV: 4 added (`vfx_dst_*` destruction events), **0 changed**.
- WBNK: 2 changed — `011D671F1430A124` (`vehicles/veh_misc`, unrelated) and
  `014260B7C2E257A0` (`global/main`, 7,351,475 → 7,369,087 B).
- Frontend bricks `boot.brick` (TEMP 0157A4EF9F13604A / TBLU 016A2758866FC3AF) and
  `mainmenu.brick` (TEMP 01EBB458947C5621 / TBLU 01B45FE46F8BDEBB): same sizes both builds
  (hash-equality not verified).
- **Not yet compared:** GFXV (videos; `boot.brick` depends on 13 unnamed GFXV + a
  "menu_splashscreen_video_localized" template — the title card may be a video with audio),
  WSWB/WSWT/WSGB/WSGT (Wwise switch/state resources), global bricks.

### `main` bank HIRC diff (101,744 → 102,056 objects; 380 added / 68 removed / 9 changed)
Everything except one cluster is destruction/foley/TacSim rework. The interesting cluster:

- LayerCntr `0x3EE46395`, parent ActorMixer `0x3465E0FB` (the **UI** mixer subtree; siblings are
  `KNT_SFX_GUI_MainMenu_*`, pause menu, HUD, TacSim UI). Children:
  - Sound A `0x12ECCAA0`: Vorbis, in-memory, 364,000 B, media `0x36FEFA38` (dec 922,679,864)
  - Sound B `0x2D068E9A`: Vorbis, streamed, prefetch 649 B, media `0x0F3D39EF` (dec 255,670,767),
    override bus `0x95B34BCB` (not defined in main.bnk; probably the music bus)
- Triggered by Event `0x231B00B3` → Action `0x3653FE51` (type 0x0403 = Play). **Name unknown.**
- 1.1.0 changed only gain properties (exact bytes below):
  - Sound A: `{0x22: 0.52}` → `{0x05: -3.0, 0x22: 0.52}`
  - Sound B: `{0x00: -3.0, 0x06: 90}` → `{0x05: -1.0, 0x06: 90}`
  - Layer:   `{}` → `{0x05: -3.0}`
  - Net: A 0 → −6 dB, B −3 → −4 dB (B goes from 3 dB under A to 2 dB over A).

```
Sound 12ECCAA0
  OLD (54 B): A0 CA EC 12 01 00 04 00 00 38 FA FE 36 E0 8D 05 00 00 00 00 00 00 00 00 00 00 95 63 E4 3E 00 01 22 B8 1E 05 3F 00 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00
  NEW (59 B): A0 CA EC 12 01 00 04 00 00 38 FA FE 36 E0 8D 05 00 00 00 00 00 00 00 00 00 00 95 63 E4 3E 00 02 05 22 00 00 40 C0 B8 1E 05 3F 00 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00
Sound 2D068E9A
  OLD (59 B): 9A 8E 06 2D 01 00 04 00 02 EF 39 3D 0F 89 02 00 00 08 00 00 00 00 CB 4B B3 95 95 63 E4 3E 00 02 00 06 00 00 40 C0 00 00 B4 42 00 00 00 00 00 00 00 00 01 00 00 02 00 00 00 00 00
  NEW (59 B): 9A 8E 06 2D 01 00 04 00 02 EF 39 3D 0F 89 02 00 00 08 00 00 00 00 CB 4B B3 95 95 63 E4 3E 00 02 05 06 00 00 80 BF 00 00 B4 42 00 00 00 00 00 00 00 00 01 00 00 02 00 00 00 00 00
LayerCntr 3EE46395
  OLD (52 B): 95 63 E4 3E 00 00 00 00 00 00 00 00 FB E0 65 34 00 00 00 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00 02 00 00 00 A0 CA EC 12 9A 8E 06 2D 00 00 00 00 00
  NEW (57 B): 95 63 E4 3E 00 00 00 00 00 00 00 00 FB E0 65 34 00 01 05 00 00 40 C0 00 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00 02 00 00 00 A0 CA EC 12 9A 8E 06 2D 00 00 00 00 00
```

Other changed objects (considered unrelated): RanSeqCntr `0x34B3E967` (+children, event
`0x5568B80E`), RanSeqCntr `0x0F9E234B` (max instances 1→3), LayerCntr `0x3D980D03` (event
`0x4472FDBA`) and `0x39492C8D` (event `0xD6E009E8`) restructured, ActorMixers `0x3066ECD0`,
`0x06317153` (+children).

### Known names / IDs
- `KNT_SFX_GUI_MainMenu_RevealMainMenu_Play` = `0x015A2090`, WWEV `014BA8E3D512D129` (128 KB,
  unchanged) → LayerCntr `0x2D197886` (unchanged).
- `MX_MainMenu_Splash_Play` = `0x9EC7CD2C`, WWEV `01A96084046CCA22` → 6 streamed WWEM.
  `MX_MainMenu_SW_Play` = `0x85AAC0AD`, WWEV `014DFBBC643C800D` → 83 streamed WWEM
  (full map in `media_map.json`). Defined in `mx_mainmenu` (WBNK `01980B15FE07DD81`, 19 KB,
  unchanged) and `mx_ioisplash` (WBNK `01B8DBE7301DB1C7`, 8 KB, unchanged).
- Menu-music switch group `3931772277` (0xEA5A1BB5), states seen: 160038168, **2548270042**
  (this one plays at the title), 3573931707, 3604647259 {random}. Title clip = media
  `0x32140230` (dec 840,172,080) = WWEM `0191ED7192536723`, 550,608 B.
- chunk0 contains 1,706 WWEV; their names (from the raw files) do NOT include `0x231B00B3` or
  the other three changed-cluster events. chunk1 WWEV were not scanned.
- `boot.brick` TEMP depends include: MX_MainMenu_Splash_Play/Stop, `mx_ioisplash` WBNK,
  GFXF `01A837AF55107DEC` (knt.menu.swf), XMLB `0193EEA681A0387F` (bootsplash_page.layout.xml),
  13 unnamed GFXV, TEMP `0195275B8B98382B` (gameessentials.brick). `mainmenu.brick` depends include
  XMLB `011C04A767C36A35` (boot_page), `0185AA7FDB3E122B` (mainmenupage), GFXV
  `019BB41A56C2F47E` (01_againsttheodds.usm), no WWEV at all → UI sounds are triggered by name
  from the UI, not by scene entities.
- Reverse depend of both bricks: `0111027A324FDB81` TEMP (global_streaming.brick).

### User's listening results
- The 6 splash stems = ambient bed under the studio logos. Switch state 2548270042 of
  `MX_MainMenu_SW_Play` = the sound when the title appears — and it sounds like the **new**
  version. No music render contains the "old" notes. Since all music data is identical between
  builds, the working hypothesis is: the old character came from the UI sting (`0x231B00B3`)
  mixed on top at the old gains; the new mix drops it 6 dB and flips layer dominance.

## Open tasks, in order

1. **Name event `0x231B00B3`.**
   DONE / negative: the four UI resources (GFXF `01A837AF55107DEC` = knt.menu.swf, XMLB
   `0193EEA681A0387F` bootsplash_page.layout.xml, `011C04A767C36A35` boot_page.layout.xml,
   `0185AA7FDB3E122B` mainmenupage.layout.xml) contain NO Wwise event names at all — not even
   the known reveal event. XMLB files are plain-text XML ("bechaml"). The SWF has only a
   generic `PlaySound` hook; names come from data elsewhere.
   Next candidates, in order:
   (a) the page *behaviour scripts*: `menusystem/Aurora/Pages/BootSplash/BootSplash_Page.bs.xml`
       (hash unknown — search "bootsplash" in the GUI), `mainmenupage.bs.xml` = XMLB
       `016FFBDA65DDDCA3`, `popups.bs.xml` `01CE21F2F2C72517`, and the `menusystem/functions/*.xml`
       modules they import; also JSON/ORES resources that could hold a UI-sound map.
   (b) parse the chunk1 RPKG index directly (don't mass-extract 35 GB) and read the name at the
       start of every WWEV; FNV-1 each against 0x231B00B3.
   (c) depends of gameessentials.brick `0195275B8B98382B` / global_streaming.brick
       `0111027A324FDB81` (GUI Details pane resolves names).
   Also check WSWB/WSWT/WSGB/WSGT and global-brick TEMPs for changes between builds.
2. **Get the sting's WWEV** (chunk1?) → embedded layer A (`0x36FEFA38`) + prefetch/depend index
   for layer B (`0x0F3D39EF`) → WWEM hash → convert both with vgmstream → render old mix
   (A 0 dB, B −3 dB) and new mix (A −6, B −4) over the title clip. User confirms by ear.
3. **GFXV diff** old vs current chunk0 (hash compare) to exclude a video-audio change.
4. If confirmed: build patched `main` bank = current bank with the three objects' property
   bundles restored to OLD bytes (recompute object sizes, HIRC chunk size, re-add the 6-byte
   wrapper with new length), pack as `chunk0patchN.rpkg` via rpkg-cli/RPKG-Tool "Generate",
   handle `packagedefinition.txt` patch level the way existing Nexus 007 mods / FLMM do, test
   in game. Result contains no audio.
5. If NOT confirmed: the user's memory may predate 06-11 → diff against the launch manifest
   (2026-05-27) from SteamDB (another 20 GB chunk0), same procedure.

## PowerShell 5.1 pitfalls hit so far
- `Format-Hex` has no `-Count`; use `Get-Content -Encoding Byte -TotalCount N`.
- `0xFFFFFFFF` literal parses as Int32 −1; uint64 arithmetic silently promotes to Double —
  do hashing in Python, not PowerShell.
- Array slicing of MB-sized byte arrays is very slow; use FileStream.CopyTo with `Position`.
- Scripts need `Set-ExecutionPolicy -Scope Process Bypass`.

---

# Session 2 — 2026-09-05 (Claude Code, autonomous). Read this before the sections above.

## Headline

**The changed cluster in `main.bnk` (event `0x231B00B3`) is NOT the title sound.** It is
`UI_HUD_TSIM_MissionEnd_Complete_OS_Play` — the TacSim mission-complete jingle — and the 1.1.0
patch notes say verbatim: *"Fixed TacSim mission completion SFX being excessively loud."*
That explains the −6 dB / −4 dB gain change completely. The whole UI mixer subtree `0x3465E0FB`
is TacSim HUD (MissionStart, CombatCounter, FewEnemiesLeft, OutfitSelector).

**Between the 06-11 build and the current build nothing that feeds the boot/title audio changed:**
- WWEM, WWES: byte-identical (raw compressed bytes compared, all entries).
- WBNK: only `main` (the TacSim gain change + destruction/foley rework) and `veh_misc`.
  The Wwise **Init bank is `01E4E9C791AD95E2` = global.wwisesoundbank** (has STMG/INIT/ENVS) and
  is byte-identical → bus structure/volumes unchanged. `mx_mainmenu`, `mx_ioisplash` identical.
- WWEV: 4 added (`vfx_dst_*`), 0 changed. WSWB/WSWT/WSGB/WSGT: identical.
- GFXV: all 144 identical. The 13 boot videos are CRID/USM with **video only (no @SFA audio)**;
  `01_againsttheodds.usm` (menu background) also video-only. Only `black_loading_slate_01.usm` has audio.
- `boot.brick`, `mainmenu.brick` TEMP/TBLU: byte-identical.
- 73 XMLB + 70 UICB + knt.menu.swf changed — all of it is the **"large text size" accessibility
  mode** (bootsplash layout: `style.width` → `isLargeTextSizeModeEnabled() ? 1080 : 688`; SWF diff
  strings: TEXT_SIZE_MODE_*, SetTextSizeMode…). No `triggerUISoundEvent` change anywhere.
  No sound tags in the SWF (Scaleform GFX, uncompressed at offset 84 of the GFXF).
- ORES `config.blobs`: only new TacSim challenge images + `blobcachedb/1_1_1_0.cachedb`.
- `gameessentials.brick` TEMP: +136 B, no reference changes (not decoded — rpkg-cli QN and
  RT-JSON export both produce no output for this game). `global_streaming.brick`: gameplay
  markers/opportunities only.
- Exe: 06-11 manifest lists `Retail\007FirstLight.exe` at 323,373,448 B; current is 64,235,912 B.
  Can't diff, but the engine/Wwise runtime does not change which notes play.

**Timeline (from patch notes):** launch 2026-05-27, 1.0.2 06-02, 1.0.3 06-04, our "old" chunk0
06-11 (post-1.0.3), 1.1.0 07-24, then 1.1.x. So if the fanfare memory is real, the change is in
**1.0.2 or 1.0.3 (or launch → 1.0.2)**, and the launch manifest (05-27) is the build to compare.

## What the user should do next
1. Listen to `audio\tsim\compare_old_then_new.wav` (TacSim sting, old mix then new mix) — just to
   rule it out by ear.
2. Look up the **launch manifest ID** for depot 3768761 on
   https://steamdb.info/depot/3768761/manifests/ (SteamDB blocks non-browser fetches).
3. Download only chunk0 of that manifest (QR login, ~20 GB):
   ```
   dd\DepotDownloader.exe -app 3768760 -depot 3768761 -manifest <LAUNCH_MANIFEST_ID> -qr -filelist filelist.txt -dir D:\007Tweak\launch -max-downloads 8
   ```
   then `python tools\diff_rpkg.py D:\007Tweak\launch\Runtime\chunk0.rpkg D:\007Tweak\old\Runtime\chunk0.rpkg idx\diff_launch_vs_0611.json`
   — it prints every WWEM/WWES/WWEV/WBNK/GFXV/… that differs (index level, then byte-exact).
4. If WBNK `mx_mainmenu`/`mx_ioisplash`/`global` or any WWEM in the menu media map differ, extract
   both versions with `tools\rpkg_read.py` (see `dump_wwev.py` for usage) and render with vgmstream.

## New tools (D:\007Tweak\tools\, Python 3.14 + `lz4` + numpy)
- `rpkg_index.py <rpkg> <out.json>` — parses a 2KPR index in ~10 s without extracting. Indexes for
  old chunk0, new chunk0, new chunk1 are in `idx\*.json`.
- `rpkg_read.py` — `load_index`, `read_resource(f, entry)` (XOR key DC45A69CD3724CAB + LZ4 block),
  `fnv1(name)`. Self-test verified byte-exact against RPKG-Tool output.
- `diff_index.py` / `diff_rpkg.py` — old-vs-new diff with byte-exact compare of chosen types.
- `scan_wwev.py` → `idx\wwev_names_all.txt`: **all 6,665 WWEV names of chunk0+chunk1** with FNV-1
  ids (tab-separated: chunk, hash, size, fnv1, name, media-hit). Use it to name any bank event.
- `bank_diff_named.py` — main.bnk diff with parent chains and event names (fixed v150 offsets:
  NodeBaseParams = fxOverride u8, numFx u8, [fx…], 2 more u8, overrideBusId u32, directParentId u32;
  i.e. **4** bytes before the bus id, not 5 as written above).
- `dump_wwev.py <hash> <outdir>` — dissects a WWEV and dumps embedded + streamed wems.
  **Corrected WWEV layout:** `u32 nameLen, name\0, u8, f32 -1.0, u32 nA(0), u32 nEmbedded,
  [u32 id, u32 id, u32 size, RIFF…]×nEmbedded, u32 nStreamed, [u32 dependIdx, u32 id, u32 id,
  u32 prefetchSize, prefetch]×nStreamed`.
- `mix.py` — gain-mix renderer (numpy); `swf_diff.py`, `gfxf_check.py`, `anchored_diff.py`, `names.py`.
- Extractions: `cmp3\{old,new}\XMLB` (74 changed XMLB, plain text), `cmp3\{old,new}\ALLTXT`
  (all XMLB/JSON/ORES of chunk0 both builds), `cmp3\{old,new}\GFXF` (knt.menu.swf),
  `cmp3\{old,new}\TEMP` (gameessentials, global_streaming), `audio\tsim\` (sting wems/wavs/mixes).
- `dd\` had lost its DepotDownloader binary; re-downloaded from the official SteamRE release.

## Pitfalls added
- Python `difflib.SequenceMatcher` on MB-sized byte strings never finishes — use `anchored_diff.py`.
- `subprocess` needs an absolute Windows path for `vgmstream-cli.exe`.
- rpkg-cli `-extract_entity_to_qn` and `-extract_to_rt_json -version HM3` run without error but
  write nothing for this game's TEMP/TBLU.
- steamdb.info returns 403 to non-browser fetchers; ioi.dk patch-notes pages fetch fine.

## User clarification (2026-09-05, after session 2 report)
- The changed sound is specifically the **title clip** `audio\menu\theme\32140230.wav`
  (WWEM `0191ED7192536723`, media 0x32140230, switch state 2548270042 of `MX_MainMenu_SW_Play`):
  the loud opening horn used to be a **fast triple note** instead of the Bond-like fanfare.
- The TacSim gain change is irrelevant (confirmed by user).
- User is downloading the **launch manifest 7322178669849310269** (2026-05-27) chunk0 into
  `D:\007Tweak\older\Runtime\`. When it lands, run `python tools\after_launch.py` — diffs launch vs 06-11
  for all audio types, extracts changed WWEM/WBNK/WWEV to `audio\launch\` and converts wems to wav.

## BREAKTHROUGH (2026-09-05, launch build 7322178669849310269 in `older\Runtime`)
Launch (05-27) vs 06-11 chunk0, audio types: WWEM/WWES identical except one in-game music stem swap
(`MX_Music_SW_Play`: wem 3E5F24AC → 236D6A95, unrelated). **`mx_mainmenu` WBNK `01980B15FE07DD81`
changed**, and it is byte-identical from 06-11 through today, so the title change happened in 1.0.2/1.0.3.
Exact changes (wwiser XML diff, `wwiser\launch` vs `wwiser\b0611`):
- MusicRanSeqCntr `0x19EA31A3` playlist: SegmentID 978446613 (0x3A51E915) → 744897837 (0x2C663D2D).
- MusicTrack `0x0BC0A5DA` (src 0x136A5556): fBeginTrimOffset 3230.77 ms → 12923.08 ms, + FadeIn 3.75 s.
- MusicTrack `0x21BB990C` (src 0x0E85E12E): fBeginTrimOffset 3230.77 ms → 11076.92 ms, + FadeIn 5.37 s.
- MusicTrack `0x21E1267C` (src 0x0E1285C8): + Volume prop +5 dB.
- BKHD: only the 16-byte bank hash differs.
The title clip media is unchanged; the old opening (fast triple horn) is the first ~10 s of the stems
that 1.0.x now trims away. Launch render: `wwiser\launch\render\MX_MainMenu_SW_Play (3931772277=2548270042).wav`.

### Mod (audio-free)
- `mod\restore_fanfare.py <Runtime dir>` — standalone, needs `pip install lz4`. Reads the user's own
  chunk0.rpkg, rebuilds the bank with the launch BKHD + 4 object payloads (property values only, embedded
  as hex), verifies md5 (current 6ca50654…, patched d5ccca44…), writes RPKG v2 `chunk0patch1.rpkg`
  (LZ4+XOR, header mirrors chunk0, empty deletion list). Verified: output bank == launch bank bytes.
- `tools\make_patch.py <folder> <out.rpkg>` — generic RPKG v2 writer (RPKG-Tool folder layout).
  Note: rpkg-cli `-generate_rpkg_from` produces RPKG **v1 (GKPR)**; the game ships v2 (2KPR).
- `packagedefinition.txt` (XTEA; decrypt/encrypt with rpkg-cli, `-output_path` required) has
  `patchlevel=0` on partitions `super` and `base` in all builds → patches are NOT loaded until raised.
  `mod\pd\packagedefinition.txt.encrypted` = current file with patchlevel=10000 on both (CRLF preserved,
  round-trip verified). rpkg-cli's decrypt of the launch/06-11/current files: all three identical.
- In-game test still pending.

### Install / test (staged in `mod\`, not yet copied into the game — the session's sandbox blocked writes there)
- `mod\chunk0patch1.rpkg` — RPKG v2 patch with the restored launch bank (built by `restore_fanfare.py`).
- `packagedefinition.txt` is XTEA with **First-Light-specific keys** {0x71482CF0,0x5FDC4B9F,0x86CE569D,0x0509FC1E},
  delta 0x61C88647 (RPKG-Tool first-light branch `src/crypto.cpp`); layout = 16-byte header (game's own
  header `b7e2ea00…`, NOT rpkg-cli's `223d6f9a…`) + CRC32(plaintext) + XTEA blocks. `tools\pkgdef.py`
  round-trips the game file byte-exactly.
- Two candidate manifests, both verified round-trip: `mod\pd\packagedefinition_B_patchlevel.txt`
  (patchlevel=10000 on partitions super+base, Hitman-style) and `mod\pd\packagedefinition_A_include.txt`
  (appends `@include chunk0patch1`, the mechanism FLMM uses — but FLMM's code targets the Hitman header,
  so it is unverified on this build). Original backed up as `mod\pd\packagedefinition_ORIGINAL_backup.txt`.
- Test: copy `chunk0patch1.rpkg` + variant B (renamed `packagedefinition.txt`) into `Runtime\`, start game,
  listen at the title. If unchanged, try variant A. Revert = put the ORIGINAL_backup back and delete the patch.

### First in-game test (user): CRASH ON LAUNCH with v2 patch (old header) + patchlevel=10000. Fixes applied:
- Reference: Nexus "Skip Intro" mod (`cmp3\refmod\skipintro\Runtime\`, chunk0patch203.rpkg + packagedefinition.txt).
  Its manifest = the game's file with **patchlevel=310** on `super` and `base`, same XTEA header/keys → our codec is right.
  Its RPKG sub-header is `01 00 00 00 00 00 CB 78 78`: **byte 8 = chunk index, byte 10 = patch number (0xCB=203)**.
  IOI's chunk1.rpkg has byte 8 = 01. My first patch had 00 there → mismatch with the file name, probable crash cause.
  Reference stores GFXV raw (flags 0) and XMLB LZ4+XOR, so both storage modes are accepted; its table-size
  header fields are bogus (0x14000) yet it loads, so the engine derives them from the count.
- Rebuilt: `mod\chunk0patch1.rpkg` (sub-header `…00 00 01 78 78`, raw storage, verified bank == launch) and
  `mod\pd\packagedefinition_B310_patchlevel.txt` (plaintext identical to the Skip-Intro manifest). `restore_fanfare.py`
  and `tools\make_patch.py` updated accordingly (make_patch derives chunk/patch numbers from the output file name).
- User confirmed the launch render `wwiser\launch\render\…2548270042.wav` IS the remembered fanfare (wwiser's
  other renders overlap all layers/variants, which is expected and not a bug).

## Renders (2026-09-05, later)
- State names by FNV-1 brute force: group `State_MX_MainMenu` (3931772277); 160038168 `Splash`, 2548270042 `Landing`
  (= title fanfare), 3573931707 `Loading`, 3604647259 `MainMenu` (step-random of 3 segments).
- wwiser TXTP renders were judged wrong by ear: hard cut at ~10 s (segment trimmed at exit cue, no pre-entry/
  post-exit overlap) and "too fast" (vgmstream layers 24/32/36 kHz stems into a 48 kHz mix without resampling).
- `tools/render_music_timeline.py` replaces them: full playlist expansion (ContinuousSequence/StepSequence/
  StepRandom, loops), segment scheduling at cues, clip math per wwiser (`audible start = fPlayAt + fBeginTrim`,
  source offset = fBeginTrim, length = fSrcDuration − fBeginTrim + fEndTrim), FadeIn/FadeOut clip automation
  with AkCurveInterpolation shapes, Volume+MakeUpGain along DirectParentID chain, resample_poly to 48 kHz,
  one global gain so relative levels between states survive. `mx_ioisplash.bnk` duplicates the same music
  switch (Splash state) – its Play action just adds a 2 s fade-in – so it is not rendered separately.
