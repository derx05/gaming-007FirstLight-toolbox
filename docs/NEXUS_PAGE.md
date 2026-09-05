# 007 First Light – Launch Title Fanfare Restored

Restores the main-menu title music exactly as it played in the launch build of *007 First Light*
(Steam depot 3768761, manifest 7322178669849310269, 2026-05-27). Update 1.0.2/1.0.3 (June 2026)
re-arranged the "Landing" menu-music state so the opening horn motif is skipped and faded in; this
mod puts the original arrangement back. **No audio is added, replaced or redistributed** – the game's own
music clips are untouched, only four Wwise property values inside one 19 KB soundbank are restored.

Verified working on the current Steam build (1.1.x, September 2026).

## Install (like every other 007 First Light RPKG mod)

1. Back up `…\007 First Light\Runtime\packagedefinition.txt`.
2. Extract the release zip. Copy `Runtime\chunk0patch1.rpkg` and `Runtime\packagedefinition.txt`
   into the game's `Runtime\` folder, overwriting `packagedefinition.txt`.
3. Start the game. The title screen now plays the launch fanfare.

Notes
- The shipped `packagedefinition.txt` is the game's own manifest with `patchlevel=310` on both
  partitions (identical to what other mods such as *Skip Intro* ship). Any patch mod needs that,
  because the retail file has `patchlevel=0` and ignores all `chunkNpatchM.rpkg` files.
- Conflicts: only one mod may use the `chunk0patch1` slot. Rename this file to a free slot
  (`chunk0patch2.rpkg`, …) if needed – the patch is self-contained and slot-independent in content,
  but rebuild it with `restore_fanfare.py` (below) if you rename it, because the RPKG header stores
  the patch number.
- Uninstall: delete `Runtime\chunk0patch1.rpkg` and restore your original `packagedefinition.txt`
  (or verify game files in Steam).

## Audio-free alternative: build the patch from your own game files

`mod\restore_fanfare.py` contains **only** the restored Wwise property values (a few hundred bytes of
hex) and rebuilds the patch from *your* `chunk0.rpkg`:

```
pip install lz4
python mod\restore_fanfare.py "D:\SteamLibrary\steamapps\common\007 First Light\Runtime"
```

It checks the MD5 of the current soundbank (`6ca50654…`), rebuilds it, checks that the result equals
the launch bank (`d5ccca44…`) and writes `chunk0patch1.rpkg` next to `chunk0.rpkg`. You still need the
`patchlevel=310` manifest (`mod\packagedefinition.txt`, or build your own with `tools\pkgdef.py`).

## What exactly changed in 1.0.x (and what the mod reverts)

Resource `01980B15FE07DD81` = `[assembly:/_knt/sound/wwise/exported/soundbanks/global/mx_mainmenu.wwisesoundbank]`
(Wwise 2023.1, bank version 150). Event `MX_MainMenu_SW_Play`, switch group `State_MX_MainMenu`,
state `Landing` (2548270042) is the music that plays when the title appears. Diff launch → 1.0.x:

| HIRC object | Type | Launch (restored) | 1.0.x – current |
|---|---|---|---|
| `0x19EA31A3` | Music Random/Sequence playlist | plays segment `0x3A51E915` | plays segment `0x2C663D2D` |
| `0x0BC0A5DA` | Music Track (source 0x136A5556) | clip starts at 3 230.77 ms, no fade | starts at 12 923.08 ms + 3.75 s fade-in |
| `0x21BB990C` | Music Track (source 0x0E85E12E) | clip starts at 3 230.77 ms, no fade | starts at 11 076.92 ms + 5.37 s fade-in |
| `0x21E1267C` | Music Track (source 0x0E1285C8) | no volume property | Volume +5 dB |
| BKHD | bank header | launch bank hash | new bank hash |

Every `.wem` referenced by the bank is byte-identical in all builds – the "fast triple horn" opening is
simply the first ~10 s of two stems that 1.0.x trims away. The mod contains the launch values of those
four objects (plus the 16-byte bank hash) and nothing else.

## How the patch is applied by the game

`chunk0patch1.rpkg` is an RPKG v2 (`2KPR`) patch archive with a single resource. Its 9-byte sub-header
`01 00 00 00 <chunk> 00 <patch> 78 78` encodes chunk 0 / patch 1 (the game checks this against the file
name – a mismatch crashes on launch). The game loads `chunk0patchN.rpkg` for `N ≤ patchlevel`, so the
resource overrides the one in `chunk0.rpkg`. `packagedefinition.txt` is XTEA-encrypted
(16-byte header + CRC32 + XTEA blocks, keys from the RPKG-Tool *first-light* branch); `tools\pkgdef.py`
decrypts/encrypts it byte-exactly.

## Listening material (not redistributable)

`tools\render_music_timeline.py` renders every menu-music state and random variant of both bank versions
to 24-bit FLAC with an offline re-implementation of Wwise music playback (`audio\renders\…`). These are the game's own recordings and are
kept out of the repository by `.gitignore`.

## Credits / tools

- [RPKG-Tool](https://github.com/glacier-modding/RPKG-Tool) (*first-light* branch, glacier-modding) – hash list, XTEA keys, format reference
- [wwiser](https://github.com/bnnm/wwiser) (bnnm) – Wwise bank parsing and TXTP generation
- [vgmstream](https://vgmstream.org) – Wwise Vorbis decoding
- [DepotDownloader](https://github.com/SteamRE/DepotDownloader) (SteamRE) – fetching the launch depot
- The *Skip Intro* mod (Nexus) served as the reference for a working patch header and manifest

The research and the tooling behind this mod were made with the help of Claude (Anthropic's Claude Code);
the result was verified in game by a human.

007 First Light © IO Interactive. This mod ships no audio and no original game data other than the
restored property values described above; the release zip additionally contains the rebuilt 19 KB
soundbank (no media) and the manifest with a changed patch level.
