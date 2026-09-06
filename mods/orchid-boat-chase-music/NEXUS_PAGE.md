# 007 First Light – Launch Boat Chase Music Restored (mission 9)

Restores the orchestral music of the boat chase in mission 9 (codename *Orchid*, the mission with Isola) as it
played in the launch build of *007 First Light* (2026-05-27). Update 1.0.2/1.0.3 (early June 2026) replaced that
cue with a new, more electronic recording of the same length. This mod puts the launch recording back.

Verified working on the current Steam build (1.1.x, September 2026), together with the *Launch Title Fanfare* mod.

## Why there is no download of the patch itself

The old recording no longer exists in the current game, and it is IO Interactive's music, so this mod does not
ship it. Instead you build the patch yourself from the launch build, which Steam still lets you download for a
game you own. The build takes a Python script, one 20 GB download and about ten minutes.

## Build it (Windows, Python 3.12+)

1. Get the repository (GitHub, *Code → Download ZIP* or `git clone`) and open a terminal in its folder.
2. Install the Python package and the downloader:
   ```
   python setup.py
   ```
   (or only `pip install lz4` and DepotDownloader from https://github.com/SteamRE/DepotDownloader/releases).
3. Download the launch build's `chunk0.rpkg` (20 GB) with DepotDownloader. It logs into *your* Steam account
   through a QR code shown in the terminal, scanned with the Steam mobile app:
   ```
   external\DepotDownloader\DepotDownloader.exe -app 3768760 -depot 3768761 -manifest 7322178669849310269 -qr ^
       -filelist filelist.txt -dir versions\launch_2026-05-27_manifest_7322178669849310269 -max-downloads 8
   ```
   HTTP 503 errors from Steam's CDN are transient; run the same command again and it resumes.
   Details and alternatives: [docs/DOWNLOAD_OLD_BUILD.md](../../docs/DOWNLOAD_OLD_BUILD.md).
4. Build the patch:
   ```
   python mods\orchid-boat-chase-music\build_from_launch.py versions\launch_2026-05-27_manifest_7322178669849310269\Runtime\chunk0.rpkg "D:\SteamLibrary\steamapps\common\007 First Light\Runtime"
   ```
   The script checks the MD5 of the launch stem, builds `chunk0patch2.rpkg` next to itself (13 MB) and reads it
   back to verify it. Add `--manifest` to also get a `packagedefinition.txt` with `patchlevel=310` if you have no
   other mod installed yet (the retail manifest has `patchlevel=0` and ignores every patch file).
5. Copy `chunk0patch2.rpkg` into the game's `Runtime\` folder. If you do not have a patch-enabled manifest yet,
   back up `Runtime\packagedefinition.txt` and copy the one from step 4 over it.
6. Play the boat chase. Delete `versions\` afterwards if you want the 20 GB back.

Slots: the patch is built as `chunk0patch2.rpkg` so it sits next to the *Launch Title Fanfare* mod in slot 1.
Pass another number as third argument if slot 2 is taken (the RPKG header must match the file name).
Uninstall: delete `Runtime\chunk0patch2.rpkg`.

## What exactly changed in 1.0.x (and what the mod reverts)

All in-game music is streamed through one Wwise event, `MX_Music_SW_Play` (WWEV `01A872A294A76EAD`, 5,397
stems). Between the launch build and the 2026-06-11 build exactly one stem was exchanged, and nothing in the
music media changed after that:

| | Launch (restored) | 1.0.x – current |
|---|---|---|
| Wwise source id | `3E5F24AC` | `236D6A95` |
| Resource | WWEM `0164B2AAA73D4801` (removed from the game) | WWEM `015E589FC5DD9B12` |
| Length | 1:13.7, 48 kHz stereo | 1:13.7, 48 kHz stereo |

The campaign music bank in `chunk1.rpkg` reaches this stem via `State_MX_GameFlow = Campaign` → mission
`m09_orchid` → one section of that mission. The bank itself is left untouched: the mod replaces the audio
behind the *current* source id (WWEM `015E589FC5DD9B12` gets the launch recording) and swaps the 3.8 KB
prefetch snippet of that stream inside the event, so the current bank's track plays the old recording.

## Credits / tools

Same toolchain as the *Launch Title Fanfare* mod: [RPKG-Tool](https://github.com/glacier-modding/RPKG-Tool)
(*first-light* branch, format reference), [wwiser](https://github.com/bnnm/wwiser), [vgmstream](https://vgmstream.org),
[DepotDownloader](https://github.com/SteamRE/DepotDownloader). Research and tooling were made with the help of
Claude (Anthropic's Claude Code); the result was verified in game by a human.

007 First Light © IO Interactive. This mod ships no audio and no game data; the patch you build from your own
copies of the game stays on your machine.
