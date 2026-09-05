"""Restore the launch-day (2026-05-27) title fanfare of 007 First Light.

Rebuilds the mx_mainmenu Wwise soundbank (resource 01980B15FE07DD81) from YOUR OWN chunk0.rpkg and
restores the bank header hash and the four HIRC objects that update 1.0.x changed (one playlist segment id, two music-track
clip trim offsets / fade-ins, one +5 dB volume property). This script contains no audio and no game
file, only the Wwise property values in RESTORE. Output: chunk0patch1.rpkg next to chunk0.rpkg.
Needs Python 3 and: pip install lz4

Usage:  python restore_fanfare.py "D:/SteamLibrary/steamapps/common/007 First Light/Runtime" [patch slot, default 1]
"""
import sys, os, struct, hashlib, lz4.block
KEY = bytes([0xDC,0x45,0xA6,0x9C,0xD3,0x72,0x4C,0xAB])
BANK_HASH = 0x01980B15FE07DD81
EXPECT_CURRENT_MD5 = "6ca506540e556150a14a95f89bbb030a"   # bank as shipped since 1.0.x (unchanged through 1.1.x)
EXPECT_PATCHED_MD5 = "d5ccca44469d5746db6945abdb62e56f"   # bank as shipped at launch
# BKHD header of the launch bank (same version/bank id/language/project id; only the 16-byte bank hash differs).
BKHD_LAUNCH = '960000004b0c5ace3e5d701710000000f223000000000000dededf4fda917bddebb82be67d80314e'
# HIRC object id -> (type, launch payload hex). Property values only.
RESTORE = {
    0x19EA31A3: (13, 'a331ea1900000000000000000095000e0c000000000000000000000100000000000000000500000065f1a40a2ba2001d2d3d662c487ed32c15e9513a0000000000408f4000000000000000000000f042040400000000000100000001000000ffffffff01000000ffffffff00000000040000000000000007000000000000000100000000040000000000000000000000000000000000000001000006000000000000000cbfa530030000000000000001000000000050c3000001000100487ed32c65ce852100000000ffffffff01000000000050c300000000000000000000495ec707010000000100000001000000000050c300000100010015e9513a63aa711000000000ffffffff01000000000050c3000000000000000000002f44fa22010000000000000000000000000050c30000010001002ba2001d2d02470900000000ffffffff01000000000050c3000000000000'),
    0x0BC0A5DA: (11, 'daa5c00b0001000000010004000156556a138002000008010000000000000056556a1300000000d7899dd8893da9c0d7899dd8893da9400000000000000080aaaaaaaaecd4e34001000000000000000000000000000000584ff603000000000000000000000100000000000000000064000000'),
    0x21BB990C: (11, '0c99bb21000100000001000400012ee1850ef80200000801000000000000002ee1850e00000000d7899dd8893da9c0d7899dd8893da9400000000000000080aaaaaaaaecd4e34001000000000000000000000000000000584ff603000000000000000000000100000000000000000064000000'),
    0x21E1267C: (11, '7c26e12100010000000100040001c885120ef8020000080100000000000000c885120e00000000d7899dd8893da9c0d7899dd8893da9400000000000000080aaaaaaaaecd4e34001000000000000000000000000000000584ff603000000000000000000000100000000000000000064000000'),
}
def read_index(f):
    hdr = f.read(25); assert hdr[:4] == b'2KPR', 'not an RPKG v2 file'
    n, htab, itab = struct.unpack_from('<III', hdr, 13)
    hashes = f.read(htab); info = f.read(itab); q = 0
    for i in range(n):
        h, off, sz = struct.unpack_from('<QQI', hashes, i*20)
        typ = info[q:q+4][::-1]; rts, ds, sm, vm = struct.unpack_from('<IIII', info, q+4); q += 20
        ref = info[q:q+rts]; q += rts
        if h == BANK_HASH: return dict(off=off, csize=sz & 0x3FFFFFFF, enc=bool(sz & 0x80000000), size=ds, typ=typ, rts=rts, sm=sm, vm=vm, ref=ref)
    raise SystemExit('mx_mainmenu bank not found in chunk0.rpkg')
def read_resource(f, e):
    f.seek(e['off']); b = bytearray(f.read(e['csize'] or e['size']))
    if e['enc']:
        for i in range(len(b)): b[i] ^= KEY[i & 7]
    return lz4.block.decompress(bytes(b), uncompressed_size=e['size']) if e['csize'] else bytes(b)
def patch_bank(wbnk):
    bank = wbnk[6:]; assert bank[:4] == b'BKHD'
    out = bytearray(); p = 0
    while p < len(bank):
        tag = bank[p:p+4]; sz = struct.unpack_from('<I', bank, p+4)[0]; body = bank[p+8:p+8+sz]; p += 8+sz
        if tag == b'BKHD': body = bytes.fromhex(BKHD_LAUNCH)
        if tag == b'HIRC':
            n = struct.unpack_from('<I', body, 0)[0]; q = 4; objs = []
            for i in range(n):
                t = body[q]; s = struct.unpack_from('<I', body, q+1)[0]; pl = body[q+5:q+5+s]; q += 5+s
                oid = struct.unpack_from('<I', pl, 0)[0]
                if oid in RESTORE:
                    t2, hx = RESTORE[oid]; assert t2 == t; pl = bytes.fromhex(hx)
                objs.append(bytes([t]) + struct.pack('<I', len(pl)) + pl)
            body = struct.pack('<I', n) + b''.join(objs)
        out += tag + struct.pack('<I', len(body)) + body
    return wbnk[:2] + struct.pack('<I', len(out)) + bytes(out)
def write_patch(path, h, typ, data, rts, sm, vm, ref, chunk=0, patch=1):
    # RPKG v2 patch: 9-byte sub-header = 01 00 00 00 <chunk> 00 <patch> 78 78 (as in IOI's chunkN.rpkg and in
    # working community patches), then hash count / table sizes, empty deletion list, tables, raw data (flags 0).
    hdr = b'2KPR' + bytes([1,0,0,0,chunk,0,patch,0x78,0x78]) + struct.pack('<III', 1, 20, 20+rts) + struct.pack('<I', 0)
    off = len(hdr) + 20 + 20 + rts
    open(path, 'wb').write(hdr + struct.pack('<QQI', h, off, 0) + typ[::-1] + struct.pack('<IIII', rts, len(data), sm, vm) + ref + data)
if __name__ == '__main__':
    rt = sys.argv[1] if len(sys.argv) > 1 else '.'
    patch_no = int(sys.argv[2]) if len(sys.argv) > 2 else 1   # optional: patch slot, e.g. 2 -> chunk0patch2.rpkg
    f = open(os.path.join(rt, 'chunk0.rpkg'), 'rb'); e = read_index(f); cur = read_resource(f, e)
    md5 = hashlib.md5(cur).hexdigest(); print('current mx_mainmenu bank md5', md5, 'OK' if md5 == EXPECT_CURRENT_MD5 else 'UNEXPECTED (game updated? patch may still apply)')
    new = patch_bank(cur); md5n = hashlib.md5(new).hexdigest(); print('patched bank md5', md5n, 'OK' if md5n == EXPECT_PATCHED_MD5 else 'UNEXPECTED')
    out = os.path.join(rt, f'chunk0patch{patch_no}.rpkg'); write_patch(out, BANK_HASH, e['typ'], new, e['rts'], e['sm'], e['vm'], e['ref'], 0, patch_no); print('wrote', out, os.path.getsize(out), 'bytes')
