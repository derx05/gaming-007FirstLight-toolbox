"""Write an RPKG v2 (2KPR) patch file from a folder of <HASH>.<TYPE> + <HASH>.<TYPE>.meta (RPKG-Tool layout).
Usage: python tools/make_patch.py <folder> <out.rpkg> [--no-compress]
Header layout mirrors the game's own chunk0.rpkg (unknown bytes 01 00 00 00 00 00 00 78 78) plus a
zero-length patch deletion list. Entries are LZ4-block compressed and XOR-encrypted like IOI's."""
import sys, os, re, struct, lz4.block
sys.path.insert(0, os.path.dirname(__file__))
from rpkg_read import KEY
folder, out = sys.argv[1], sys.argv[2]; compress = '--compress' in sys.argv
m = re.search(r'chunk(\d+)patch(\d+)', os.path.basename(out)); CHUNK, PATCH = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
files = sorted(f for f in os.listdir(folder) if not f.endswith('.meta') and not f.endswith('.JSON') and not f.endswith('.rpkg'))
entries = []
for fn in files:
    data = open(os.path.join(folder, fn), 'rb').read(); meta = open(os.path.join(folder, fn + '.meta'), 'rb').read()
    h = struct.unpack_from('<Q', meta, 0)[0]; typ = meta[20:24]; rts = struct.unpack_from('<I', meta, 24)[0]
    sysm, vidm = struct.unpack_from('<II', meta, 32); reftable = meta[40:40 + rts]
    assert len(reftable) == rts, (fn, len(reftable), rts)
    if compress:
        c = lz4.block.compress(data, mode='high_compression', store_size=False); csize = len(c) | 0x80000000
    else:
        c = data; csize = 0
    enc = bytes(x ^ KEY[i & 7] for i, x in enumerate(c)) if compress else c
    entries.append((h, csize, typ, rts, len(data), sysm, vidm, reftable, enc))
    print(fn, typ, 'size', len(data), 'stored', len(enc), 'refs', rts)
hashtab = b''.join(struct.pack('<QQI', h, 0, cs) for h, cs, *_ in entries)  # offsets patched below
infotab = b''.join(typ[::-1] + struct.pack('<IIII', rts, ds, sm, vm) + rt for h, cs, typ, rts, ds, sm, vm, rt, enc in entries)
is_patch = 'patch' in os.path.basename(out).lower()
hdr = b'2KPR' + bytes([1, 0, 0, 0, CHUNK, 0, PATCH, 0x78, 0x78]) + struct.pack('<III', len(entries), len(hashtab), len(infotab))
if is_patch: hdr += struct.pack('<I', 0)  # empty deletion list
base = len(hdr) + len(hashtab) + len(infotab); off = base; ht = b''
for h, cs, typ, rts, ds, sm, vm, rt, enc in entries:
    ht += struct.pack('<QQI', h, off, cs); off += len(enc)
blob = hdr + ht + infotab + b''.join(e[-1] for e in entries)
open(out, 'wb').write(blob); print('wrote', out, len(blob), 'bytes, patch header' if is_patch else '')
