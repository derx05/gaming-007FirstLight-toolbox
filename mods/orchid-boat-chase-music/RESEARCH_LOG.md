# Research log – mission 9 boat chase music (2026-09-05/06)

Question: the boat chase with Isola late in the game used to have an orchestral cue; the current build plays a more
electronic one. Which update changed it, and can it be restored? All findings below were verified against the files.

## Inputs

- Installed game 1.1.x (`chunk0.rpkg` 20.7 GB, `chunk1.rpkg` 35.8 GB), launch build chunk0 (manifest
  7322178669849310269, 2026-05-27) in `versions/`. The launch **chunk1 was never downloaded** (36 GB), so the
  campaign music bank could not be diffed, only the media.
- Index dumps via `tools/rpkg_index.py` into `idx/` (ignored). chunk0: 285,091 files, 20 WBNK, 1,706 WWEV,
  11,872 WWEM. chunk1: 464,056 files, 82 WBNK, 4,959 WWEV, 9,906 WWEM.
- `external/rpkg-cli/hash_list.txt` (RPKG-Tool *first-light* branch) names the chunk0 banks
  (`global`, `main`, `sweet_templates`, …) and the two music events `mx_music_sw_play` (WWEV `01A872A294A76EAD`)
  and `mx_music_sw_stop`, but none of the 82 chunk1 banks.

## Step 1 – what changed in the audio between launch and current (chunk0)

`research/01_banks_and_music_event_diff.py`, byte-exact comparison of every WBNK, WWEV and WWEM:

| Type | Change |
|---|---|
| WBNK `014260B7C2E257A0` (`main`) | changed (TacSim gain fix + foley rework, known from the fanfare research) |
| WBNK `011D671F1430A124` (unnamed, 15 KB) | changed; SFX bank (111 CAkSound, 21 events, no music), every object re-exported. Not music. |
| WBNK `01980B15FE07DD81` (`mx_mainmenu`) | the title fanfare change (other mod) |
| WWEV `01A872A294A76EAD` (`mx_music_sw_play`) | 11,367,908 → 11,367,912 bytes: **one streamed entry differs** |
| WWEV `014DFBBC643C800D` (`mx_mainmenu_sw_play`) | same size, prefetch bytes differ (menu, other mod) |
| WWEM `0164B2AAA73D4801` | **removed** |
| WWEM `015E589FC5DD9B12` | **added** |

`MX_Music_SW_Play` has 0 embedded and 5,397 streamed stems. Media list launch vs current: identical except
source `3E5F24AC` (→ WWEM `0164B2AAA73D4801`, dependIdx 4266, prefetch 3,792 B) replaced by `236D6A95`
(→ WWEM `015E589FC5DD9B12`, same dependIdx, prefetch 3,796 B). The reference table slot 159 points to the new WWEM.
Both stems: Wwise Vorbis, 48 kHz stereo, 3,539,456 samples = 1:13.739 – a re-recording of the same cue.
The earlier fanfare research had already seen this swap between launch and the 2026-06-11 build and nothing in
the music media changed after 06-11, so the change is in **1.0.2 or 1.0.3** (1.0.3 = 2026-06-04 per SteamDB;
the patch notes themselves could not be fetched, all mirrors answer 403).

WAV renders for listening (ignored): `audio/renders/research_boat_chase/MX_Music_launch_3E5F24AC.wav` and
`…_current_236D6A95.wav`. The user confirmed launch = the orchestral version.

## Step 2 – where it is played

Searching all 102 banks for the 4-byte source ids: only chunk1 WBNK `015750D5211B2EAE` (2.1 MB, the campaign
music bank; contains no CAkEvent objects, the events live elsewhere) references `236D6A95`; no current bank
references `3E5F24AC` (`research/02_locate_track_in_bank.py`).

Object chain (wwiser XML of that bank): `CAkMusicTrack 24D28472` (sources 236D6A95 ×2, fSrcDuration 73738.67 ms,
no trim) ← `CAkMusicSegment 06C8404A` ← `CAkMusicRanSeqCntr 11CF0184` (playlist: one segment, loop) ←
`CAkMusicSwitchCntr 1A10CFAB` ← `17908951` ← `0EDE3B03` ← `0AC8C49D` (top).

Decision-tree path (`research/03_switch_chain.py`) and the names found by FNV-1 brute force
(`research/04_name_states_bruteforce.py`):

| Switch | Group id | Group name | State key → child | State name |
|---|---|---|---|---|
| `0AC8C49D` | 1571198769 | `State_MX_GameFlow` | 30729851 | `Campaign` (other: 1465331116 `Global`) |
| `0EDE3B03` | 1814311043 | ? (mission) | 3282568939 | `m09_orchid` |
| `17908951` | 1825805883 | ? (section, 11 states) | 3367804089 | unresolved |
| `1A10CFAB` | 2353839690 | ? | 2961386889 / default | unresolved (both leaves → 11CF0184) |

Mission states in the bank: `m01_clover`, `m02_lotus`, `m03_rose`, `m04_dahlia`, `m05_pepper`, `m06_bluebell`,
`m07_magnolia`, `m08_iris`, `m09_orchid`, `m10_ivy` (+ 11 unresolved ids). Isola's outfit assets are
`…/_maincast/isola/kits/kit_orchid/…`, i.e. mission 9 is her mission. Section names could not be brute-forced
(orchid-related tokens × ~150 words × prefixes; a wider pass over all 633k hash-list tokens only produced
32-bit collisions such as `sw_dth_burn_civfem09…`). They are not needed for the mod.

## Step 3 – how to restore it

Unlike the fanfare, no property change can bring the cue back: the old audio is gone from the current game.
Mechanism chosen (keeps the bank untouched, so no chunk1 patch and no risk from unseen bank changes):

- WWEM `015E589FC5DD9B12` (the resource the current bank's track resolves to) gets the launch stem bytes.
- WWEV `01A872A294A76EAD`: the streamed entry for `236D6A95` keeps its ids and dependIdx, only its prefetch
  (the first N bytes of the wem, verified `prefetch == wem[:N]` for both builds) is replaced by the launch stem's
  first 3,792 bytes. Result size 11,367,908 = the launch WWEV size.
- Both resources stored raw (flags 0) in `chunk0patch2.rpkg` (13.7 MB); sysMem/vidMem 0xFFFFFFFF as in the archive.

`build_from_launch.py` does this, checks the launch stem MD5 (`2089fbc97454c9ea279f7dd772d04c1f`) and reads the
patch back. **Tested in game 2026-09-06 together with chunk0patch1 (fanfare): works, orchestral cue plays.**
First multi-resource patch and first patch with an 11 MB uncompressed WWEV – no load-time problem observed.

## Dead ends and side findings

- Save games: Steam Cloud files `userdata/<id>/3768760/remote/KntSlotSaveFile-N/{data,index}.save`, 10–30 KB,
  encrypted (no strings, uniform entropy), plus `KntProfileSaveFile`, `LocalProfile`, `SystemData`. Not editable
  without reverse-engineering the cipher; the game's mission replay is the way to reach the chase.
- Patch notes: ioi.dk lists only 1.1.0/1.1.1 without content; steamdb.info and the Zendesk support pages return
  HTTP 403 to fetchers.
- `research/mx_music_sw_play_media_launch_vs_current.json`: full media lists (source id, WWEM hash) of both event
  versions, useful if another cue turns out to have changed in a later update.
