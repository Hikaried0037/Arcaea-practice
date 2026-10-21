"""Test real ARM64 initialization guards; downstream native modules are mocked."""
from pathlib import Path
import json,struct
from test_windows import Model,ROOT
from patch_ios import repair
from inspect_ipa import macho
from unicorn.arm64_const import UC_ARM64_REG_X0
class NativeModel(Model):
 def __init__(self,plugin,slide,game,mutation=None):
  super().__init__(plugin,slide);self.modules=[];self.base=0x100000000
  meta=macho(game)
  for s in meta['commands']:
   if 'segment' not in s or s['segment']=='__PAGEZERO':continue
   self.u.mem_map(s['vmaddr'],(s['vmsize']+4095)//4096*4096)
   self.u.mem_write(s['vmaddr'],game[s['fileoff']:s['fileoff']+s['filesize']])
  if mutation=='signature':self.u.mem_write(self.base+0x16ac000,b'BROKEN')
  if mutation=='hook':self.u.mem_write(self.base+0xca47ec,b'\0\0\0\0')
  if mutation=='uuid':
   cmd=next(c for c in meta['commands'] if c['command']=='0x1b');self.u.mem_write(self.base+cmd['file_offset']+8,b'\0'*16)
 def hook(self,u,pc,size,user):
  a=pc-self.slide
  if a==0x1ffa0:self.ret(self.base);return
  if a==0x2009c:
   lhs=bytes(u.mem_read(self.x(0),self.x(2)));rhs=bytes(u.mem_read(self.x(1),self.x(2)));self.ret(0 if lhs==rhs else 1);return
  if a in [0xc250,0xb3bc]:self.modules.append(hex(a));self.ret(1);return
  super().hook(u,pc,size,user)
def main():
 original=(ROOT/'binaries/ArcaeaPractice.dylib').read_bytes();plugin,_,symbols=repair(original,(ROOT/'diagnostics.o').read_bytes());game=(ROOT/'binaries/Arc-mobile').read_bytes();cases=[]
 for slide in [0x1000000,0x123000000,0x700000000]:
  for mutation in [None,'signature','hook','uuid']:
   m=NativeModel(plugin,slide,game,mutation);actual=m.run(0x528c);assert bool(actual)==(mutation is None),(mutation,actual)
   if mutation is None:assert m.modules==['0xc250','0xb3bc']
   else:assert not m.modules,'Unsupported game reached native installation'
   cases.append({'slide':hex(slide),'mutation':mutation,'accepted':bool(actual),'downstream_modules_reached':m.modules})
 report={'passed':True,'checks':len(cases),'scope':'Real native initialization guards executed with supplied game segments; final import/effects module installation calls mocked, not a full gameplay test','cases':cases};(ROOT/'native-entry-regression.json').write_text(json.dumps(report,indent=2)+'\n');print('Native entry guard PASS',len(cases))
if __name__=='__main__':main()
