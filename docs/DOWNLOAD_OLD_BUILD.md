# Downloading an older build of 007 First Light

You need an older build when you want to hear or diff what an update changed, or when you write a mod that
restores something from an earlier version. Steam keeps every published build of a game, and you can download
any of them for a game **you own** with the open-source [DepotDownloader](https://github.com/SteamRE/DepotDownloader)
(SteamRE). Only the two files the tools need are fetched: `chunk0.rpkg` (about 20 GB) and
`packagedefinition.txt`.

See the legal section of the [README](../README.md#legal) for the terms this touches.

## 1. Tools

```
python setup.py
```

puts `DepotDownloader.exe` into `external\DepotDownloader\` (official release build). Nothing runs as
administrator, nothing touches the game installation.

## 2. Find the manifest id of the build you want

Every build of the Windows depot has a manifest id. They are listed with dates on SteamDB:

https://steamdb.info/depot/3768761/manifests/

(app 3768760 = 007 First Light, depot 3768761 = Windows content). Known ids:

| Build | Date | Manifest id |
|---|---|---|
| Launch | 2026-05-27 | 7322178669849310269 |
| 1.0.x | 2026-06-11 | 866138554611481703 |

Compare the SteamDB dates with the patch notes to pick the last build *before* the change you are after.

## 3. Download

From the repository folder, in PowerShell or cmd (one line, `^` is the cmd line continuation):

```
external\DepotDownloader\DepotDownloader.exe -app 3768760 -depot 3768761 -manifest 7322178669849310269 -qr ^
    -filelist filelist.txt -dir versions\launch_2026-05-27_manifest_7322178669849310269 -max-downloads 8
```

- `-qr` shows a QR code; scan it with the Steam mobile app to log in. Your password never goes through the
  tool. Alternatively use `-username <name>` and enter the Steam Guard code when asked.
- `filelist.txt` in this repository restricts the download to `Runtime\chunk0.rpkg` and
  `Runtime\packagedefinition.txt`. Delete it from the command if you want the whole depot (about 57 GB).
- Keep the folder name pattern `versions\<label>_manifest_<id>`: `versions\` is git-ignored and the tools'
  examples use it.
- Steam's CDN sometimes answers with HTTP 503 for older manifests. That is transient; DepotDownloader retries,
  and if it gives up, simply run the same command again. It resumes.
- Requesting an old manifest is granted by Steam for a game your account owns. If Steam refuses the manifest
  request code, the build has been withdrawn by the publisher and cannot be fetched.

## 4. What to do with it

Diff the old archive against your installed game (index level, then byte-exact for audio and UI resources).
Indexing a 20 GB archive takes about 10 seconds; the byte comparison a few minutes:

```
python tools\diff_rpkg.py versions\launch_2026-05-27_manifest_7322178669849310269\Runtime\chunk0.rpkg ^
    "D:\SteamLibrary\steamapps\common\007 First Light\Runtime\chunk0.rpkg" research_diff.json
```

`tools\after_launch.py OLD.rpkg NEW.rpkg outdir` does the same and additionally extracts every changed or
removed sound resource from the old build and converts the stems to WAV. `tools\bank_diff_files.py OLD.WBNK NEW.WBNK full`
lists the Wwise objects that differ between two versions of a soundbank, with their payloads.

Pull a single resource out of the old archive by its hash:

```
python tools\rpkg_extract.py versions\<build>\Runtime\chunk0.rpkg 01980B15FE07DD81 out\mx_mainmenu_old.WBNK
```

Resource hashes are `01` + the first 14 hex digits of MD5 of the IOI path; readable names come from the
hash list of [RPKG-Tool](https://github.com/glacier-modding/RPKG-Tool) (*first-light* branch build).

## 5. Hear the old menu music

`extract_menu_music.py` renders the current build and, reconstructed from it, the launch build. To render
any other build's menu bank, extract it from that build and drop it into `render\banks\` as a plain `.bnk`
(a WBNK is `00 00` + a 4-byte length + the bank, so strip the first 6 bytes):

```
python tools\rpkg_extract.py versions\<build>\Runtime\chunk0.rpkg 01980B15FE07DD81 render\banks\mx_mainmenu_<build>.WBNK
python -c "d=open(r'render\banks\mx_mainmenu_<build>.WBNK','rb').read(); open(r'render\banks\mx_mainmenu_<build>.bnk','wb').write(d[6:])"
```

then add `('mx_mainmenu_<build>.bnk', 'menu_music_<build>')` to the `BANKS` tuple in
`tools\render_music_timeline.py` and run `python tools\render_music_timeline.py`. The stems in `render\wem\`
are identical in every build so far, so nothing else is needed. If a future build changes the stems, extract
them from that build with `rpkg_extract.py` using the hashes in `tools\media_map.json`.
