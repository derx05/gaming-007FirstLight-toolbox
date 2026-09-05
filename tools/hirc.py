import struct, sys
TYPES={1:'State',2:'Sound',3:'Action',4:'Event',5:'RanSeqCntr',6:'SwitchCntr',7:'ActorMixer',8:'Bus',9:'LayerCntr',10:'MusicSegment',11:'MusicTrack',12:'MusicSwitchCntr',13:'MusicRanSeqCntr',14:'Attenuation',15:'DialogueEvent',16:'FxShareSet',17:'FxCustom',18:'AuxBus',19:'LFO',20:'Envelope',21:'AudioDevice',22:'TimeMod'}
def load(path):
    b=open(path,'rb').read()
    assert b[:4]==b'BKHD'
    p=0; objs={}; order=[]
    while p<len(b):
        tag=b[p:p+4]; sz=struct.unpack_from('<I',b,p+4)[0]; body=b[p+8:p+8+sz]
        if tag==b'HIRC':
            n=struct.unpack_from('<I',body,0)[0]; q=4
            for i in range(n):
                t=body[q]; s=struct.unpack_from('<I',body,q+1)[0]; pl=body[q+5:q+5+s]
                oid=struct.unpack_from('<I',pl,0)[0]
                objs[oid]=(t,pl); order.append(oid)
                q+=5+s
            assert q==len(body),(q,len(body))
        p+=8+sz
    return objs,order
if __name__=='__main__':
    o,oo=load('/mnt/user-data/uploads/main_old.bnk'); n,no=load('/mnt/user-data/uploads/main_new.bnk')
    print('old objs',len(o),'new objs',len(n))
    from collections import Counter
    print('old types',Counter(TYPES.get(t,t) for t,_ in o.values()))
    added=[i for i in no if i not in o]; removed=[i for i in oo if i not in n]
    changed=[i for i in oo if i in n and o[i]!=n[i]]
    print('added',len(added),'removed',len(removed),'changed',len(changed))
    print('added types',Counter(TYPES.get(n[i][0],n[i][0]) for i in added))
    print('removed types',Counter(TYPES.get(o[i][0],o[i][0]) for i in removed))
    print('changed types',Counter(TYPES.get(o[i][0],o[i][0]) for i in changed))
    for i in changed: print('CHG',TYPES.get(o[i][0]),f'{i:08X} ({i})',len(o[i][1]),'->',len(n[i][1]))
    for i in removed: print('REM',TYPES.get(o[i][0]),f'{i:08X} ({i})',len(o[i][1]))
    for i in added: print('ADD',TYPES.get(n[i][0]),f'{i:08X} ({i})',len(n[i][1]))
