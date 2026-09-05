"""Extract one resource from an RPKG v2 archive by its hash (decrypts + decompresses).

    python tools/rpkg_extract.py "<Runtime>/chunk0.rpkg" 01980B15FE07DD81 out/mx_mainmenu.WBNK

Useful with a downloaded older build (see docs/DOWNLOAD_OLD_BUILD.md). WBNK files are `00 00 + u32 len + .bnk`;
strip the first 6 bytes to get a plain Wwise bank for wwiser / render_music_timeline.py.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpkg_index import parse
from rpkg_read import read_resource

if __name__ == '__main__':
    rpkg, h, out = sys.argv[1], sys.argv[2].upper(), sys.argv[3]
    idx = parse(rpkg); e = next((e for e in idx['entries'] if e['hash'] == h), None)
    if e is None:
        raise SystemExit(f'{h} not in {rpkg}')
    with open(rpkg, 'rb') as f:
        data = read_resource(f, e)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, 'wb').write(data)
    print(f'{h} ({e["type"]}) -> {out}, {len(data)} bytes')
