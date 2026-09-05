import sys,struct,re,subprocess,os
sys.path.insert(0,'tools')
from rpkg_read import *
GAME='D:/SteamLibrary/steamapps/common/007 First Light/Runtime/'
IDX={c:load_index(f'idx/new_{c}.json') for c in ('chunk0','chunk1')}
def find(h):
    for c,d in IDX.items():
        if h in d['by_hash']: return c,d['by_hash'][h]
def get(h):
    c,e=find(h); f=open(GAME+c+'.rpkg','rb'); return c,e,read_resource(f,e)
h=sys.argv[1]; out=sys.argv[2]
c,e,b=get(h); open(f'{out}/{h}.WWEV','wb').write(b)
print(c,'size',len(b),'refs',[(hex(fl),hh,(find(hh) or ('?',{}))[0],(find(hh) or ('?',{'type':'?'}))[1].get('type')) for fl,hh in e['refs']])
nl=struct.unpack_from('<I',b,0)[0]; p=4+nl; name=b[4:p-1].decode(); print('name',name,'fnv1 %08X'%fnv1(name))
u8,f32,nA,nEmb=struct.unpack_from('<BfII',b,p); p+=13; print('u8',u8,'f32',f32,'nA',nA,'nEmbedded',nEmb)
for i in range(nEmb):
    i1,i2,sz=struct.unpack_from('<III',b,p); print(' embedded',i,'id %08X %08X'%(i1,i2),'size',sz,'head',b[p+12:p+16]); 
    open(f'{out}/{i1:08X}.wem','wb').write(b[p+12:p+12+sz]); p+=12+sz
nS=struct.unpack_from('<I',b,p)[0]; p+=4; print('nStreamed',nS)
for i in range(nS):
    di,i1,i2,pf=struct.unpack_from('<IIII',b,p); print(' streamed',i,'dependIdx',di,'id %08X %08X'%(i1,i2),'prefetch',pf,'ref->',e['refs'][di] if di<len(e['refs']) else '??'); p+=16+pf
    ref=e['refs'][di][1]; cc,ee,bb=get(ref); open(f'{out}/{i1:08X}.wem','wb').write(bb); print('   WWEM',ref,cc,ee['type'],len(bb),bb[:4])
print('pos',p,'of',len(b),'tail',b[p:].hex())
for w in sorted(os.listdir(out)):
    if w.endswith('.wem'):
        r=subprocess.run(['vgmstream/vgmstream-cli.exe','-o',f'{out}/{w[:-4]}.wav',f'{out}/{w}'],capture_output=True,text=True); print(w,'->',r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[-200:])
