"""Read individual resources out of an RPKG v2 using a parsed index (idx/*.json)."""
import json, struct, lz4.block
KEY=bytes([0xDC,0x45,0xA6,0x9C,0xD3,0x72,0x4C,0xAB])
def load_index(p):
    d=json.load(open(p)); d['by_hash']={e['hash']:e for e in d['entries']}; return d
def read_raw(f,e):
    f.seek(e['off']); n=e['csize'] if e['csize'] else e['size']; return f.read(n)
def read_resource(f,e):
    b=bytearray(read_raw(f,e))
    if e['enc']:
        for i in range(len(b)): b[i]^=KEY[i&7]
    if e['csize']:
        b=lz4.block.decompress(bytes(b),uncompressed_size=e['size'])
    return bytes(b)
def fnv1(s):
    h=2166136261
    for c in s.lower().encode(): h=((h*16777619)&0xFFFFFFFF)^c
    return h
if __name__=='__main__':
    # self-test: decode one chunk0 WWEV and compare with RPKG-Tool raw extraction
    d=load_index('idx/new_chunk0.json'); e=d['by_hash']['010001FD0BBCDF5A']
    f=open('D:/SteamLibrary/steamapps/common/007 First Light/Runtime/chunk0.rpkg','rb')
    b=read_resource(f,e); ref=open('cmp/new/WWEV/010001FD0BBCDF5A.WWEV','rb').read()
    print('self-test', len(b), len(ref), b==ref, b[:40])
    print('fnv1 check KNT_SFX_GUI_MainMenu_RevealMainMenu_Play = %08X (expect 015A2090)'%fnv1('KNT_SFX_GUI_MainMenu_RevealMainMenu_Play'))
