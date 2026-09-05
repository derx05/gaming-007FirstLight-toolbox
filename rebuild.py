"""Regenerate everything this repository ignores, from the installed game only (about one minute).

    python rebuild.py "D:/SteamLibrary/steamapps/common/007 First Light/Runtime"

1. extract_menu_music.py  -> render/wem, render/banks, audio/renders (stems, soundbanks, FLAC renders)
2. every mods/*/build.py  -> that mod's patch RPKG, patchlevel=310 manifest and release/*.zip

Needs: python setup.py first. No other game build is required.
"""
import glob, importlib.util, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def main():
    rt = sys.argv[1] if len(sys.argv) > 1 else 'D:/SteamLibrary/steamapps/common/007 First Light/Runtime'
    import extract_menu_music; extract_menu_music.main([rt])
    for path in sorted(glob.glob(os.path.join(ROOT, 'mods', '*', 'build.py'))):
        spec = importlib.util.spec_from_file_location('build_' + os.path.basename(os.path.dirname(path)), path)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.build(rt)

if __name__ == '__main__':
    main()
