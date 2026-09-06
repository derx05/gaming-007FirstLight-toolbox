"""Research step 3: resolve which switch-group states lead from the top music switch to the swapped track (decision
tree keys of each CAkMusicSwitchCntr on the parent chain). Argument: scratch folder holding banks/music_current.bnk.xml.
"""
import sys, os, xml.etree.ElementTree as ET
S = sys.argv[1]; bd = os.path.join(S, 'banks')
root = ET.parse(os.path.join(bd, 'music_current.bnk.xml')).getroot()
objs = {}
for o in root.iter('object'):
    f = o.find('field[@name="ulID"]')
    if f is not None and o.get('name', '').startswith('CAk'): objs[int(f.get('value'))] = o
def fld(o, name):
    f = o.find('.//field[@name="%s"]' % name); return f.get('value') if f is not None else None
def tree_path(sw, target):
    """decision tree of a MusicSwitchCntr: list (group, state) pairs leading to child node 'target'."""
    groups = [int(f.get('value')) for f in sw.iter('field') if f.get('name') == 'ulGroup']
    nodes = [n for n in sw.iter('object') if n.get('name') == 'Node']
    res = []
    for n in nodes:
        key = fld(n, 'key'); aid = fld(n, 'audioNodeId')
        if aid == str(target): res.append(int(key))
    return groups, res
chain = [0x11CF0184, 0x1A10CFAB, 0x17908951, 0x0EDE3B03, 0x0AC8C49D]
for child, parent in zip(chain, chain[1:]):
    g, keys = tree_path(objs[parent], child)
    print('switch %08X groups %s -> child %08X via state keys %s' % (parent, g, child, keys))
# also every leaf in the innermost switch 1A10CFAB: key -> node type
sw = objs[0x1A10CFAB]
for n in sw.iter('object'):
    if n.get('name') == 'Node':
        k, a = fld(n, 'key'), fld(n, 'audioNodeId')
        if a and int(a) in objs: print('  1A10CFAB leaf key %s -> %s %08X' % (k, objs[int(a)].get('name'), int(a)))
# playlist of 11CF0184 and segments' tracks
rs = objs[0x11CF0184]
print('RanSeq 11CF0184 playlist items:', [(fld(i, 'SegmentID'), fld(i, 'eRSType'), fld(i, 'Loop')) for i in rs.iter('object') if i.get('name') == 'PlaylistItem' or i.get('name') == 'AkMusicRanSeqPlaylistItem'][:20])
seg = objs[0x06C8404A]
print('Segment 06C8404A children:', [fld(c, 'ulChildID') for c in seg.iter('field') if c.get('name') == 'ulChildID'], 'dur', fld(seg, 'fDuration'))
for c in seg.iter('field'):
    if c.get('name') == 'ulChildID':
        t = objs[int(c.get('value'))]; print('  track %08X sources' % int(c.get('value')), ['%08X' % int(f.get('value')) for f in t.iter('field') if f.get('name') == 'sourceID'])
# which states does the group of 1A10CFAB have overall (all keys)
