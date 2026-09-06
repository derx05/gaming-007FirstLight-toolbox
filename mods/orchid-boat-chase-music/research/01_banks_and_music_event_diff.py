"""Research step 1 (run from the repo root, needs idx/new_chunk0.json, idx/new_chunk1.json, idx/launch_chunk0.json from
tools/rpkg_index.py and external/rpkg-cli/hash_list.txt). Names every WBNK, byte-diffs all WBNK/WWEV/WWEM of chunk0
launch vs current, and diffs the media list of the in-game music event MX_Music_SW_Play. Result: exactly one stem swapped
(3E5F24AC -> 236D6A95). Argument: output folder. The vgmstream call at the end needs an absolute path on Windows.
"""
import sys, os, struct, subprocess, json
sys.path.insert(0, 'tools')
from rpkg_read import load_index, read_resource, fnv1
S = sys.argv[1]
RT = 'D:/SteamLibrary/steamapps/common/007 First Light/Runtime/'
LAUNCH = 'versions/launch_2026-05-27_manifest_7322178669849310269/Runtime/chunk0.rpkg'
names = {}
for line in open('external/rpkg-cli/hash_list.txt', encoding='utf-8', errors='replace'):
    if line[16:17] == '.' and line[17:21] in ('WBNK', 'WWEV', 'WWEM'):
        h, rest = line[:16], line.rstrip('\n')
        names[h] = rest.split(',', 1)[1]
IDX = {'chunk0': load_index('idx/new_chunk0.json'), 'chunk1': load_index('idx/new_chunk1.json')}
L = load_index('idx/launch_chunk0.json')
F = {c: open(RT + c + '.rpkg', 'rb') for c in IDX}; FL = open(LAUNCH, 'rb')
def find(h):
    for c, d in IDX.items():
        if h in d['by_hash']: return c, d['by_hash'][h]
# A. bank names + which bank contains the MX_Music_SW_Play event
ev = fnv1('MX_Music_SW_Play'); evb = struct.pack('<I', ev)
print('MX_Music_SW_Play id %08X' % ev)
print('--- banks (chunk, hash, size, name, has-event)')
for c, d in IDX.items():
    for e in sorted((e for e in d['entries'] if e['type'] == 'WBNK'), key=lambda e: names.get(e['hash'], '~')):
        b = read_resource(F[c], e)
        print(c, e['hash'], e['size'], names.get(e['hash'], '?'), 'HAS_EVENT' if evb in b else '')
# C. WBNK/WWEV changed between launch chunk0 and current chunk0
print('--- chunk0 WBNK/WWEV/WWEM differences launch -> current')
cur = IDX['chunk0']['by_hash']
for t in ('WBNK', 'WWEV', 'WWEM'):
    for h, e in L['by_hash'].items():
        if e['type'] != t: continue
        if h not in cur: print(t, h, 'REMOVED', names.get(h, '?')); continue
        n = cur[h]
        if (e['size'], e['csize']) != (n['size'], n['csize']) or read_resource(FL, e) != read_resource(F['chunk0'], n):
            print(t, h, 'CHANGED', names.get(h, '?'), e['size'], '->', n['size'])
    for h, e in cur.items():
        if e['type'] == t and h not in L['by_hash']: print(t, h, 'ADDED', names.get(h, '?'))
# B. the MX_Music_SW_Play WWEV: media lists launch vs current
def wwev(b, refs):
    nl = struct.unpack_from('<I', b, 0)[0]; p = 4 + nl; name = b[4:p-1].decode()
    u8, f32, nA, nEmb = struct.unpack_from('<BfII', b, p); p += 13; emb = []; st = []
    for i in range(nEmb):
        i1, i2, sz = struct.unpack_from('<III', b, p); emb.append('%08X' % i1); p += 12 + sz
    nS = struct.unpack_from('<I', b, p)[0]; p += 4
    for i in range(nS):
        di, i1, i2, pf = struct.unpack_from('<IIII', b, p); st.append(('%08X' % i1, refs[di][1])); p += 16 + pf
    return name, emb, st
H = '01A872A294A76EAD'
c, e = find(H); nb = read_resource(F[c], e); nn, nemb, nst = wwev(nb, e['refs'])
le = L['by_hash'][H]; lb = read_resource(FL, le); ln, lemb, lst = wwev(lb, le['refs'])
print('--- WWEV', H, nn, 'in', c, 'launch: emb', len(lemb), 'streamed', len(lst), '| current: emb', len(nemb), 'streamed', len(nst))
ls, ns = dict(lst), dict(nst)
for k in sorted(set(ls) | set(ns)):
    if ls.get(k) != ns.get(k): print('  ', k, 'launch', ls.get(k), 'current', ns.get(k))
json.dump({'launch': lst, 'current': nst}, open(os.path.join(S, 'mx_music_media.json'), 'w'), indent=1)
# extract the swapped wems and convert to wav
VG = 'external/vgmstream/vgmstream-cli.exe'
for tag, wid, wh, src in (('launch', '3E5F24AC', ls.get('3E5F24AC'), (FL, L)), ('current', '236D6A95', ns.get('236D6A95'), (F['chunk0'], IDX['chunk0']))):
    if wh and wh in src[1]['by_hash']:
        w = read_resource(src[0], src[1]['by_hash'][wh]); p = os.path.join(S, f'{tag}_{wid}.wem'); open(p, 'wb').write(w)
        subprocess.run([VG, '-o', p[:-4] + '.wav', p], capture_output=True); print('wrote', p[:-4] + '.wav', len(w))
    else: print(tag, wid, 'wem hash', wh, 'not found in that archive')
