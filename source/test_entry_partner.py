"""Execute r5 ARM64 entry, native portrait/UserCell refresh, editor removal and
lock opacity control flow. UIKit, rendering and native asset loading are mocked.
"""
import json,struct
from test_pause_audio import Device,ROOT
from patch_ios import repair,STATE
from unicorn.arm64_const import *
class R5(Device):
 def __init__(self,b,slide):
  super().__init__(b,slide);self.u.mem_map(self.base+0x66000,0x1000);self.u.mem_map(self.base+0x23000,0x1000);self.portrait_calls=[];self.avatar_calls=[];self.lock_state={'visible':1,'opacity':255};self.finish_panel=False
 def hook(self,u,pc,size,user):
  a=pc-self.slide;g=pc-self.base
  if self.finish_panel and a==0x1f9c:u.emu_stop();return
  if g==0x66020:self.portrait_calls.append(self.x(0));self.ret();return
  if g==0x2303c:self.avatar_calls.append((self.x(0),self.x(1),self.x(2),self.x(4)));self.ret();return
  if a==0xb0200:self.lock_state['visible']=self.x(1);self.ret();return
  if a==0xb0300:self.lock_state['opacity']=self.x(1);self.ret();return
  if a==0x20108:
   sel=self.cstring(self.x(1))
   if sel.startswith('set') and sel not in ['setHidden:','setInteger:forKey:']:self.ret();return
  super().hook(u,pc,size,user)
 def setup_partner_views(self):
  self.put64(self.scene,self.base+0x147dfd8);self.put64(self.scene+0x2f0,0x20098000)
  self.char=0x2008b000;self.cell=0x2008c000;self.profile=0x2008d000;self.other=0x2008e000;self.other_profile=0x20092000;container=0x2008f000;children=0x20090000
  self.put64(self.slide+0x28808,self.char);self.put32(0x2803c,23);self.u.mem_write(self.char+0xc,struct.pack('<I',99));self.u.mem_write(self.char+0xc9,b'\1\0')
  self.put64(self.scene+0x140,container);self.put64(container,children);self.put64(container+8,children+16);self.put64(children,self.cell);self.put64(children+8,self.other)
  for node,profile,owned in [(self.cell,self.profile,True),(self.other,self.other_profile,False)]:
   self.put64(node,self.base+0x1476080);self.put64(node+0x408,profile);self.u.mem_write(node+0x1c1,b'\1');self.u.mem_write(node+0x1d1,b'\1');self.u.mem_write(profile+0x109,bytes([owned]));self.u.mem_write(profile+0x40,struct.pack('<I',0))

def main():
 b,_,s=repair((ROOT/'binaries/ArcaeaPractice.dylib').read_bytes(),(ROOT/'diagnostics.o').read_bytes());cases=[]
 for slide in [0x1000000,0x123000000,0x700000000]:
  for kind in [0,1,2,3,0xffffffff]:
   m=R5(b,slide);m.put32(0x280d8,kind);m.put32(0x280dc,155407);m.put64(slide+0x280c0,m.obj('UIView',subviews=[]));m.finish_panel=True
   m.u.reg_write(UC_ARM64_REG_X1,slide+0x214dd);m.u.reg_write(UC_ARM64_REG_X2,0);m.u.reg_write(UC_ARM64_REG_X0,0);m.u.reg_write(UC_ARM64_REG_LR,m.stop)
   m.u.emu_start(slide+0x150c,m.stop+4,count=200000);assert m.u.reg_read(UC_ARM64_REG_PC)==slide+0x1f9c,'Panel was rejected'
   panel=struct.unpack('<Q',m.u.mem_read(slide+0x28090,8))[0];overlay=struct.unpack('<Q',m.u.mem_read(slide+0x280c0,8))[0];assert panel and panel in m.objects[overlay]['subviews'];assert m.get32(0x283d8)>0 and m.u.mem_read(slide+0x283dc,1)==b'\1'
   cases.append({'test':'real_action_allocates_attaches_panel_and_queues_begin_despite_stale_kind','slide':hex(slide),'cached_kind':kind})
  for attached in [False,True]:
   m=R5(b,slide);m.parents[m.pause]=m.hud if attached else 0;m.put32(0x280d8,1);m.invoke(s['_panel_pending_kind']);assert m.x(8)==(2 if attached else 1)
   m.u.mem_write(slide+0x283dc,b'\1');m.u.reg_write(UC_ARM64_REG_X20,m.scene);m.u.reg_write(UC_ARM64_REG_X24,slide+0x28000);m.enter(0x6f84,0x6ab4 if attached else 0x6f88)
   cases.append({'test':'pending_panel_and_begin_use_actual_menu_without_relaxing_normal_play_guard','slide':hex(slide),'attached':attached})
  m=R5(b,slide);m.setup_partner_views();m.invoke(s['_refresh_partner_views']);assert m.portrait_calls==[m.scene];assert len(m.avatar_calls)==1 and m.avatar_calls[0][0]==m.cell and m.avatar_calls[0][3]==99;assert m.u.mem_read(m.profile+0x40,4)==struct.pack('<I',99);assert m.u.mem_read(m.profile+0xb8,2)==b'\1\0';assert m.u.mem_read(m.other_profile+0x40,4)==b'\0'*4
  m.invoke(s['_refresh_partner_views']);assert len(m.portrait_calls)==1 and len(m.avatar_calls)==1
  m.u.mem_write(m.char+0xc9,b'\0\1');m.put32(0x2803c,24);m.invoke(s['_refresh_partner_views']);assert len(m.portrait_calls)==2 and len(m.avatar_calls)==2
  cases.append({'test':'restore_refreshes_portrait_and_self_avatar_once_per_selection_or_form','slide':hex(slide),'other_profiles_untouched':True})
  m=R5(b,slide);lock=m.obj('Sprite');vt=0x20099000;m.put64(lock,vt);m.put64(vt+0x470,slide+0xb0300);m.u.reg_write(UC_ARM64_REG_X8,slide+0xb0200);m.u.reg_write(UC_ARM64_REG_X1,0);m.invoke(s['_hide_partner_lock'],lock);assert m.lock_state=={'visible':0,'opacity':0};m.lock_state['visible']=1;assert m.lock_state['opacity']==0
  cases.append({'test':'native_card_visibility_reset_cannot_reveal_zero_opacity_lock','slide':hex(slide)})
  m=R5(b,slide);before=len(m.calls);m.invoke(0x1be08);m.invoke(0x1c44c);assert m.x(0)==0;m.invoke(0x1e598);assert len(m.calls)==before
  cases.append({'test':'four_editor_buttons_never_created_and_no_editor_hit_area_or_action','slide':hex(slide)})
 out={'passed':True,'checks':len(cases),'scope':__doc__,'cases':cases};(ROOT/'entry-partner-regression.json').write_text(json.dumps(out,indent=2)+'\n');print('Entry/partner/editor ARM64 regression PASS',len(cases))
if __name__=='__main__':main()


