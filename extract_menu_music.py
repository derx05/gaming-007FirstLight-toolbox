"""Extract the 007 First Light menu music from YOUR installed game and render it the way it plays in game.

    python extract_menu_music.py "D:/SteamLibrary/steamapps/common/007 First Light/Runtime"
    python extract_menu_music.py "<Runtime>" --no-render        # stems + soundbanks only

Output (git-ignored; derived from your own copy of the game, do not upload or share it):
    render/wem/<id>.wem                    the 83 menu-music stems (Wwise Vorbis, play with vgmstream/foobar2000)
    render/banks/mx_mainmenu_current.bnk   the mx_mainmenu soundbank of your installed build
    render/banks/mx_mainmenu_launch.bnk    the launch-day (2026-05-27) soundbank, reconstructed from the current one
                                           with the values stored in mods/launch-title-fanfare (MD5-verified;
                                           skipped when your bank is not the one this repo knows)
    audio/renders/<bank>/<state>.flac      every menu-music state and random variant, 24-bit 48 kHz FLAC

Needs: python setup.py first (numpy, scipy, soundfile, lz4, vgmstream, wwiser).
"""
import hashlib, importlib.util, json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from rpkg_index import parse
from rpkg_read import read_resource

BANK = '01980B15FE07DD81'   # [assembly:/_knt/sound/wwise/exported/soundbanks/global/mx_mainmenu.wwisesoundbank]
DEFAULT_RT = 'D:/SteamLibrary/steamapps/common/007 First Light/Runtime'

def load_module(path):
    spec = importlib.util.spec_from_file_location(os.path.splitext(os.path.basename(path))[0], path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def extract(rt):
    """Stems + current bank -> render/. Returns the current WBNK bytes."""
    chunk0 = os.path.join(rt, 'chunk0.rpkg')
    print('indexing', chunk0); idx = parse(chunk0); by = {e['hash']: e for e in idx['entries']}
    wemdir = os.path.join(ROOT, 'render', 'wem'); os.makedirs(wemdir, exist_ok=True)
    mm = json.load(open(os.path.join(ROOT, 'tools', 'media_map.json'))); n = 0
    with open(chunk0, 'rb') as f:
        for grp in ('splash', 'theme'):
            for e in mm[grp]:
                dst = os.path.join(wemdir, f"{e['wem_dec']}.wem")
                if not os.path.exists(dst):
                    open(dst, 'wb').write(read_resource(f, by[e['rpkg_hash']])); n += 1
        cur = read_resource(f, by[BANK])
    print(f'stems: {n} extracted, {len(os.listdir(wemdir))} present')
    bdir = os.path.join(ROOT, 'render', 'banks'); os.makedirs(bdir, exist_ok=True)
    open(os.path.join(bdir, 'mx_mainmenu_current.bnk'), 'wb').write(cur[6:])
    print('current bank md5', hashlib.md5(cur).hexdigest())
    return cur

def reconstruct_launch(cur):
    """Launch-day bank from the current one via the fanfare mod's patcher; None if the current bank is unknown."""
    rf = load_module(os.path.join(ROOT, 'mods', 'launch-title-fanfare', 'restore_fanfare.py'))
    if hashlib.md5(cur).hexdigest() != rf.EXPECT_CURRENT_MD5:
        print('current bank is not the one this repository knows - launch bank not reconstructed'); return None
    launch = rf.patch_bank(cur)
    assert hashlib.md5(launch).hexdigest() == rf.EXPECT_PATCHED_MD5, 'reconstructed bank does not match the launch MD5'
    open(os.path.join(ROOT, 'render', 'banks', 'mx_mainmenu_launch.bnk'), 'wb').write(launch[6:])
    print('launch bank reconstructed and verified')
    return launch

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rt = next((a for a in argv if not a.startswith('--')), DEFAULT_RT)
    cur = extract(rt)
    launch = reconstruct_launch(cur)
    if '--no-render' not in argv:
        import render_music_timeline; render_music_timeline.main()
    return cur, launch

if __name__ == '__main__':
    main()
