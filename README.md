# 007 First Light – tools & mods

Python tooling for *007 First Light* (IO Interactive, 2026) and the mods built with it: reading and diffing
the game's RPKG archives, decoding its manifest, dissecting Wwise soundbanks, rendering the interactive menu
music the way it plays in game, and writing patch archives that change a few values without shipping any
game data.

Everything works from **your own installed copy** of the game. This repository contains no game audio, no
game media and no game data beyond a handful of Wwise property values (see [Legal](#legal)).

## Mods

| Mod | What it does | Get it |
|---|---|---|
| [`mods/launch-title-fanfare/`](mods/launch-title-fanfare/NEXUS_PAGE.md) | Restores the launch-build (2026-05-27) title-screen music arrangement that update 1.0.2/1.0.3 replaced. Four Wwise property values in one soundbank; no audio is added or replaced. | [Nexus Mods](https://www.nexusmods.com/007firstlight/mods/207) or the releases page |

Every mod folder holds its user-facing description (`NEXUS_PAGE.md`), a standalone audio-free builder, the
built patch RPKG and manifest, a `build.py` used by `rebuild.py`, and its research notes.

Install a mod like every other 007 First Light RPKG mod: back up `Runtime\packagedefinition.txt`, copy the
zip's `Runtime\` files into the game's `Runtime\` folder, or let a mod manager do it. The mod page has the
details, the slot rules and how to uninstall.

## Tools

Front ends in the repository root (Windows, Python 3.12+, installed game):

```
git clone <this repository>
python setup.py                                                        # pip packages + vgmstream, wwiser, DepotDownloader -> external/
python extract_menu_music.py "D:/SteamLibrary/steamapps/common/007 First Light/Runtime"
python rebuild.py "D:/SteamLibrary/steamapps/common/007 First Light/Runtime"
```

- `setup.py` downloads the third-party tools from their official GitHub releases. Nothing runs as
  administrator, nothing is written into the game folder.
- `extract_menu_music.py` pulls the 83 menu-music stems and the `mx_mainmenu` soundbank out of your
  `chunk0.rpkg`, reconstructs the launch-day soundbank from it (MD5-verified, no download needed) and renders
  every menu-music state (Splash, Landing/title, Loading, MainMenu with all random variants) of both versions to
  24-bit FLAC in `audio/renders/`. `--no-render` stops after the stems and banks.
- `rebuild.py` does the above and then runs every `mods/*/build.py`: patch RPKG, `patchlevel=310` manifest and
  release zip. The result is byte-identical to the published files (about one minute).

The library behind them, `tools/`:

| Script | Purpose |
|---|---|
| `rpkg_index.py` | index an RPKG v2 archive (`chunkN.rpkg`, patches incl. deletion list) to JSON, no extraction |
| `rpkg_read.py`, `rpkg_extract.py` | read / extract one resource (XOR key + LZ4); FNV-1 hashing for Wwise ids |
| `diff_rpkg.py`, `after_launch.py` | diff two builds of an archive, byte-exact for audio and UI types, extract what changed |
| `make_patch.py` | write a `chunkNpatchM.rpkg` from a folder of resources |
| `pkgdef.py` | decrypt / encrypt `packagedefinition.txt` (XTEA, byte-exact round trip) |
| `scan_wwev.py`, `dump_wwev.py`, `wwev_list.py` | Wwise event resources: names, embedded and streamed media |
| `hirc.py`, `bank_diff_files.py` | Wwise soundbank object walker; object-level diff of two banks |
| `render_music_timeline.py` | offline Wwise interactive-music engine: segments, cues, transitions, clip trims, fades, hierarchy volumes, resampling; one FLAC per state and variant |
| `media_map.json` | menu-music wem ids and their resource hashes |

The formats are documented in [ARCHITECTURE.md](ARCHITECTURE.md). Older builds of the game, for diffing or
listening, are covered in [docs/DOWNLOAD_OLD_BUILD.md](docs/DOWNLOAD_OLD_BUILD.md).

## Making another mod

1. Download the build that still had what you want (`docs/DOWNLOAD_OLD_BUILD.md`).
2. `tools/diff_rpkg.py OLD NEW` tells you which resources changed; `tools/bank_diff_files.py OLD.WBNK NEW.WBNK full`
   shows the changed Wwise objects; wwiser (`python external/wwiser/wwiser.pyz -d xml bank.bnk`) names the fields.
3. Prefer restoring *values* over shipping files: put the old payloads into a small patcher like
   `mods/launch-title-fanfare/restore_fanfare.py` that rewrites the user's own resource, and let `tools/make_patch.py`
   or its `write_patch` produce the `chunkNpatchM.rpkg`. `tools/pkgdef.py` makes the `patchlevel=310` manifest.
4. Create `mods/<name>/` with `build.py` exposing `build(runtime)`, a `NEXUS_PAGE.md`, and check the result in game.
   `rebuild.py` picks the folder up automatically.

## Legal

Not legal advice; the maintainer is not a lawyer. This is what the repository does and where the gray
zones are, so you can decide for yourself.

**What is here.** Code and documentation written for this project (MIT licensed), reverse-engineered format
descriptions, and for each mod a few hundred bytes of Wwise property values taken from an older build of one
soundbank. The committed patch RPKG is a rebuilt 19 KB soundbank *structure* (no audio) and the committed
manifest is the game's own manifest with one number changed. That is the same pair of files every community
RPKG mod for this game ships.

**What is not here, and must stay out.** No `.wem` stems, no soundbanks, no FLAC renders, no downloaded
depots. The tools produce all of that from your own installation into git-ignored folders. It is a private
copy of content you hold a license for. Do not upload it, do not share it, do not put it in a mod. If you
fork this repository, keep the `.gitignore`.

**Gray zones, honestly.**

- *Keys.* The RPKG XOR key and the manifest XTEA keys are in the source (`tools/`, `restore_fanfare.py`).
  They have been public in glacier-modding's RPKG-Tool for years, for Hitman and now for this game, but some
  jurisdictions treat bypassing even light obfuscation as circumventing a technical protection measure
  (DMCA §1201 in the US, §95a UrhG in Germany). The counter-argument is interoperability for modding, and IOI's
  long-standing tolerance of the Hitman modding scene; there is no court decision either way for this game.
- *Terms of use.* The Steam Subscriber Agreement and IOI's EULA most likely prohibit reverse engineering and
  modifying the game. That is a contractual matter between you and them, not a copyright one, but it exists.
- *Older builds.* DepotDownloader logs into *your* Steam account and can only fetch games you own. Steam's
  servers grant older manifests of owned games; the publisher has not endorsed it. The downloaded depot is
  yours to keep privately, not to share.
- *Mods in general.* IOI has tolerated and at times supported community mods for Hitman. Nothing guarantees
  the same attitude for 007 First Light.

If IO Interactive objects to anything in this repository the maintainer will take it down. Use and fork at
your own risk.

## Credits

[RPKG-Tool](https://github.com/glacier-modding/RPKG-Tool) (glacier-modding) for the hash list and the
manifest keys, [wwiser](https://github.com/bnnm/wwiser) (bnnm), [vgmstream](https://vgmstream.org),
[DepotDownloader](https://github.com/SteamRE/DepotDownloader) (SteamRE). The community *Skip Intro* mod served
as the reference for a working patch header and manifest.

## AI assistance

The investigation, the Python tools and this documentation were produced with the help of Claude (Anthropic's
Claude Code, model Claude Fable 5.1). The archive diffs, format findings and the patches were verified against
the real game files at every step, and every in-game result was confirmed by a human. Errors are the
maintainer's responsibility, not the model's.

## License

Code and documentation: [MIT](LICENSE). 007 First Light © IO Interactive; the license does not extend to the
game or to anything derived from it.
