"""Build this mod's release from the installed game: chunk0patch1.rpkg, the patchlevel=310 manifest, the zip.

    python mods/launch-title-fanfare/build.py "<Runtime>"       (or via rebuild.py, which builds every mod)

Writes next to this file: chunk0patch1.rpkg, packagedefinition.txt, packagedefinition.txt.original (backup of yours),
research/*.WBNK (current + reconstructed launch bank); and release/007FirstLight_LaunchTitleFanfare_v1.0.zip.
Needs only python + lz4.
"""
import hashlib, importlib.util, os, shutil, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools')); import pkgdef
ZIP = '007FirstLight_LaunchTitleFanfare_v1.0.zip'

def build(rt):
    spec = importlib.util.spec_from_file_location('restore_fanfare', os.path.join(HERE, 'restore_fanfare.py'))
    rf = importlib.util.module_from_spec(spec); spec.loader.exec_module(rf)
    with open(os.path.join(rt, 'chunk0.rpkg'), 'rb') as f:
        e = rf.read_index(f); cur = rf.read_resource(f, e)
    assert hashlib.md5(cur).hexdigest() == rf.EXPECT_CURRENT_MD5, 'unknown mx_mainmenu bank - did the game change it again?'
    launch = rf.patch_bank(cur)
    assert hashlib.md5(launch).hexdigest() == rf.EXPECT_PATCHED_MD5
    os.makedirs(os.path.join(HERE, 'research'), exist_ok=True)
    for name, data in (('mx_mainmenu_current_since_1.0.x.WBNK', cur), ('mx_mainmenu_launch_2026-05-27.WBNK', launch)):
        open(os.path.join(HERE, 'research', name), 'wb').write(data)
    patch = os.path.join(HERE, 'chunk0patch1.rpkg')
    rf.write_patch(patch, rf.BANK_HASH, e['typ'], launch, e['rts'], e['sm'], e['vm'], e['ref'], 0, 1)
    src = os.path.join(rt, 'packagedefinition.txt')
    hdr, crc, plain = pkgdef.decrypt(open(src, 'rb').read())
    manifest = os.path.join(HERE, 'packagedefinition.txt')
    open(manifest, 'wb').write(pkgdef.encrypt(hdr, plain.replace(b'patchlevel=0', b'patchlevel=310')))
    shutil.copy(src, os.path.join(HERE, 'packagedefinition.txt.original'))
    os.makedirs(os.path.join(ROOT, 'release'), exist_ok=True)
    with zipfile.ZipFile(os.path.join(ROOT, 'release', ZIP), 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(patch, 'Runtime/chunk0patch1.rpkg'); z.write(manifest, 'Runtime/packagedefinition.txt')
    print(f'launch-title-fanfare: chunk0patch1.rpkg, packagedefinition.txt, release/{ZIP} written')

if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else 'D:/SteamLibrary/steamapps/common/007 First Light/Runtime')
