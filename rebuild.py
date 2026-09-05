"""Regenerate everything this repository ignores, from the installed game only.

    python rebuild.py "D:/SteamLibrary/steamapps/common/007 First Light/Runtime"

1. extracts the current mx_mainmenu soundbank and the 83 menu-music stems from chunk0.rpkg -> render/
2. reconstructs the launch-day bank from it (same code path as mod/restore_fanfare.py, MD5-verified)
3. builds mod/chunk0patch1.rpkg and the patchlevel=310 mod/packagedefinition.txt
4. zips the release (release/…zip)
5. renders every menu-music state and random variant to audio/renders/ (24-bit FLAC)

Needs: python setup.py first (tools + packages). No other game build is required.
"""
import hashlib, importlib.util, json, os, shutil, sys, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from rpkg_index import parse
from rpkg_read import read_resource
import pkgdef

BANK = '01980B15FE07DD81'

def load_restore():
    spec = importlib.util.spec_from_file_location('restore_fanfare', os.path.join(ROOT, 'mod', 'restore_fanfare.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def main():
    rt = sys.argv[1] if len(sys.argv) > 1 else 'D:/SteamLibrary/steamapps/common/007 First Light/Runtime'
    chunk0 = os.path.join(rt, 'chunk0.rpkg')
    print('indexing', chunk0); idx = parse(chunk0); by = {e['hash']: e for e in idx['entries']}; f = open(chunk0, 'rb')

    # 1. stems + current bank
    wemdir = os.path.join(ROOT, 'render', 'wem'); os.makedirs(wemdir, exist_ok=True)
    mm = json.load(open(os.path.join(ROOT, 'tools', 'media_map.json'))); n = 0
    for grp in ('splash', 'theme'):
        for e in mm[grp]:
            dst = os.path.join(wemdir, f"{e['wem_dec']}.wem")
            if not os.path.exists(dst):
                open(dst, 'wb').write(read_resource(f, by[e['rpkg_hash']])); n += 1
    print(f'stems: {n} extracted, {len(os.listdir(wemdir))} present')
    cur = read_resource(f, by[BANK]); print('current bank md5', hashlib.md5(cur).hexdigest())

    # 2. launch bank via the mod's own patcher
    rf = load_restore()
    launch = rf.patch_bank(cur)
    assert hashlib.md5(launch).hexdigest() == rf.EXPECT_PATCHED_MD5, 'reconstructed bank does not match the launch MD5'
    bdir = os.path.join(ROOT, 'render', 'banks'); os.makedirs(bdir, exist_ok=True)
    open(os.path.join(bdir, 'mx_mainmenu_current.bnk'), 'wb').write(cur[6:])
    open(os.path.join(bdir, 'mx_mainmenu_launch.bnk'), 'wb').write(launch[6:])
    rdir = os.path.join(ROOT, 'research', 'banks'); os.makedirs(rdir, exist_ok=True)
    open(os.path.join(rdir, 'mx_mainmenu_current_since_1.0.x.WBNK'), 'wb').write(cur)
    open(os.path.join(rdir, 'mx_mainmenu_launch_2026-05-27.WBNK'), 'wb').write(launch)
    print('launch bank reconstructed and verified')

    # 3. patch + manifest
    e = rf.read_index(open(chunk0, 'rb'))
    out = os.path.join(ROOT, 'mod', 'chunk0patch1.rpkg')
    rf.write_patch(out, rf.BANK_HASH, e['typ'], launch, e['rts'], e['sm'], e['vm'], e['ref'], 0, 1)
    src = open(os.path.join(rt, 'packagedefinition.txt'), 'rb').read()
    hdr, crc, plain = pkgdef.decrypt(src)
    plain2 = plain.replace(b'patchlevel=0', b'patchlevel=310') if b'patchlevel=0' in plain else plain
    open(os.path.join(ROOT, 'mod', 'packagedefinition.txt'), 'wb').write(pkgdef.encrypt(hdr, plain2))
    shutil.copy(os.path.join(rt, 'packagedefinition.txt'), os.path.join(ROOT, 'research', 'packagedefinition.txt.original'))
    print('mod/chunk0patch1.rpkg + mod/packagedefinition.txt written')

    # 4. release zip
    os.makedirs(os.path.join(ROOT, 'release'), exist_ok=True)
    with zipfile.ZipFile(os.path.join(ROOT, 'release', '007FirstLight_LaunchTitleFanfare_v1.0.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(out, 'Runtime/chunk0patch1.rpkg'); z.write(os.path.join(ROOT, 'mod', 'packagedefinition.txt'), 'Runtime/packagedefinition.txt')
    print('release zip written')

    # 5. renders
    import render_music_timeline; render_music_timeline.main()

if __name__ == '__main__':
    main()
