"""Regression for the device-reported r12 dyld LINKEDIT alignment rejection.
Static validation only; does not execute Apple's dyld or code signing.
"""
from pathlib import Path
import struct,json,hashlib
from inspect_ipa import macho
ROOT=Path(__file__).resolve().parent
def validate(data):
 m=macho(data);link=next(c for c in m['commands'] if c.get('segment')=='__LINKEDIT');lo=link['fileoff'];hi=lo+link['filesize'];items=[];errors=[]
 def item(name,offset,size,alignment):
  if not size:return
  items.append(dict(name=name,offset=offset,size=size,alignment=alignment))
  if offset%alignment:errors.append(dict(name=name,offset=offset,reason='alignment',required=alignment))
  if not(lo<=offset and offset+size<=hi):errors.append(dict(name=name,offset=offset,reason='LINKEDIT bounds'))
 for c in m['commands']:
  p=c['file_offset'];kind=int(c['command'],16)
  assert p%8==0 and c['size']%8==0
  if kind==0x80000022:
   for field,name in [(8,'rebase opcodes'),(16,'bind opcodes'),(24,'weak bind opcodes'),(32,'lazy bind opcodes'),(40,'export trie')]:
    off,size=struct.unpack_from('<II',data,p+field);item(name,off,size,8)
  if kind==2:
   so,n,st,ss=struct.unpack_from('<4I',data,p+8);item('symbol table',so,n*16,8);item('string table',st,ss,8)
  if kind in [0x1d,0x26,0x29,0x80000033,0x80000034]:
   off,size=struct.unpack_from('<II',data,p+8);item(hex(kind),off,size,16 if kind==0x1d else 8)
 ordered=sorted(items,key=lambda x:x['offset'])
 for a,b in zip(ordered,ordered[1:]):
  if a['offset']+a['size']>b['offset']:errors.append(dict(name=a['name'],reason='content overlaps '+b['name']))
 return items,errors
def main():
 errors=[]
 if (ROOT.parent/'r12/ArcLibrary.dylib').exists():
  old=(ROOT.parent/'r12/ArcLibrary.dylib').read_bytes();before,errors=validate(old);assert any(e['name']=='bind opcodes' and e['offset']==0xc05f and e['reason']=='alignment' for e in errors),errors
 else:print('SKIP historical r12 reproducer: old binary is not exported')
 fixed=(ROOT/'ArcLibrary.dylib').read_bytes();after,errors_after=validate(fixed);assert not errors_after,errors_after
 result=dict(passed=True,checks=1+bool(errors),scope=__doc__,r12_reproduced_errors=errors,current_contents=after,library_sha256=hashlib.sha256(fixed).hexdigest())
 (ROOT/'dyld-layout-regression.json').write_text(json.dumps(result,indent=2)+'\n');print('dyld layout regression PASS; current offsets:',{x['name']:hex(x['offset']) for x in after})
if __name__=='__main__':main()
