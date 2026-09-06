"""Research step 2: extract the current stem, dump the chunk1 campaign music bank 015750D5211B2EAE with wwiser and find
the MusicTrack that uses source 236D6A95 plus its parent chain. Arguments: scratch folder, output folder for the WAV.
"""
import sys, os, struct, subprocess, re, xml.etree.ElementTree as ET
sys.path.insert(0, 'tools')
from rpkg_read import load_index, read_resource, fnv1
S = sys.argv[1]; OUT = sys.argv[2]
RT = 'D:/SteamLibrary/steamapps/common/007 First Light/Runtime/'
IDX = {'chunk0': load_index('idx/new_chunk0.json'), 'chunk1': load_index('idx/new_chunk1.json')}
F = {c: open(RT + c + '.rpkg', 'rb') for c in IDX}
VG = os.path.abspath('external/vgmstream/vgmstream-cli.exe'); WW = os.path.abspath('external/wwiser/wwiser.pyz')
# 1. current swapped stem
e = IDX['chunk0']['by_hash']['015E589FC5DD9B12']; w = read_resource(F['chunk0'], e)
p = os.path.join(S, 'current_236D6A95.wem'); open(p, 'wb').write(w)
subprocess.run([VG, '-o', os.path.join(OUT, 'MX_Music_current_236D6A95.wav'), p], capture_output=True)
m = subprocess.run([VG, '-m', p], capture_output=True, text=True).stdout
print('current stem:', [l.strip() for l in m.splitlines() if 'sample rate' in l or 'play duration' in l or 'channels' in l])
# 2. the chunk1 music bank that references it
H = '015750D5211B2EAE'; e = IDX['chunk1']['by_hash'][H]; b = read_resource(F['chunk1'], e)
bd = os.path.join(S, 'banks'); open(os.path.join(bd, 'music_current.bnk'), 'wb').write(b[6:])
print('music bank', H, len(b), 'refs', len(e['refs']))
subprocess.run([sys.executable, WW, '-d', 'xml', 'music_current.bnk'], cwd=bd, capture_output=True)
x = open(os.path.join(bd, 'music_current.bnk.xml'), encoding='utf-8').read()
# event ids in the bank -> names via hash list WWEV names + fnv1
names = {}
for line in open('external/rpkg-cli/hash_list.txt', encoding='utf-8', errors='replace'):
    if line[16:21] == '.WWEV':
        n = line.rstrip('\n').split(',', 1)[1]; names[fnv1(n)] = n
evs = re.findall(r'<object name="CAkEvent" index="\d+">\s*<field type="tid" name="ulID" value="(\d+)"', x)
print('events in bank:', len(evs)); print(sorted(names.get(int(v), '?%08X' % int(v)) for v in evs)[:60])
# 3. where is source 236D6A95 used: MusicTrack -> parents -> switch states
tree = ET.parse(os.path.join(bd, 'music_current.bnk.xml')); root = tree.getroot()
objs = {}
for o in root.iter('object'):
    f = o.find('field[@name="ulID"]')
    if f is not None and o.get('name', '').startswith('CAk'): objs[int(f.get('value'))] = o
def fld(o, name):
    f = o.find('.//field[@name="%s"]' % name); return f.get('value') if f is not None else None
tracks = [oid for oid, o in objs.items() if o.get('name') == 'CAkMusicTrack' and any(f.get('value') == str(0x236D6A95) for f in o.iter('field') if f.get('name') == 'sourceID')]
print('tracks with source 236D6A95:', ['%08X' % t for t in tracks])
for t in tracks:
    chain = []; cur = t
    while cur in objs:
        o = objs[cur]; chain.append('%s %08X' % (o.get('name'), cur)); par = fld(o, 'DirectParentID'); cur = int(par) if par else 0
    print(' chain:', ' <- '.join(chain))
    o = objs[t]; print(' track fields:', {k: fld(o, k) for k in ('fSrcDuration', 'fPlayAt', 'fBeginTrimOffset', 'fEndTrimOffset', 'eTrackType')})
# switch containers: list their arguments (group ids) and decision tree leaf -> node
for oid, o in objs.items():
    if o.get('name') == 'CAkMusicSwitchCntr':
        groups = [f.get('value') for f in o.iter('field') if f.get('name') == 'ulGroup']
        print('MusicSwitch %08X groups %s' % (oid, groups))
