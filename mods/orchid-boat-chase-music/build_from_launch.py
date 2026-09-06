"""Restore the launch-build music stem of the mission 9 (Orchid) boat chase.

Update 1.0.2/1.0.3 replaced one stem of the in-game music event MX_Music_SW_Play: Wwise source 3E5F24AC
(WWEM 0164B2AAA73D4801, launch) became 236D6A95 (WWEM 015E589FC5DD9B12, current). Same length (1:13.7), new
recording. The old audio no longer exists in the current game, so this mod needs the launch archive to build:

    python build_from_launch.py "<launch>/Runtime/chunk0.rpkg" "<game>/Runtime" [patch number, default 2] [--manifest]

It writes chunk0patch<N>.rpkg next to this file, containing two resources:
  - WWEM 015E589FC5DD9B12  = the launch stem (the audio the current bank's track now points at)
  - WWEV 01A872A294A76EAD  = the current music event with that stream's prefetch snippet swapped to the launch stem's
Nothing else changes: bank, ids and reference tables stay as in the current game.
--manifest additionally writes a packagedefinition.txt with patchlevel=310 (only needed if you have no other mod installed).
Needs python + lz4. No audio is stored in this script.
"""
import hashlib, os, struct, sys
import lz4.block

KEY = bytes([0xDC, 0x45, 0xA6, 0x9C, 0xD3, 0x72, 0x4C, 0xAB])
WWEV = 0x01A872A294A76EAD          # mx_music_sw_play
WWEM_CUR = 0x015E589FC5DD9B12      # current stem resource (source id 236D6A95)
WWEM_LAUNCH = 0x0164B2AAA73D4801   # launch stem resource (source id 3E5F24AC)
SRC_CUR, SRC_LAUNCH = 0x236D6A95, 0x3E5F24AC
MD5_LAUNCH_WEM = '2089fbc97454c9ea279f7dd772d04c1f'   # the launch stem as shipped in manifest 7322178669849310269
HERE = os.path.dirname(os.path.abspath(__file__))

def read_index(f, wanted):
    """{hash: entry} for the wanted hashes of an RPKG v2 (entry keeps the raw reference table bytes)."""
    hdr = f.read(25); assert hdr[:4] == b'2KPR', 'not an RPKG v2 file'
    n, htab, itab = struct.unpack_from('<III', hdr, 13)
    if hdr[10] != 0:                      # patch file: skip the deletion list
        cnt = struct.unpack('<I', f.read(4))[0]; f.read(8 * cnt)
    hashes = f.read(htab); info = f.read(itab); q = 0; out = {}
    for i in range(n):
        h, off, sz = struct.unpack_from('<QQI', hashes, i * 20)
        typ = info[q:q + 4][::-1]; rts, ds, sm, vm = struct.unpack_from('<IIII', info, q + 4); q += 20
        ref = info[q:q + rts]; q += rts
        if h in wanted:
            out[h] = dict(off=off, csize=sz & 0x3FFFFFFF, enc=bool(sz & 0x80000000), size=ds, typ=typ, rts=rts, sm=sm, vm=vm, ref=ref)
    missing = [x for x in wanted if x not in out]
    assert not missing, 'missing resources: ' + ' '.join('%016X' % x for x in missing)
    return out

def read_resource(f, e):
    f.seek(e['off']); b = bytearray(f.read(e['csize'] or e['size']))
    if e['enc']:
        for i in range(len(b)): b[i] ^= KEY[i & 7]
    return lz4.block.decompress(bytes(b), uncompressed_size=e['size']) if e['csize'] else bytes(b)

def stream_entry(wwev, src):
    """(offset of the 16-byte streamed-entry header, dependIdx, prefetchSize) for Wwise source id `src`."""
    nl = struct.unpack_from('<I', wwev, 0)[0]; p = 4 + nl
    nEmb = struct.unpack_from('<I', wwev, p + 9)[0]; p += 13
    for _ in range(nEmb):
        p += 12 + struct.unpack_from('<I', wwev, p + 8)[0]
    nS = struct.unpack_from('<I', wwev, p)[0]; p += 4
    for _ in range(nS):
        di, i1, i2, pf = struct.unpack_from('<IIII', wwev, p)
        if i1 == src: return p, di, pf
        p += 16 + pf
    raise SystemExit('source %08X not in WWEV' % src)

def write_patch(path, resources, chunk, patch):
    """resources: list of (hash, type bytes, data, ref bytes, sysmem, vidmem); stored raw (flags 0)."""
    n = len(resources); itab = sum(20 + len(r[3]) for r in resources)
    hdr = b'2KPR' + bytes([1, 0, 0, 0, chunk, 0, patch, 0x78, 0x78]) + struct.pack('<III', n, 20 * n, itab) + struct.pack('<I', 0)
    off = len(hdr) + 20 * n + itab; ht = b''; it = b''; body = b''
    for h, typ, data, ref, sm, vm in resources:
        ht += struct.pack('<QQI', h, off, 0); it += typ[::-1] + struct.pack('<IIII', len(ref), len(data), sm, vm) + ref
        body += data; off += len(data)
    open(path, 'wb').write(hdr + ht + it + body)

def build(launch, rt, patch=2, manifest=False, outdir=HERE):
    with open(launch, 'rb') as f:
        li = read_index(f, {WWEM_LAUNCH, WWEV}); launch_wem = read_resource(f, li[WWEM_LAUNCH]); launch_ev = read_resource(f, li[WWEV])
    with open(os.path.join(rt, 'chunk0.rpkg'), 'rb') as f:
        ci = read_index(f, {WWEM_CUR, WWEV}); cur_ev = read_resource(f, ci[WWEV])
    md5 = hashlib.md5(launch_wem).hexdigest(); print('launch stem %d bytes md5 %s' % (len(launch_wem), md5))
    assert md5 == MD5_LAUNCH_WEM, 'this is not the launch stem - is the first argument the launch-build chunk0.rpkg?'
    lp, ldi, lpf = stream_entry(launch_ev, SRC_LAUNCH); cp, cdi, cpf = stream_entry(cur_ev, SRC_CUR)
    assert launch_ev[lp + 16:lp + 16 + lpf] == launch_wem[:lpf], 'launch prefetch is not the head of the launch stem'
    # current event, same entry, prefetch replaced by the launch stem's head (ids and dependIdx untouched)
    new_ev = cur_ev[:cp] + struct.pack('<IIII', cdi, SRC_CUR, SRC_CUR, lpf) + launch_wem[:lpf] + cur_ev[cp + 16 + cpf:]
    print('WWEV: prefetch %d -> %d bytes, size %d -> %d' % (cpf, lpf, len(cur_ev), len(new_ev)))
    out = os.path.join(outdir, 'chunk0patch%d.rpkg' % patch)
    e = ci[WWEM_CUR]; ev = ci[WWEV]
    write_patch(out, [(WWEV, b'WWEV', new_ev, ev['ref'], ev['sm'], ev['vm']), (WWEM_CUR, b'WWEM', launch_wem, e['ref'], e['sm'], e['vm'])], 0, patch)
    print('wrote', out, os.path.getsize(out), 'bytes')
    with open(out, 'rb') as f:                      # verify by reading it back
        vi = read_index(f, {WWEM_CUR, WWEV})
        assert read_resource(f, vi[WWEM_CUR]) == launch_wem and read_resource(f, vi[WWEV]) == new_ev
    print('verified: patch reads back correctly')
    if manifest:
        sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools')); import pkgdef
        src = open(os.path.join(rt, 'packagedefinition.txt'), 'rb').read(); hdr, crc, plain = pkgdef.decrypt(src)
        mp = os.path.join(outdir, 'packagedefinition.txt')
        open(mp, 'wb').write(pkgdef.encrypt(hdr, plain.replace(b'patchlevel=0', b'patchlevel=310'))); print('wrote', mp, '(patchlevel=310)')
    return out

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) < 2:
        raise SystemExit(__doc__)
    build(args[0], args[1], int(args[2]) if len(args) > 2 else 2, '--manifest' in sys.argv)
