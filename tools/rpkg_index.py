"""Parse an RPKG v2 (2KPR) index without extracting data.
Usage: python rpkg_index.py <rpkg> <out.json>
Writes a JSON list of entries: hash, off, csize(low30), enc(bit31), type, refTableSize, dataSize, sysMem, vidMem, refs[(flag,hash)]
"""
import struct, sys, json, time
def parse(path):
    f=open(path,'rb')
    hdr=f.read(25)
    assert hdr[:4]==b'2KPR', hdr[:4]
    unk=hdr[4:13]
    nfiles,htab,itab=struct.unpack_from('<III',hdr,13)
    deleted=[]
    if 'patch' in path.lower():
        n=struct.unpack('<I',f.read(4))[0]; deleted=['%016X'%x for x in struct.unpack('<%dQ'%n,f.read(8*n))]
    hashes=f.read(htab); info=f.read(itab)
    assert len(hashes)==nfiles*20, (len(hashes), nfiles*20)
    ents=[]; q=0
    for i in range(nfiles):
        h,off,sz=struct.unpack_from('<QQI',hashes,i*20)
        typ=info[q:q+4][::-1].decode('ascii'); rts,ds,sm,vm=struct.unpack_from('<IIII',info,q+4); q+=20
        refs=[]
        if rts:
            cnt=struct.unpack_from('<I',info,q)[0]; n=cnt&0x3FFFFFFF; flags=info[q+4:q+4+n]
            hs=struct.unpack_from('<%dQ'%n,info,q+4+n)
            refs=[(flags[k],'%016X'%hs[k]) for k in range(n)]
            q+=rts
        ents.append(dict(hash='%016X'%h,off=off,csize=sz&0x3FFFFFFF,enc=bool(sz&0x80000000),type=typ,rts=rts,size=ds,sysmem=sm,vidmem=vm,refs=refs))
    assert q==len(info),(q,len(info))
    return dict(file=path,unk=unk.hex(),nfiles=nfiles,deleted=deleted,entries=ents)
if __name__=='__main__':
    t=time.time(); d=parse(sys.argv[1])
    json.dump(d,open(sys.argv[2],'w'))
    from collections import Counter
    c=Counter(e['type'] for e in d['entries'])
    print(sys.argv[1],'files',d['nfiles'],'unk',d['unk'],'%.1fs'%(time.time()-t))
    print(sorted(c.items(),key=lambda x:-x[1]))
