"""Execute r4 ARM64 control flow with synthetic Objective-C/native contracts.
Not UIKit, dyld, device suspension, signing, audio playback, or an FPS test.
"""
import itertools,json,struct
from test_windows import Model,ROOT
from test_runloop import Runtime
from patch_ios import repair,STATE
from unicorn.arm64_const import *
class Lifecycle(Runtime):
 def __init__(self,b,slide):
  super().__init__(b,slide);self.stop_at=None;self.method_selectors=[]
  self.u.mem_write(slide+0x282c8,struct.pack('<Q',slide+0xb0000))
 def hook(self,u,pc,size,user):
  a=pc-self.slide
  if a==self.stop_at:u.emu_stop();return
  if a==0x1ffc4:self.method_selectors.append(self.cstring(self.x(1)))
  super().hook(u,pc,size,user)
 def get32(self,a):return struct.unpack('<I',self.u.mem_read(self.slide+a,4))[0]
 def put32(self,a,v):self.u.mem_write(self.slide+a,struct.pack('<I',v))
 def enter(self,a,stop,arg=0):
  self.stop_at=stop;self.u.reg_write(UC_ARM64_REG_X0,arg);self.u.reg_write(UC_ARM64_REG_LR,self.stop);self.u.emu_start(self.slide+a,self.stop+4,count=100000);assert self.u.reg_read(UC_ARM64_REG_PC)==self.slide+stop

def main():
 orig=(ROOT/'binaries/ArcaeaPractice.dylib').read_bytes();fixed,_,syms=repair(orig,(ROOT/'diagnostics.o').read_bytes());cases=[]
 for slide in [0x1000000,0x123000000,0x700000000]:
  m=Lifecycle(fixed,slide);m.invoke(0x1228)
  assert set(m.method_selectors)>={'arcpracWillResign:','arcpracDidBecomeActive:'}
  assert {x[2] for x in m.observers}=={'UIApplicationWillResignActiveNotification','UIApplicationDidEnterBackgroundNotification','UIApplicationDidBecomeActiveNotification'}
  cases.append(dict(test='real_initializer_registers_lifecycle_methods_and_notifications',slide=hex(slide)))
  # Repeated resign/background/foreground events, with a practice preview open.
  for cycle in range(8):
   m=Lifecycle(fixed,slide);panel=m.obj('UIView');button=m.obj('UIButton');m.u.mem_write(slide+0x28090,struct.pack('<Q',panel));m.u.mem_write(slide+0x281d0,struct.pack('<Q',button));m.put32(0x28120,123);m.put32(0x283d8,123);m.u.mem_write(slide+0x28208,b'\1')
   m.invoke(syms['_resign']);assert m.get32(STATE+16)==1 and m.get32(STATE+20)==123;assert not m.get32(0x28120);assert bytes(m.u.mem_read(slide+0x28090,8))==b'\0'*8;assert m.objects[panel]['detached'] and m.objects[button]['hidden']==1
   # A second notification must not lose the deferred cancellation request.
   m.invoke(syms['_resign']);assert m.get32(STATE+20)==123
   before=len(m.calls);m.invoke(0x2970);assert len(m.calls)==before,'Inactive tick did UIKit work'
   m.enter(0x65b4,0xb0000,arg=0x1234);assert m.x(0)==0x1234 and not m.get32(0x283e8)
   m.stop_at=None;m.invoke(syms['_active']);assert m.get32(STATE+16)==0
   m.enter(0x65b4,0x65b8,arg=0x1234);assert m.x(0)==0x1234;assert m.get32(0x283e8)==3 and m.get32(STATE+20)==0
   cases.append(dict(test='resign_detach_inactive_skip_and_deferred_foreground_cancel',slide=hex(slide),cycle=cycle))
  for index in [0,1,23,64,128]:
   m=Lifecycle(fixed,slide);m.u.reg_write(UC_ARM64_REG_X19,index);m.u.reg_write(UC_ARM64_REG_X8,slide+0x2803c);m.invoke(syms['_partner_applied']);assert m.get32(0x2803c)==index and m.get32(STATE+28)==1
   m.invoke(syms['_persist_partner']);assert m.prefs=={'ArcPrac.selectedPartner.v1':index} and m.pref_writes==1
   m.invoke(syms['_persist_partner']);assert m.pref_writes==1,'Preferences written every frame'
   restarted=Lifecycle(fixed,slide);restarted.prefs=dict(m.prefs);restarted.invoke(syms['_restore_partner']);assert restarted.get32(0x28038)==index
   # Native owner unavailable: the pending selection survives the frame.
   restarted.put32(0x28038,0xffffffff);restarted.u.reg_write(UC_ARM64_REG_X19,index);restarted.enter(syms['_partner_retry'],0xb68c);assert restarted.get32(0x28038)==index
   cases.append(dict(test='partner_success_persists_restart_and_retry',slide=hex(slide),index=index))
  for locked in [False,True]:
   m=Lifecycle(fixed,slide);dst=0x20090000;source=bytes(range(64));previous=b'Z'*64;m.u.mem_write(dst,previous);m.u.mem_write(slide+0x28234,source);m.u.mem_write(slide+0x28230,bytes([int(locked)]));m.invoke(0x55e4,dst)
   assert bytes(m.u.mem_read(dst,64))==(previous if locked else source)
   assert bytes(m.u.mem_read(slide+0x28230,1))==bytes([int(locked)])
   assert m.get32(0x28258)==(struct.unpack_from('<I',source,0x24)[0] if locked else 0)
   cases.append(dict(test='snapshot_busy_returns_without_spinning_or_partial_copy',slide=hex(slide),locked=locked))
  for invalid in [-1,129,100000]:
   m=Lifecycle(fixed,slide);m.prefs={'ArcPrac.selectedPartner.v1':invalid};m.put32(0x28038,0xffffffff);m.invoke(syms['_restore_partner']);assert m.get32(0x28038)==0xffffffff
   cases.append(dict(test='invalid_preference_ignored',slide=hex(slide),value=invalid))
 report={'passed':True,'checks':len(cases),'scope':__doc__,'cases':cases};(ROOT/'lifecycle-partner-regression.json').write_text(json.dumps(report,indent=2)+'\n');print('Lifecycle/pause/partner ARM64 regression PASS',len(cases))
if __name__=='__main__':main()
