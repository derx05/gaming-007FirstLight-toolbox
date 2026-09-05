import sys, struct, re, time
sys.path.insert(0,'tools')
from rpkg_read import *
GAME='D:/SteamLibrary/steamapps/common/007 First Light/Runtime/'
TARGET_EV={0x231B00B3:'sting?',0x5568B80E:'ev-RanSeq34B3E967',0x4472FDBA:'ev-Layer3D980D03',0xD6E009E8:'ev-Layer39492C8D'}
MEDIA={b'\x38\xFA\xFE\x36':'mediaA_36FEFA38',b'\xEF\x39\x3D\x0F':'mediaB_0F3D39EF',b'\xB3\x00\x1B\x23':'evid_231B00B3'}
out=open('idx/wwev_names_all.txt','w',encoding='utf-8')
t=time.time()
for chunk in ('chunk1','chunk0'):
    d=load_index(f'idx/new_{chunk}.json'); f=open(GAME+chunk+'.rpkg','rb')
    ents=[e for e in d['entries'] if e['type']=='WWEV']; ents.sort(key=lambda e:e['off'])
    for e in ents:
        b=read_resource(f,e)
        nl=struct.unpack_from('<I',b,0)[0]; name=b[4:4+nl].rstrip(b'\0').decode('latin1')
        h=fnv1(name); hits=[v for k,v in MEDIA.items() if k in b]
        out.write(f"{chunk}\t{e['hash']}\t{e['size']}\t{h:08X}\t{name}\t{','.join(hits)}\n")
        if h in TARGET_EV or hits: print('HIT',chunk,e['hash'],e['size'],'%08X'%h,name,TARGET_EV.get(h,''),hits,flush=True)
    print(chunk,'done',len(ents),'%.0fs'%(time.time()-t),flush=True)
