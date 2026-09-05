import sys,struct
sys.path.insert(0,'handoff_tools/handoff_tools')
from hirc import TYPES
def load_wbnk(p):
    b=open(p,'rb').read(); b=b[6:] if b[:4]!=b'BKHD' else b
    assert b[:4]==b'BKHD'
    objs={}; order=[]; q=0
    while q<len(b):
        tag=b[q:q+4]; sz=struct.unpack_from('<I',b,q+4)[0]; body=b[q+8:q+8+sz]
        if tag==b'HIRC':
            n=struct.unpack_from('<I',body,0)[0]; p=4
            for i in range(n):
                t=body[p]; s=struct.unpack_from('<I',body,p+1)[0]; pl=body[p+5:p+5+s]; oid=struct.unpack_from('<I',pl,0)[0]
                objs[oid]=(t,pl); order.append(oid); p+=5+s
        q+=8+sz
    return objs,order
if __name__=='__main__':
    names={}
    for line in open('idx/wwev_names_all.txt',encoding='utf-8'):
        c,h,sz,fnv,name,hits=line.rstrip('\n').split('\t'); names[int(fnv,16)]=name
    a,ao=load_wbnk(sys.argv[1]); b,bo=load_wbnk(sys.argv[2]); full=len(sys.argv)>3
    print(sys.argv[1],len(a),'objs ->',sys.argv[2],len(b))
    added=[i for i in bo if i not in a]; removed=[i for i in ao if i not in b]; changed=[i for i in ao if i in b and a[i]!=b[i]]
    print('added',len(added),'removed',len(removed),'changed',len(changed))
    def desc(objs,i):
        t,pl=objs[i]; s=f"{TYPES.get(t,t)} {i:08X} ({i}) len {len(pl)}"
        if t==2: s+=' media %08X (%d) stream %d'%(struct.unpack_from('<I',pl,9)[0],struct.unpack_from('<I',pl,9)[0],pl[8])
        if t==11:  # MusicTrack: sources after id: u8 flags, u32 numSources, then per source: plugin u32, streamType u8, sourceId u32, inMemSize u32, bits u8
            n=struct.unpack_from('<I',pl,5)[0]; p=9; srcs=[]
            for k in range(n): srcs.append('%08X'%struct.unpack_from('<I',pl,p+5)[0]); p+=14
            s+=' sources '+','.join(srcs)
        if t==4: s+=' name '+names.get(i,'?')
        return s
    for i in removed: print('REM',desc(a,i)); 
    for i in added: print('ADD',desc(b,i))
    for i in changed:
        print('CHG',desc(a,i),'->',len(b[i][1]))
        if full or len(a[i][1])<400: print('   OLD',a[i][1].hex()); print('   NEW',b[i][1].hex())
