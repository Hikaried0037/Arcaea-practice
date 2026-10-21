"""Small deterministic ARM64 Mach-O dylib linker for these two audited C objects.

Supports only the audited relocation kinds emitted by this build and rejects every
other kind. Uses ordinary dyld bind/rebase/export streams and system dylibs.
Avoids the Windows Zig Mach-O linker crash; the Zig C compiler still builds .o.
"""
from pathlib import Path
import struct,hashlib,json
def align(n,a=16):return (n+a-1)//a*a
def uleb(n):
 assert n>=0;b=bytearray()
 while n>=128:b.append((n&127)|128);n>>=7
 b.append(n);return bytes(b)
def command(kind,payload):return struct.pack('<II',kind,len(payload)+8)+payload
def dylib(kind,name):
 p=struct.pack('<4I',24,0,0x10000,0x10000)+name.encode()+b'\0';p+=b'\0'*(align(len(p)+8,8)-len(p)-8);return command(kind,p)
def segment(name,vm,size,off,fs,prot,sections):
 p=struct.pack('<16s4Q4I',name.encode(),vm,size,off,fs,prot,prot,len(sections),0)
 for s in sections:p+=struct.pack('<16s16sQQ8I',s['name'].encode(),name.encode(),s['addr'],s['size'],s['offset'],s['align'],0,0,s.get('flags',0),0,0,0)
 return command(0x19,p)
def objects(paths):
 result=[]
 for path in paths:
  b=path.read_bytes();assert struct.unpack_from('<I',b)[0]==0xfeedfacf;p=32;sections=[]
  for _ in range(struct.unpack_from('<I',b,16)[0]):
   kind,size=struct.unpack_from('<II',b,p)
   if kind==0x19:
    for j in range(struct.unpack_from('<I',b,p+64)[0]):
     q=p+72+j*80;name=b[q:q+16].split(b'\0')[0].decode();seg=b[q+16:q+32].split(b'\0')[0].decode();addr,n=struct.unpack_from('<QQ',b,q+32);off,a,ro,nr,flags=struct.unpack_from('<5I',b,q+48)
     sections.append(dict(name=name,segment=seg,old=addr,size=n,align=a,flags=flags,data=bytearray(n) if flags&255 in [1,12] else bytearray(b[off:off+n]),relocs=[struct.unpack_from('<II',b,ro+8*k) for k in range(nr)]))
   if kind==2:so,ns,st,ss=struct.unpack_from('<4I',b,p+8)
   p+=size
  symbols=[]
  for i in range(ns):
   no,t,s,d,v=struct.unpack_from('<IBBHQ',b,so+i*16);name=b[st+no:st+ss].split(b'\0')[0].decode();symbols.append(dict(name=name,type=t,section=s,value=v))
  result.append(dict(path=path.name,sections=sections,symbols=symbols))
 return result
def build(paths,out):
 obs=objects(paths);cursor=0x1000;allsec=[];index=0
 for group in ['__TEXT','__DATA']:
  if group=='__DATA':textend=align(cursor,0x4000);cursor=textend
  for o in obs:
   for s in o['sections']:
    assert s['segment'] in ['__TEXT','__DATA'],s
    if s['segment']!=group:continue
    assert s['name'] not in ['__compact_unwind','__eh_frame'],'Compile with unwind disabled'
    cursor=align(cursor,1<<s['align']);s['addr']=s['offset']=cursor;s['flags']=0x80000400 if s['name']=='__text' else 0;cursor+=s['size'];index+=1;s['index']=index;allsec.append(s)
 # Undefined symbols use nonlazy pointers and ordinary ARM64 call veneers.
 defined={}
 for o in obs:
  for s in o['symbols']:
   if s['section']:
    sec=o['sections'][s['section']-1];s['addr']=sec['addr']+s['value']-sec['old']
    if s['type']&1:assert s['name'] not in defined;defined[s['name']]=s['addr']
 undefined=sorted({s['name'] for o in obs for s in o['symbols'] if not s['section'] and s['name'] not in defined})
 got=align(cursor,8);cursor=got+8*len(undefined);dataend=align(cursor,0x4000)
 # Space between TEXT sections and the next page is reserved for call veneers.
 veneer=align(max(s['addr']+s['size'] for s in allsec if s['segment']=='__TEXT'),4);assert veneer+12*len(undefined)<=textend
 calls={name:veneer+12*i for i,name in enumerate(undefined)};pointers={name:got+8*i for i,name in enumerate(undefined)}
 image=bytearray(dataend);rebases=[];relocations=[]
 def target(o,sym):
  s=o['symbols'][sym];return s.get('addr',defined.get(s['name'],calls.get(s['name'])))
 for o in obs:
  for sec in o['sections']:
   data=sec['data']
   for off,info in sec['relocs']:
    typ=info>>28;external=(info>>27)&1;pc=sec['addr']+off;assert external,(o['path'],sec['name'],hex(info));dest=target(o,info&0xffffff);assert dest is not None
    if typ==0:
     assert (info>>25)&3==3;add=struct.unpack_from('<Q',data,off)[0];struct.pack_into('<Q',data,off,dest+add);rebases.append(pc)
    elif typ==2:
     w=struct.unpack_from('<I',data,off)[0];assert w&0x7c000000==0x14000000;delta=dest-pc;assert delta%4==0 and -(1<<27)<=delta<1<<27;struct.pack_into('<I',data,off,(w&0xfc000000)|((delta//4)&0x3ffffff))
    elif typ in [3,5]:
     if typ==5:dest=pointers[o['symbols'][info&0xffffff]['name']]
     w=struct.unpack_from('<I',data,off)[0];assert w&0x9f000000==0x90000000;delta=(dest>>12)-(pc>>12);assert -(1<<20)<=delta<1<<20;struct.pack_into('<I',data,off,(w&0x9f00001f)|((delta&3)<<29)|(((delta>>2)&0x7ffff)<<5))
    elif typ in [4,6]:
     if typ==6:dest=pointers[o['symbols'][info&0xffffff]['name']]
     w=struct.unpack_from('<I',data,off)[0];scale=0
     if w&0x3b000000==0x39000000:
      scale=(w>>30)&3
      if w&(1<<26) and w&(1<<23):scale=4
     else:assert w&0x7f000000==0x11000000,(hex(w),hex(pc))
     low=dest&4095;assert low%(1<<scale)==0;struct.pack_into('<I',data,off,(w&~(4095<<10))|((low>>scale)<<10))
    else:raise AssertionError(('unsupported relocation',typ))
    relocations.append(dict(pc=pc,target=dest,type=typ))
   image[sec['addr']:sec['addr']+sec['size']]=data
 for name in undefined:
  pc=calls[name];dest=pointers[name];delta=(dest>>12)-(pc>>12);w=0x90000010|((delta&3)<<29)|(((delta>>2)&0x7ffff)<<5);struct.pack_into('<3I',image,pc,w,0xf9400210|(((dest&4095)//8)<<10),0xd61f0200)
 # Explicit dependency ordinals. Reject unrecognized external references.
 deps=['/usr/lib/libSystem.B.dylib','/usr/lib/libobjc.A.dylib','/System/Library/Frameworks/Foundation.framework/Foundation','/System/Library/Frameworks/UIKit.framework/UIKit','/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics','/System/Library/Frameworks/WebKit.framework/WebKit','/usr/lib/libz.1.dylib']
 def ordinal(n):
  if n.startswith(('_objc_','_class_','_sel_')):return 2
  if n.startswith(('_UIImage','_UIGraphics')):return 4
  if n.startswith('_CGImage'):return 5
  if n in ['_crc32','_inflate','_inflateEnd','_inflateInit2_','_zlibVersion']:return 7
  assert n in ['_malloc','_free','_memcpy','_memcmp','_memset','_snprintf','_strcmp','_strlen','_dispatch_async_f','_dispatch_get_global_queue','__dispatch_main_q'],n
  return 1
 bind=bytearray()
 for name in undefined:bind+=bytes([0x10|ordinal(name),0x40])+name.encode()+b'\0'+bytes([0x51,0x60,0,0x71])+uleb(pointers[name]-textend)+bytes([0x90])
 bind+=b'\0';rebase=bytearray()
 for addr in sorted(rebases):
  assert textend<=addr<dataend;rebase+=bytes([0x11,0x21])+uleb(addr-textend)+bytes([0x51])
 rebase+=b'\0'
 exports={n:defined[n] for n in ['_arc_library_open','_arc_library_take_reload']}
 leaves={n:uleb(len(uleb(0)+uleb(a)))+uleb(0)+uleb(a)+b'\0' for n,a in exports.items()};offsets={n:0 for n in exports}
 for _ in range(5):
  root=b'\0'+bytes([len(exports)])+b''.join(n.encode()+b'\0'+uleb(offsets[n]) for n in exports);cur=len(root)
  for n in exports:offsets[n]=cur;cur+=len(leaves[n])
 trie=root+b''.join(leaves.values());link=bytearray()
 # dyld validates the start alignment of each LINKEDIT content independently.
 # Rebase/bind/export streams are variable length, so pad BEFORE each stream.
 def append_content(content):
  link.extend(b'\0'*(align(len(link),8)-len(link)));offset=dataend+len(link);link.extend(content);return offset
 ro=append_content(rebase);bo=append_content(bind);eo=append_content(trie)
 # A normal symbol table is retained for reproducible binary inspection/testing.
 while len(link)%8:link+=b'\0'
 so=dataend+len(link);strs=bytearray(b'\0');symbytes=bytearray();symbol_report={}
 ordered=[(o,s) for o in obs for s in o['symbols'] if s['section']]
 ordered.sort(key=lambda pair:pair[1]['name'] in exports)
 for o,s in ordered:
  name=s['name'];sec=o['sections'][s['section']-1];no=len(strs);strs+=name.encode()+b'\0';symbytes+=struct.pack('<IBBHQ',no,0xf if name in exports else 0xe,sec['index'],0,s['addr']);symbol_report[name]=s['addr']
 link+=symbytes;st=dataend+len(link);link+=strs
 textsecs=[s for s in allsec if s['segment']=='__TEXT'];datasecs=[s for s in allsec if s['segment']=='__DATA']
 # Veneers and pointer slots remain regular sections, described by bind streams.
 textsecs.append(dict(name='__calls',addr=veneer,size=12*len(undefined),offset=veneer,align=2,flags=0x80000400));datasecs.append(dict(name='__got',addr=got,size=8*len(undefined),offset=got,align=3))
 # Symbol section ordinals follow segment command order, including the veneer.
 # Recompute because the veneer section precedes all DATA sections.
 remap={s['index']:i+1 for i,s in enumerate(textsecs+datasecs) if 'index' in s}
 for i in range(len(symbytes)//16):link[so-dataend+i*16+5]=remap[link[so-dataend+i*16+5]]
 cmds=segment('__TEXT',0,textend,0,textend,5,textsecs)+segment('__DATA',textend,dataend-textend,textend,dataend-textend,3,datasecs)+segment('__LINKEDIT',dataend,align(len(link),0x4000),dataend,len(link),1,[])
 cmds+=dylib(0xd,'@loader_path/ArcLibrary.dylib')+b''.join(dylib(0xc,n) for n in deps)
 cmds+=command(0x80000022,struct.pack('<10I',ro,len(rebase),bo,len(bind),0,0,0,0,eo,len(trie)))
 cmds+=command(2,struct.pack('<4I',so,len(symbytes)//16,st,len(strs)))+command(0x32,struct.pack('<4I',2,0x000c0400,0x000c0400,0))
 locals_count=len(symbytes)//16-len(exports)
 cmds+=command(0xb,struct.pack('<18I',0,locals_count,locals_count,len(exports),locals_count+len(exports),0,*([0]*12)))
 cmds+=command(0x1b,hashlib.sha256(image).digest()[:16]);assert len(cmds)+32<=0x1000
 image[:32]=struct.pack('<8I',0xfeedfacf,0x100000c,0,6,15,len(cmds),0x85,0)
 # Count rather than assuming a fixed number of commands.
 p=0;nc=0
 while p<len(cmds):nc+=1;p+=struct.unpack_from('<I',cmds,p+4)[0]
 struct.pack_into('<I',image,16,nc);image[32:32+len(cmds)]=cmds;image+=link;out.write_bytes(image)
 report=dict(bytes=len(image),sha256=hashlib.sha256(image).hexdigest(),symbols=symbol_report,undefined=undefined,relocations=relocations,rebases=rebases,pointers=pointers,calls=calls,dependencies=deps,exported=exports)
 out.with_suffix('.link.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 r=Path(__file__).resolve().parent;report=build([r/'library.o',r/'archive.o'],r/'ArcLibrary.dylib');print('Linked ARM64 library:',report['bytes'],'bytes;',len(report['relocations']),'relocations')
