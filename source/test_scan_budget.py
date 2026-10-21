"""Execute the actual ARM64 menu-scan throttle; no claim about device FPS."""
import struct,json
from test_windows import Model,ROOT
from patch_ios import repair
from unicorn.arm64_const import *
class Budget(Model):
 def __init__(self,plugin,slide):
  super().__init__(plugin,slide);self.scans=0;self.skips=0
 def hook(self,u,pc,size,user):
  if pc==self.slide+0xd1a0:self.scans+=1;u.emu_stop();return
  if pc==self.slide+0xd220:self.skips+=1;u.emu_stop();return
  super().hook(u,pc,size,user)
 def frame(self,t,scene):
  self.u.reg_write(UC_ARM64_REG_D0,struct.unpack('<Q',struct.pack('<d',t))[0]);self.u.reg_write(UC_ARM64_REG_X20,scene);self.u.emu_start(self.slide+0xd16c,self.stop,count=100);assert self.u.reg_read(UC_ARM64_REG_PC) in [self.slide+0xd1a0,self.slide+0xd220]
def main():
 original=(ROOT/'binaries/ArcaeaPractice.dylib').read_bytes();fixed,_,_=repair(original,(ROOT/'diagnostics.o').read_bytes());cases=[]
 for slide in [0x1000000,0x123000000,0x700000000]:
  for hz in [60,120,144]:
   counts={}
   for name,plugin in [('original',original),('fixed',fixed)]:
    m=Budget(plugin,slide)
    for i in range(hz*10):m.frame(i/hz,0x20010000)
    counts[name]=m.scans
    if name=='fixed':
     assert 35<=m.scans<=40
     # A new scene bypasses the scan cooldown on the next frame.
     before=m.scans;m.frame(10.,0x20020000);assert m.scans==before+1
   assert counts['fixed']<counts['original']
   cases.append({'slide':hex(slide),'synthetic_frame_hz':hz,'duration_seconds':10,'scan_entries':counts,'scene_change_immediate':True})
 report={'passed':True,'checks':len(cases),'scope':'Real ARM64 scan cooldown instructions; not a performance benchmark or proof of actual loading-frame smoothness','cases':cases};(ROOT/'scan-budget-regression.json').write_text(json.dumps(report,indent=2)+'\n');print('Menu scan budget PASS',len(cases))
if __name__=='__main__':main()
