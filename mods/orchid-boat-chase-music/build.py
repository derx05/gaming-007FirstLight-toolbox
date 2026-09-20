"""rebuild.py hook for the boat-chase mod.

    python mods/orchid-boat-chase-music/build.py "<Runtime>"

1. always: writes the Nexus "build kit" zip (release/007FirstLight_OrchidBoatChaseMusic_v1.0_BuildKit.zip):
   the builder script, tools/pkgdef.py, filelist.txt and a README.txt - everything a user needs without the repo.
2. if a launch-build archive is present in versions/: builds chunk0patch2.rpkg (contains audio, never committed).
"""
import glob, os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); import build_from_launch
KIT = '007FirstLight_OrchidBoatChaseMusic_v1.0_BuildKit.zip'
README = """007 First Light - Launch Boat Chase Music Restored (mission 9)  -  build kit
==========================================================================

This kit contains NO audio. It builds the patch from the launch build of the game, which you download
yourself with DepotDownloader (about 20 GB, needs the game on your Steam account).

Needs: Windows, Python 3.12+ (python.org), then once:   pip install lz4

1. DepotDownloader: https://github.com/SteamRE/DepotDownloader/releases  (DepotDownloader-windows-x64.zip),
   unzip it next to these files.

2. Download the launch build's chunk0.rpkg (one line; scan the QR code with the Steam mobile app):

   DepotDownloader.exe -app 3768760 -depot 3768761 -manifest 7322178669849310269 -qr -filelist filelist.txt -dir launch -max-downloads 8

   HTTP 503 from Steam's CDN is transient: run the same command again, it resumes.

3. Build the patch (adjust the game path):

   python build_from_launch.py launch\\Runtime\\chunk0.rpkg "D:\\SteamLibrary\\steamapps\\common\\007 First Light\\Runtime"

   Add  --manifest  at the end if you have NO other mod installed yet: it also writes a packagedefinition.txt
   with patchlevel=310 (the retail one has patchlevel=0 and ignores every patch file).
   Add a number before --manifest (e.g. 3) if patch slot 2 is already taken by another mod.

4. Copy chunk0patch2.rpkg into the game's Runtime\\ folder. If you built a packagedefinition.txt in step 3,
   back up the game's Runtime\\packagedefinition.txt and copy the new one over it.

5. Play the mission 9 boat chase. The launch\\ folder can be deleted afterwards.

Uninstall: delete Runtime\\chunk0patch2.rpkg (and restore your manifest backup if you replaced it).

Source, research and the other tools: https://github.com/derx05/gaming-007FirstLight-toolbox
"""

def build(rt):
    os.makedirs(os.path.join(ROOT, 'release'), exist_ok=True)
    kit = os.path.join(ROOT, 'release', KIT)
    with zipfile.ZipFile(kit, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(HERE, 'build_from_launch.py'), 'build_from_launch.py')
        z.write(os.path.join(ROOT, 'tools', 'pkgdef.py'), 'pkgdef.py')
        z.write(os.path.join(ROOT, 'filelist.txt'), 'filelist.txt')
        z.writestr('README.txt', README)
    print('orchid-boat-chase-music: release/%s written' % KIT)
    launches = sorted(glob.glob(os.path.join(ROOT, 'versions', '*7322178669849310269*', 'Runtime', 'chunk0.rpkg')))
    if not launches:
        print('orchid-boat-chase-music: no launch archive in versions/ (manifest 7322178669849310269) - patch not built'); return
    build_from_launch.build(launches[0], rt, 2)

if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'D:/SteamLibrary/steamapps/common/007 First Light/Runtime')
