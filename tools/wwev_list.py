import sys,struct,json
def parse(path,refs):
    b=open(path,'rb').read(); nl=struct.unpack_from('<I',b,0)[0]; p=4+nl; name=b[4:p-1].decode()
    u8,f32,nA,nEmb=struct.unpack_from('<BfII',b,p); p+=13; emb=[]; st=[]
    for i in range(nEmb):
        i1,i2,sz=struct.unpack_from('<III',b,p); emb.append(('%08X'%i1,sz)); p+=12+sz
    nS=struct.unpack_from('<I',b,p)[0]; p+=4
    for i in range(nS):
        di,i1,i2,pf=struct.unpack_from('<IIII',b,p); st.append(('%08X'%i1,refs[di][1] if di<len(refs) else '??',pf)); p+=16+pf
    assert p==len(b),(p,len(b))
    return name,emb,st
h=sys.argv[1]
L=json.load(open('idx/launch_chunk0.json')); O=json.load(open('idx/old_chunk0.json'))
lr={e['hash']:e['refs'] for e in L['entries'] if e['hash']==h}[h]; orr={e['hash']:e['refs'] for e in O['entries'] if e['hash']==h}[h]
n1,e1,s1=parse(f'audio/launch/{h}.launch.WWEV',lr); n2,e2,s2=parse(f'audio/launch/{h}.0611.WWEV',orr)
print(n1,'launch: embedded',len(e1),'streamed',len(s1),'| 0611: embedded',len(e2),'streamed',len(s2))
S1={x[0]:x for x in s1}; S2={x[0]:x for x in s2}
for w in S1:
    if w not in S2: print(' LAUNCH-ONLY streamed wem',S1[w])
    elif S1[w][1]!=S2[w][1]: print(' CHANGED ref',S1[w],'->',S2[w])
for w in S2:
    if w not in S1: print(' 0611-ONLY streamed wem',S2[w])
E1={x[0]:x for x in e1}; E2={x[0]:x for x in e2}
for w in set(E1)|set(E2):
    if E1.get(w)!=E2.get(w): print(' embedded diff',w,E1.get(w),E2.get(w))
print(' order launch',[x[0] for x in s1][:12],'...'); print(' order 0611  ',[x[0] for x in s2][:12],'...')
