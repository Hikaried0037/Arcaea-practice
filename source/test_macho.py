"""Audit thin ARM64 Mach-O layout and dyld metadata after segment insertion."""
import struct,json,hashlib
from pathlib import Path
from inspect_ipa import macho
from patch_ios import repair,BASE,EXTRA,STATE
ROOT=Path(__file__).resolve().parent

def read_uleb(b,p):
 value=0;shift=0
 while True:
  x=b[p];p+=1;value|=(x&127)<<shift
  if not x&128:return value,p
  shift+=7;assert shift<70

def dyld_targets(program,bind=False):
 p=0;segment=offset=0;out=[];symbol='';ordinal=0
 while p<len(program):
  x=program[p];p+=1;op=x&240;imm=x&15
  if op==0:
   if not bind or not any(program[p:]):break
  elif bind and op==0x10:ordinal=imm
  elif bind and op in [0x20,0x60]:v,p=read_uleb(program,p);ordinal=v if op==0x20 else ordinal
  elif bind and op==0x30:ordinal=imm
  elif bind and op==0x40:
   end=program.index(0,p);symbol=program[p:end].decode();p=end+1
  elif (bind and op==0x50) or (not bind and op==0x10):pass
  elif op==(0x70 if bind else 0x20):segment=imm;offset,p=read_uleb(program,p)
  elif op==(0x80 if bind else 0x30):v,p=read_uleb(program,p);offset+=v
  elif not bind and op==0x40:offset+=imm*8
  elif op==(0x90 if bind else 0x50):
   for _ in range(1 if bind else imm):out.append((segment,offset,symbol,ordinal));offset+=8
  elif op==(0xa0 if bind else 0x70):
   out.append((segment,offset,symbol,ordinal));v,p=read_uleb(program,p);offset+=8+v
  elif op==(0xb0 if bind else 0x60):
   if bind:out.append((segment,offset,symbol,ordinal));offset+=8+imm*8
   else:
    count,p=read_uleb(program,p)
    for _ in range(count):out.append((segment,offset,symbol,ordinal));offset+=8
  elif op==(0xc0 if bind else 0x80):
   count,p=read_uleb(program,p);skip,p=read_uleb(program,p)
   for _ in range(count):out.append((segment,offset,symbol,ordinal));offset+=8+skip
  else:raise AssertionError(hex(x))
 return out

def main():
 original=(ROOT/'binaries/ArcaeaPractice.dylib').read_bytes();fixed,report,_=repair(original,(ROOT/'diagnostics.o').read_bytes());old=macho(original);new=macho(fixed);segments=[s for s in new['commands'] if 'segment' in s]
 assert [s['segment'] for s in segments]==['__TEXT','__DATA','__PRACFIX','__LINKEDIT']
 for a,b in zip(segments,segments[1:]):assert a['vmaddr']+a['vmsize']<=b['vmaddr'] and a['fileoff']+a['filesize']<=b['fileoff']
 for s in segments:assert s['fileoff']+s['filesize']<=len(fixed)
 assert fixed[0x92910:0x92930]==original[0x92910:0x92930]
 assert old['symbols']==new['symbols'],'Original symbol values/section indexes changed'
 for sec in old['sections']:assert sec in new['sections']
 state=next(s for s in new['sections'] if s['name']=='__practice');assert state['addr']==STATE and state['size']==0x100
 info_old=next(c for c in old['commands'] if c['command']=='0x80000022')['file_offset'];info=next(c for c in new['commands'] if c['command']=='0x80000022')['file_offset'];counts={}
 for field,name,isbind in [(8,'rebase',False),(16,'bind',True),(24,'weak_bind',True),(32,'lazy_bind',True)]:
  off,size=struct.unpack_from('<II',fixed,info+field);oldoff,oldsize=struct.unpack_from('<II',original,info_old+field)
  assert not off or off>=BASE+EXTRA
  before=dyld_targets(original[oldoff:oldoff+oldsize],isbind);after=dyld_targets(fixed[off:off+size],isbind);assert all(v[0]<=1 for v in before),'Existing dyld targets a moved segment'
  if name=='bind':assert after==before+[(1,STATE+8-0x28000,'_NSRunLoopCommonModes',6),(1,STATE+80-0x28000,'_arc_library_open',7),(1,STATE+88-0x28000,'_arc_library_take_reload',7)]
  else:assert before==after
  counts[name]=len(after)
  for seg,off,_,_ in after:assert off+8<=segments[seg]['vmsize']
 text=next(s for s in new['sections'] if s['segment']=='__PRACFIX');assert text['size']==report['code_island_bytes'] and text['size']<EXTRA
 out={'passed':True,'scope':'Mach-O structure, file bounds, original symbols/sections/init array, decoded dyld fixups; not a real dyld/code-signing run','segments':segments,'dyld_target_counts':counts,'sha256':hashlib.sha256(fixed).hexdigest()};(ROOT/'macho-regression.json').write_text(json.dumps(out,indent=2)+'\n');print('Mach-O/fixup audit PASS',counts)
if __name__=='__main__':main()
