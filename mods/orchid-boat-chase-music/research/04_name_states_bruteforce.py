"""Research step 4: FNV-1 brute force of group/state ids against tokens from the hash list. Resolved State_MX_GameFlow,
Campaign/Global and the mission states m01_clover .. m10_ivy; the section-level names stayed unresolved (a wider
second pass produced only 32-bit collisions). Argument: scratch folder.
"""
import sys, os, re, xml.etree.ElementTree as ET
sys.path.insert(0, 'tools'); from rpkg_read import fnv1
S = sys.argv[1]; bd = os.path.join(S, 'banks')
root = ET.parse(os.path.join(bd, 'music_current.bnk.xml')).getroot()
objs = {}
for o in root.iter('object'):
    f = o.find('field[@name="ulID"]')
    if f is not None and o.get('name','').startswith('CAk'): objs[int(f.get('value'))] = o
def fld(o, n):
    f = o.find('.//field[@name="%s"]' % n); return f.get('value') if f is not None else None
chain = [0x0AC8C49D, 0x0EDE3B03, 0x17908951, 0x1A10CFAB]
targets = {}   # id -> role
for sw in chain:
    o = objs[sw]
    for f in o.iter('field'):
        if f.get('name') == 'ulGroup': targets[int(f.get('value'))] = 'group of %08X' % sw
    for n in o.iter('object'):
        if n.get('name') == 'Node' and fld(n, 'key') not in (None, '0'): targets[int(fld(n, 'key'))] = 'state in %08X' % sw
print(len(targets), 'ids to name')
toks = set()
for line in open('external/rpkg-cli/hash_list.txt', encoding='utf-8', errors='replace'):
    for t in re.split(r'[^A-Za-z0-9_]+', line[22:]):
        if 2 <= len(t) <= 40: toks.add(t.lower())
for t in list(toks):
    for part in t.split('_'):
        if len(part) >= 2: toks.add(part)
print(len(toks), 'candidate tokens')
extra = ['none', 'default', 'off', 'on', 'intro', 'outro', 'combat', 'stealth', 'explore', 'chase', 'boat', 'boatchase', 'boat_chase', 'action', 'tension', 'ambient', 'calm', 'menu', 'end', 'start', 'high', 'low', 'medium', 'mid']
toks |= set(extra)
prefixes = ['', 'state_', 'state_mx_', 'mx_', 'sw_', 'mx_sw_', 'switch_', 'music_', 'mx_state_', 'state_music_', 'mission_', 'level_', 'mx_mission_', 'mx_level_']
suffixes = ['', '_mx', '_music', '_state', '_sw']
found = {}
for t in toks:
    for p in prefixes:
        for s in suffixes:
            h = fnv1(p + t + s)
            if h in targets and h not in found: found[h] = p + t + s
for h, role in sorted(targets.items(), key=lambda kv: kv[1]):
    print('%-22s %10d  %s' % (role, h, found.get(h, '?')))
