# 007 First Light – Launch Title Fanfare Restored

A small mod for *007 First Light* (IO Interactive, 2026) that brings back the title-screen music arrangement
of the launch build, plus the tooling and research that found the change.

The launch build (2026-05-27) opened the main-menu "Landing" music with a fast triple horn motif. Update
1.0.2/1.0.3 (June 2026) re-arranged that music state inside the `mx_mainmenu` Wwise soundbank: a different
segment in the playlist, two stems trimmed ~10 s later with fade-ins, one +5 dB volume property. The audio
clips themselves never changed. This mod restores those property values – **no audio is added, replaced or
redistributed.**

Confirmed working on the current Steam build (1.1.x, September 2026).

## Repository contents

| Path | What |
|---|---|
| `mod/restore_fanfare.py` | Audio-free builder: rebuilds the launch bank from *your* `chunk0.rpkg`, writes `chunk0patch1.rpkg`. Only Wwise property values are embedded. |
| `mod/` (ignored files) | The built `chunk0patch1.rpkg` and the `patchlevel=310` `packagedefinition.txt` – see releases / Nexus for the ready-made zip. |
| `tools/` | Python tools written for this project: RPKG v2 indexer/reader/diff/writer, Wwise bank diff, WWEV dissector, manifest XTEA codec, and an offline Wwise interactive-music renderer. |
| `research/` | wwiser XML dumps of the launch and current bank (the exact four-object diff is in `docs/`). |
| `docs/NEXUS_PAGE.md` | The user-facing mod description (install, uninstall, technical summary). |
| `docs/RESEARCH_LOG.md` | The full investigation log: what was compared, every dead end, all format findings. |
| `ARCHITECTURE.md` | Folder layout, data flow, verified file formats, how to reproduce or diff another build. |

Game data (soundbanks, stems, renders, downloaded depots) and third-party tools are excluded by `.gitignore`.

## Install the mod

Grab the release zip and copy `Runtime\chunk0patch1.rpkg` and `Runtime\packagedefinition.txt` into the
game's `Runtime\` folder (back up the original manifest first), or let a 007 First Light mod manager install
the zip. Details and uninstall: [docs/NEXUS_PAGE.md](docs/NEXUS_PAGE.md).

## Rebuild everything from a fresh clone (about one minute)

Only the installed game and Python 3.12+ are needed. No other game build has to be downloaded: the launch
bank is reconstructed from the current one by the mod's own patcher and verified by MD5.

```
python setup.py                                                   # pip packages + vgmstream, wwiser, DepotDownloader -> external/
python rebuild.py "D:/SteamLibrary/steamapps/common/007 First Light/Runtime"
```

`rebuild.py` extracts the 83 menu stems and the current bank from `chunk0.rpkg`, reconstructs the launch bank,
writes `mod/chunk0patch1.rpkg`, the `patchlevel=310` manifest and the release zip, and renders every menu-music
state to `audio/renders/` (24-bit FLAC). All outputs are byte-identical to the originals of this project.

Just the patch, without the rest:

```
pip install lz4
python mod/restore_fanfare.py "<game>/Runtime"        # writes chunk0patch1.rpkg next to chunk0.rpkg
```

## Reproduce the research

[ARCHITECTURE.md](ARCHITECTURE.md) explains the tools and the verified formats. To diff another game build,
download it with DepotDownloader into `versions/` (manifest ids on SteamDB) and run `tools/diff_rpkg.py`
against the installed game; `tools/bank_diff_files.py` shows the HIRC objects that differ. RPKG-Tool
(first-light branch) is only needed for resource names.

## Credits

RPKG-Tool (glacier-modding) for the hash list and the manifest keys, wwiser (bnnm), vgmstream, DepotDownloader
(SteamRE). The community *Skip Intro* mod served as the reference for a working patch header and manifest.

## AI assistance

The investigation, the Python tools and this documentation were produced with the help of Claude (Anthropic's
Claude Code, model Claude Fable 5.1). The archive diffs, format findings and the patch itself were verified
against the real game files at every step, and the in-game result was confirmed by a human. Errors are the
maintainer's responsibility, not the model's.

007 First Light © IO Interactive. This repository contains no game audio.
