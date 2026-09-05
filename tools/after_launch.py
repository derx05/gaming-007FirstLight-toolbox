"""Compare two builds' chunk0 (default: the launch build in versions/ vs the installed game).
Usage: python tools/after_launch.py [OLD.rpkg] [NEW.rpkg] [outdir]
1) index-level + byte-exact diff vs the 06-11 build, 2) extract every changed/removed WWEM, WBNK,
WWEV from the launch build into audio/launch/, 3) convert wems to wav, 4) flag the menu-music clips."""
import sys, os, json, subprocess, struct
sys.path.insert(0,'tools')
from rpkg_index import parse
from rpkg_read import read_resource, read_raw
LAUNCH=sys.argv[1] if len(sys.argv)>1 else 'versions/launch_2026-05-27_manifest_7322178669849310269/Runtime/chunk0.rpkg'
OLD=sys.argv[2] if len(sys.argv)>2 else 'D:/SteamLibrary/steamapps/common/007 First Light/Runtime/chunk0.rpkg'
OUT=sys.argv[3] if len(sys.argv)>3 else 'research/extracted'
VG=os.path.abspath('vgmstream/vgmstream-cli.exe')
mm=json.load(open('tools/media_map.json'))
menu={e['rpkg_hash']:(grp,e['wem_id']) for grp in ('splash','theme') for e in mm[grp]}
L=parse(LAUNCH); O=parse(OLD); lh={e['hash']:e for e in L['entries']}; oh={e['hash']:e for e in O['entries']}
print('launch files',L['nfiles'],'new files',O['nfiles'])
fl=open(LAUNCH,'rb'); fo=open(OLD,'rb')
T={'WWEM','WWES','WWEV','WBNK','WSWB','WSWT','WSGB','WSGT','WEMD','GFXV'}
changed=[]; removed=[]; added=[]
for h,e in lh.items():
    if e['type'] not in T: continue
    if h not in oh: removed.append(h); continue
    o=oh[h]
    if (e['size'],e['csize'])!=(o['size'],o['csize']) or read_raw(fl,e)!=read_raw(fo,o): changed.append(h)
for h,e in oh.items():
    if e['type'] in T and h not in lh: added.append(h)
from collections import Counter
print('changed (launch->new):',Counter(lh[h]['type'] for h in changed))
print('only in launch:',Counter(lh[h]['type'] for h in removed)); print('only in new:',Counter(oh[h]['type'] for h in added))
names={}
want=set(changed+removed+added)
for line in open('rpkg-cli/hash_list.txt',encoding='utf-8',errors='replace'):
    if line[:16].upper() in want: names[line[:16].upper()]=line.strip()[17:]
for tag,lst,src in (('CHG',changed,lh),('LAUNCH-ONLY',removed,lh),('new-ONLY',added,oh)):
    for h in lst:
        e=src[h]; m=menu.get(h); print(f" {tag} {e['type']} {h} {e['size']}", f"MENU {m[0]} wem {m[1]}" if m else '', names.get(h,'')[:90])
# extract launch versions of changed/launch-only WWEM+WBNK+WWEV, plus new versions of changed for A/B
for h in changed+removed:
    e=lh[h]
    if e['type'] in ('WWEM','WBNK','WWEV'):
        b=read_resource(fl,e); m=menu.get(h); base=f"{OUT}/{(m[1]+'_') if m else ''}{h}"
        open(base+'.launch.'+e['type'],'wb').write(b)
        if h in oh: open(base+'.new.'+e['type'],'wb').write(read_resource(fo,oh[h]))
        if e['type']=='WWEM':
            for v in ('launch','new'):
                p=f"{base}.{v}.WWEM"
                if os.path.exists(p): subprocess.run([VG,'-o',f"{base}.{v}.wav",p],capture_output=True)
print('extracted to',OUT); print(sorted(os.listdir(OUT)))
json.dump(dict(changed=changed,launch_only=removed,only_new=added),open('idx/diff_launch_vs_new_audio.json','w'),indent=1)
