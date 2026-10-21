"""Real ARM64 overlay hit tests, begin-side pause hide, snapshot and UI close path.
UIKit rectangles, button factories, native calls and label formatting are synthetic; not an iOS device test.
"""
import json,struct
from pathlib import Path
from test_entry_partner import R5,ROOT
from patch_ios import repair
from unicorn.arm64_const import *
class Routing(R5):
 def hook(self,u,pc,size,user):
  a=pc-self.slide
  if a==0x20108 and not self.x(0):self.ret(0,(0.,0.,0.,0.));return
  if a==0x20108 and self.cstring(self.x(1))=='addTarget:action:forControlEvents:':
   self.objects[self.x(0)]['action']=self.cstring(self.x(3));self.ret();return
  if a==0xbfe00:self.library_open_args=[self.x(i) for i in range(3)];self.ret();return
  if a==0xb0400:
   u.mem_write(self.pause+0x1c1,bytes([self.x(1)]));self.ret();return
  if a==0x2015c:
   u.mem_write(self.x(0),b'\0');self.ret(0);return
  if a==0x200b4:
   u.mem_write(self.x(0),bytes([self.x(1)&255])*self.x(2));self.ret(self.x(0));return
  if a==0x9b00:self.ret(1);return
  if a==0x97a8:self.ret(155407);return
  if a==0x20108 and self.cstring(self.x(1))=='frame':
   ob=self.objects[self.x(0)];self.ret(d=ob['frame']);return
  super().hook(u,pc,size,user)
 def point(self,x,y):
  self.u.reg_write(UC_ARM64_REG_D0,struct.unpack('<Q',struct.pack('<d',x))[0]);self.u.reg_write(UC_ARM64_REG_D1,struct.unpack('<Q',struct.pack('<d',y))[0]);self.invoke(0x2f68);return bool(self.x(0))
def main():
 b,_,s=repair((ROOT/'binaries/ArcaeaPractice.dylib').read_bytes(),(ROOT/'diagnostics.o').read_bytes());cases=[]
 comparison=ROOT/'binaries/ArcaeaPractice-r5-comparison.dylib'
 old=comparison.read_bytes() if comparison.exists() else None
 for slide in [0x1000000,0x123000000,0x700000000]:
  for label,data in ([('r5',old)] if old else [])+[('r6',b)]:
   m=Routing(data,slide);button=m.obj('UIButton',hidden=0,frame=(800.,30.,180.,50.));m.put64(slide+0x32f88,button)
   assert m.point(850,50)==(label=='r6')
   assert not m.point(799,50) and not m.point(850,81)
   m.objects[button]['hidden']=1;assert not m.point(850,50)
   m.put64(slide+0x32f78,m.obj('UIView'));assert m.point(1,1)==(label=='r6')
   cases.append(dict(test='real_import_entry_and_modal_hit_route_reproduces_r5_failure',slide=hex(slide),build=label))
  m=Routing(b,slide);m.put32(0x280d8,2);m.put32(0x280dc,155407);m.put64(slide+0x280c0,m.obj('UIView',subviews=[]));m.u.reg_write(UC_ARM64_REG_X1,slide+0x214dd);m.invoke(0x150c);controls=[o for o in m.objects.values() if o.get('action')];assert len(controls)>=3;cases.append(dict(test='full_practice_action_builds_controls_and_returns',slide=hex(slide),registered_control_actions=len(controls)))
  m=Routing(b,slide);m.put64(slide+0x93f50,slide+0xbfe00);m.u.reg_write(UC_ARM64_REG_X1,slide+0x214dd);m.u.reg_write(UC_ARM64_REG_X2,123);m.invoke(0x1752c);assert m.library_open_args[1:]==[slide+0x214dd,123];assert m.u.mem_read(slide+0x32f80,1)==b'\0';cases.append(dict(test='entry_routes_to_new_library_without_legacy_modal',slide=hex(slide)))
  m=Routing(b,slide);button=m.obj('UIButton',hidden=0,frame=(800.,700.,140.,42.));m.put64(slide+0x281d0,button)
  assert m.point(810,710) and not m.point(810,699) and not m.point(941,710)
  m.put64(slide+0x28090,m.obj('UIView'));assert m.point(1,1)
  cases.append(dict(test='practice_rect_and_full_panel_hit_regions_survive_import_fallthrough',slide=hex(slide)))
  for label,data in ([('r5',old)] if old else [])+[('r6',b)]:
   m=Routing(data,slide);m.put32(0x282d8,1);m.put32(0x28388,155407)
   modal=0x2009a000;m.put64(m.owner+0xe0,modal);m.u.mem_write(modal+0x38,struct.pack('<I',1))
   # A real pause must publish kind=2 even when the unrelated modal hint is set.
   m.invoke(0x7828);kind=m.get32(0x28348);assert kind==(2 if label=='r6' else 0)
   cases.append(dict(test='full_snapshot_with_visible_pause_and_legacy_modal_hint',slide=hex(slide),build=label,kind=kind))
   # Execute native begin through the actual virtual pause-menu hide operation.
   m.put64(m.vtable+0x150,slide+0xb0400);m.put32(0x283d8,123);m.u.mem_write(slide+0x283dc,b'\1');m.u.reg_write(UC_ARM64_REG_X20,m.scene);m.u.reg_write(UC_ARM64_REG_X24,slide+0x28000);m.u.reg_write(UC_ARM64_REG_X22,slide+0x28230);m.u.reg_write(UC_ARM64_REG_X23,slide+0x28000)
   m.enter(0x6f84,0x6e90);assert m.get32(0x28320)==123;assert m.u.mem_read(m.pause+0x1c1,1)==b'\0'
   m.stop_at=None;m.invoke(0x7828);snapshot=bytes(m.u.mem_read(slide+0x28348,64));m.u.mem_write(slide+0x280d8,snapshot);m.put32(0x28120,123)
   panel=m.obj('UIView');m.put64(slide+0x28090,panel)
   for reg,val in [(UC_ARM64_REG_X20,slide+0x280d8),(UC_ARM64_REG_X24,slide+0x28000)]:m.u.reg_write(reg,val)
   m.enter(0x2bf4,0x2c98);kept=struct.unpack('<Q',m.u.mem_read(slide+0x28090,8))[0]==panel;assert kept==(label=='r6')
   cases.append(dict(test='real_begin_hide_snapshot_and_next_UI_tick_reproduces_r5_panel_disappearance',slide=hex(slide),build=label,panel_retained=kept))
   if label=='r6':
    m.put32(0x28104,123);m.u.reg_write(UC_ARM64_REG_X24,slide+0x28000);m.enter(0x2bf4,0x2c98);assert not struct.unpack('<Q',m.u.mem_read(slide+0x28090,8))[0]
    cases.append(dict(test='matching_completion_still_closes_panel',slide=hex(slide)))
 (ROOT/'ui-routing-regression.json').write_text(json.dumps(dict(passed=True,checks=len(cases),scope=__doc__,cases=cases),indent=2)+'\n');print('UI routing/lifecycle regression PASS',len(cases))
if __name__=='__main__':main()
