"""rebuild.py hook: build chunk0patch2.rpkg if a launch-build archive is present in versions/, otherwise skip.

    python mods/orchid-boat-chase-music/build.py "<Runtime>"

The launch archive is the only source of the old stem; see NEXUS_PAGE.md for how to download it.
"""
import glob, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); import build_from_launch

def build(rt):
    launches = sorted(glob.glob(os.path.join(ROOT, 'versions', '*7322178669849310269*', 'Runtime', 'chunk0.rpkg')))
    if not launches:
        print('orchid-boat-chase-music: no launch archive in versions/ (manifest 7322178669849310269) - skipped'); return
    build_from_launch.build(launches[0], rt, 2)

if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'D:/SteamLibrary/steamapps/common/007 First Light/Runtime')
