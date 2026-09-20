# 007 First Light – Launch Boat Chase Music Restored (mission 9)

Brings back the orchestral music of the boat chase in mission 9 (the mission with Isola) exactly as it played in
the launch build of *007 First Light* (2026-05-27). Update 1.0.2/1.0.3 (early June 2026) swapped that cue for a
new, more electronic recording of the same length. This mod puts the launch recording back.

Tested on the current Steam build (1.1.x, September 2026) by several players, together with the
*Launch Title Fanfare* mod. **No audio is included in the download** – read on for why and how.

## Why you build this one yourself

The old recording no longer exists in the current game files, and it is IO Interactive's music, so it cannot be
uploaded here. Steam, however, still lets you download the launch build of a game you own. The download is a
small build kit: a Python script pulls the original cue out of that launch build and writes the patch for you.
Cost: one 20 GB download and about ten minutes.

## Requirements

- 007 First Light on Steam (the launch build is fetched with your own account)
- Windows, Python 3.12+ from python.org, and once in a terminal: `pip install lz4`
- [DepotDownloader](https://github.com/SteamRE/DepotDownloader/releases) (open source, SteamRE)
- 20 GB of free disk space while building

## Build and install

1. Unzip the build kit into a folder. Unzip DepotDownloader into the same folder.
2. Open a terminal in that folder and download the launch build's `chunk0.rpkg`. A QR code appears; scan it
   with the Steam mobile app to log in (your password never touches the tool):
   ```
   DepotDownloader.exe -app 3768760 -depot 3768761 -manifest 7322178669849310269 -qr -filelist filelist.txt -dir launch -max-downloads 8
   ```
   HTTP 503 errors from Steam's CDN are transient. Run the same command again, it resumes.
3. Build the patch (adjust the game path):
   ```
   python build_from_launch.py launch\Runtime\chunk0.rpkg "D:\SteamLibrary\steamapps\common\007 First Light\Runtime"
   ```
   The script checks the MD5 of the original cue, writes `chunk0patch2.rpkg` (13 MB) next to itself and reads it
   back to verify it. If you have **no other mod installed yet**, add `--manifest` at the end: you also get a
   `packagedefinition.txt` with `patchlevel=310`, which every patch mod needs (the retail file has `patchlevel=0`
   and ignores all `chunkNpatchM.rpkg` files).
4. Copy `chunk0patch2.rpkg` into the game's `Runtime\` folder. If you built a manifest in step 3, back up
   `Runtime\packagedefinition.txt` and copy the new one over it.
5. Play the boat chase. Delete the `launch\` folder afterwards to get the 20 GB back.

Notes
- The patch is built for slot 2 so it sits next to the *Launch Title Fanfare* mod in slot 1. If slot 2 is taken,
  pass another number as third argument (`… "…\Runtime" 3`); the RPKG header must match the file name, so do
  not just rename the file.
- Mod managers: install the built `chunk0patch2.rpkg` like any other patch file.
- Uninstall: delete `Runtime\chunk0patch2.rpkg` and restore your manifest backup if you replaced it.

## What exactly changed in 1.0.x (and what the mod reverts)

All in-game music is streamed through one Wwise event, `MX_Music_SW_Play` (WWEV `01A872A294A76EAD`, 5,397
stems). Between the launch build and the 2026-06-11 build exactly one stem was exchanged, and nothing in the
music media has changed since:

| | Launch (restored) | 1.0.x – current |
|---|---|---|
| Wwise source id | `3E5F24AC` | `236D6A95` |
| Resource | WWEM `0164B2AAA73D4801` (removed from the game) | WWEM `015E589FC5DD9B12` |
| Length | 1:13.7, 48 kHz stereo | 1:13.7, 48 kHz stereo |

The campaign music bank in `chunk1.rpkg` reaches this stem via `State_MX_GameFlow = Campaign` → mission
`m09_orchid` → one section of that mission. The bank is left untouched: the patch puts the launch recording
behind the *current* source id (WWEM `015E589FC5DD9B12`) and swaps the 3.8 KB prefetch snippet of that stream
inside the event, so the current bank's track plays the old cue. Two resources, nothing else.

## How the patch is applied by the game

`chunk0patch2.rpkg` is an RPKG v2 (`2KPR`) patch archive with two resources, sub-header
`01 00 00 00 <chunk> 00 <patch> 78 78` = chunk 0 / patch 2. The game loads `chunk0patchN.rpkg` for
`N ≤ patchlevel`, so both resources override the ones in `chunk0.rpkg`.

## Credits / tools

- [RPKG-Tool](https://github.com/glacier-modding/RPKG-Tool) (*first-light* branch, glacier-modding) – hash list, XTEA keys, format reference
- [wwiser](https://github.com/bnnm/wwiser) (bnnm) – Wwise bank parsing
- [vgmstream](https://vgmstream.org) – Wwise Vorbis decoding
- [DepotDownloader](https://github.com/SteamRE/DepotDownloader) (SteamRE) – fetching the launch depot
- Source code, research log and the rest of the toolbox: https://github.com/derx05/gaming-007FirstLight-toolbox

The research and the tooling behind this mod were made with the help of Claude (Anthropic's Claude Code);
the result was verified in game by humans.

007 First Light © IO Interactive. This download ships no audio and no game data; the patch you build from your
own copies of the game stays on your machine.
