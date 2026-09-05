"""Diff two chunk RPKGs (e.g. launch chunk0 vs 06-11 chunk0) at index level, then byte-compare
same-size entries of the audio/UI types. Usage: python tools/diff_rpkg.py OLD.rpkg NEW.rpkg [out.json]"""
import sys, json, time, os
sys.path.insert(0,os.path.dirname(__file__))
from rpkg_index import parse
from rpkg_read import read_raw
from collections import Counter
po,pn=sys.argv[1],sys.argv[2]; out=sys.argv[3] if len(sys.argv)>3 else None
t=time.time(); o=parse(po); n=parse(pn); print('indexed in %.0fs'%(time.time()-t))
oh={e['hash']:e for e in o['entries']}; nh={e['hash']:e for e in n['entries']}
added=[h for h in nh if h not in oh]; removed=[h for h in oh if h not in nh]
sizediff=[h for h in oh if h in nh and (oh[h]['size'],oh[h]['csize'])!=(nh[h]['size'],nh[h]['csize'])]
print('added',Counter(nh[h]['type'] for h in added)); print('removed',Counter(oh[h]['type'] for h in removed))
print('size-changed',Counter(oh[h]['type'] for h in sizediff))
AUDIO={'WWEM','WWES','WWEV','WBNK','WSWB','WSWT','WSGB','WSGT','WEMD','GFXV','XMLB','GFXF','TEMP','TBLU','JSON','ORES','UICB','UICT'}
for h in sizediff:
    if oh[h]['type'] in AUDIO: print(' SIZE',oh[h]['type'],h,oh[h]['size'],'->',nh[h]['size'])
for h in added:
    if nh[h]['type'] in AUDIO: print(' ADD',nh[h]['type'],h,nh[h]['size'])
for h in removed:
    if oh[h]['type'] in AUDIO: print(' REM',oh[h]['type'],h,oh[h]['size'])
cand=[h for h in oh if h in nh and h not in sizediff and oh[h]['type'] in AUDIO]
tot=sum(oh[h]['csize'] or oh[h]['size'] for h in cand); print('byte-compare',len(cand),'entries, %.2f GB'%(tot/1e9),flush=True)
fo=open(po,'rb'); fn=open(pn,'rb'); bytediff=[]; t=time.time()
for h in sorted(cand,key=lambda h:oh[h]['off']):
    if read_raw(fo,oh[h])!=read_raw(fn,nh[h]): bytediff.append(h)
print('byte-changed',Counter(oh[h]['type'] for h in bytediff),'%.0fs'%(time.time()-t))
for h in bytediff: print(' BYTES',oh[h]['type'],h,oh[h]['size'])
if out: json.dump(dict(added=added,removed=removed,sizediff=sizediff,bytediff=bytediff),open(out,'w'),indent=1)
