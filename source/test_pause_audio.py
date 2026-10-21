"""ARM64 regressions for detached native pause menus and suspended mixers.
Runtime/virtual parent methods are synthetic. One test executes the game's real
FMOD-backend update instructions with FMOD and logging calls mocked.
"""
from pathlib import Path
import json,struct,itertools
from test_lifecycle_partner import Lifecycle,ROOT
from patch_ios import repair,STATE
from inspect_ipa import macho
from unicorn.arm64_const import *
class Device(Lifecycle):
 def __init__(self,plugin,slide,real_game=False):
  super().__init__(plugin,slide);self.parents={};self.scene=0x20080000;self.hud=0x20081000;self.pause=0x20082000;self.vtable=0x20086000;self.backend=0x20087000;self.owner=0x20088000;self.manager=0x20089000;self.base=0x100000000;self.original_frames=0;self.audio_resumes=0;self.releases=0
  if real_game:
   game=(ROOT/'binaries/Arc-mobile').read_bytes()
   for seg in macho(game)['commands']:
    if 'segment' not in seg or seg['segment']=='__PAGEZERO':continue
    self.u.mem_map(seg['vmaddr'],(seg['vmsize']+4095)//4096*4096);self.u.mem_write(seg['vmaddr'],game[seg['fileoff']:seg['fileoff']+seg['filesize']])
  else:self.u.mem_map(self.base+0x1678000,0x1000)
  self.put64(slide+0x28278,self.base);self.put64(self.base+0x16781d8,self.owner);self.put64(self.owner+0x10,self.manager);self.put64(self.manager+0x280,self.backend);self.put64(self.backend,self.base+0x14bb930);self.u.mem_write(self.backend+0x10,b'\1');self.put64(self.scene,self.base+0x1521dc0)
  self.u.mem_write(self.scene+0x470,b'\1');self.put64(self.scene+0x380,self.hud);self.put64(self.hud+0x2c0,self.pause)
  for node in [self.scene,self.hud,self.pause]:self.u.mem_write(node+0x1c1,b'\1');self.u.mem_write(node+0x1d1,b'\1')
  for node in [self.hud,self.pause]:self.put64(node,self.vtable)
  self.put64(self.vtable+0x240,slide+0xb0100);self.parents={self.hud:self.scene,self.pause:self.hud}
 def put64(self,a,v):self.u.mem_write(a,struct.pack('<Q',v))
 def hook(self,u,pc,size,user):
  a=pc-self.slide;ga=pc-0x100000000
  if a==0xb0100:self.ret(self.parents.get(self.x(0),0));return
  if a==0xcff0:self.ret(self.scene);return
  if ga in [0xb69b50,0x10a1004]:self.releases+=1;raise AssertionError('Unexpected audio resource release')
  if ga==0x8e4c3c:self.ret(1);return
  if ga==0x10adff4:self.audio_resumes+=1;self.ret(0);return
  if ga in [0x10ad010,0x8e2c94]:self.ret(0);return
  if ga==0xebdb28:self.u.mem_write(self.x(0),b'\0'*24);self.ret();return
  super().hook(u,pc,size,user)
 def bool_call(self,addr):self.invoke(addr,self.scene);return bool(self.x(0))

def main():
 original=(ROOT/'binaries/ArcaeaPractice.dylib').read_bytes();fixed,_,sym=repair(original,(ROOT/'diagnostics.o').read_bytes());cases=[]
 for slide in [0x1000000,0x123000000,0x700000000]:
  for paused,attached,visible,hud_visible,hud_attached,active in itertools.product([0,1],repeat=6):
   m=Device(fixed,slide);m.u.mem_write(m.scene+0x470,bytes([paused]));m.parents[m.pause]=m.hud if attached else 0;m.parents[m.hud]=m.scene if hud_attached else 0;m.u.mem_write(m.pause+0x1c1,bytes([visible]));m.u.mem_write(m.hud+0x1c1,bytes([hud_visible]));m.put32(STATE+16,not active)
   want=bool(paused and attached and visible and hud_visible and hud_attached)
   assert m.bool_call(sym['_scene_has_pause'])==want
   assert m.bool_call(sym['_entry_allowed'])==(want and bool(active))
   m.invoke(sym['_fresh_ui_kind']);assert m.x(8)==(2 if want and active else 1)
   # Even stale cached kind=2 cannot open a panel when the real menu is gone.
   m.u.reg_write(UC_ARM64_REG_X8,0);m.enter(sym['_action_pause_gate'],0x1d40 if want and active else 0x1c9c)
   # Actual snapshot branch must agree on attachment (irrespective of app state).
   m.u.reg_write(UC_ARM64_REG_X22,m.scene);m.enter(0x7ad0,0x7b30 if want else 0x790c)
   cases.append({'test':'real_pause_attachment_required_for_snapshot_entry_and_click','slide':hex(slide),'inputs':[paused,attached,visible,hud_visible,hud_attached,active],'allowed':bool(want and active)})
  for edge in ['parent_cycle','foreign_parent','hidden_ancestor','already_open_panel','wrong_audio_backend','hidden_scene','not_running_scene']:
   m=Device(fixed,slide)
   if edge=='hidden_scene':m.u.mem_write(m.scene+0x1c1,b'\0')
   elif edge=='not_running_scene':m.u.mem_write(m.scene+0x1d1,b'\0')
   elif edge=='parent_cycle':m.parents[m.hud]=m.hud
   elif edge=='foreign_parent':m.parents[m.pause]=m.scene
   elif edge=='hidden_ancestor':
    node=0x2008a000;m.put64(node,m.vtable);m.parents[m.hud]=node;m.parents[node]=m.scene;m.u.mem_write(node+0x1c1,b'\0')
   elif edge=='wrong_audio_backend':m.put64(m.backend,0x1234)
   if edge=='already_open_panel':
    m.u.reg_write(UC_ARM64_REG_X8,1);m.enter(sym['_action_pause_gate'],0x1c9c)
   else:assert not m.bool_call(sym['_entry_allowed'])
   cases.append({'test':edge,'slide':hex(slide)})
  # Running flag can stay true on a detached menu, as observed in native hide.
  m=Device(fixed,slide);m.parents[m.pause]=0;assert m.u.mem_read(m.pause+0x1d1,1)==b'\1';assert not m.bool_call(sym['_entry_allowed']);cases.append({'test':'detached_running_visible_node_rejected','slide':hex(slide)})
  for suspended,ready,recovering in itertools.product([0,1],repeat=3):
   m=Device(fixed,slide);m.u.mem_write(m.backend+0xa8,bytes([suspended]));m.u.mem_write(m.backend+0x10,bytes([ready]));m.u.mem_write(m.backend+0xc8,bytes([recovering]));m.put32(STATE+20,123);m.put32(0x283d8,123)
   allowed=bool(ready and not suspended and not recovering)
   assert m.bool_call(sym['_audio_ready'])==allowed
   assert m.bool_call(sym['_entry_allowed'])==allowed
   m.enter(0x65b4,0x65b8 if allowed else 0xb0000,arg=0x1234);assert m.x(0)==0x1234
   assert m.get32(STATE+20)==(0 if allowed else 123);assert m.get32(0x283e8)==(3 if allowed else 0)
   cases.append({'test':'pending_cancel_waits_for_original_backend_resume','slide':hex(slide),'suspended':suspended,'ready':ready,'recovering':recovering,'plugin_frame':allowed})
  # Execute real native backend resume: simply making UIKit active must not
  # cancel/rebuild before the original engine has executed this routine.
  m=Device(fixed,slide,real_game=True);m.u.mem_write(m.backend+0xa9,b'\1');m.u.mem_write(m.backend+0xa8,b'\0');m.u.mem_write(m.backend+0x10,b'\0');m.put32(STATE+20,123);m.put32(0x283d8,123)
  m.enter(0x65b4,0xb0000,arg=0x1234);assert m.get32(STATE+20)==123 and not m.audio_resumes
  m.stop_at=None;m.invoke(0xb6c010+m.base-m.slide,m.manager);assert m.audio_resumes==1 and m.u.mem_read(m.backend+0x10,1)==b'\1'
  m.enter(0x65b4,0x65b8,arg=0x1234);assert m.get32(0x283e8)==3 and not m.releases
  cases.append({'test':'actual_game_backend_resume_runs_before_plugin_cancel','slide':hex(slide),'FMOD_calls':'mocked','native_backend_instructions':'real'})
 report={'passed':True,'checks':len(cases),'scope':__doc__,'cases':cases};(ROOT/'pause-audio-regression.json').write_text(json.dumps(report,indent=2)+'\n');print('Pause attachment/audio ordering ARM64 regression PASS',len(cases))
if __name__=='__main__':main()
