"""ARM64 startup selection, unchanged portrait/avatar and selection-banner regression.
Native owner/asset/UI methods are synthetic; no iOS rendering or timing proof.
"""
import json,struct
from test_entry_partner import R5,ROOT
from patch_ios import repair
from unicorn.arm64_const import *
class Startup(R5):
 def __init__(self,b,slide):
  super().__init__(b,slide);self.frames=[];self.notices=[];self.applied=[];self.u.mem_map(self.base+0x1d000,0x1000)
 def hook(self,u,pc,size,user):
  a=pc-self.slide;g=pc-self.base
  if a==0xb5d0:self.frames.append(self.x(1))
  if g==0x1ddf0:self.ret(self.owner);return
  if a==0xb7d4:
   self.applied.append(self.x(1));self.put64(self.owner+0x58,0x2008b000);self.put64(self.slide+0x28800,self.owner);self.put64(self.slide+0x28808,0x2008b000);self.ret(1);return
  if a==0x4180:self.notices.append(self.x(0));self.ret();return
  super().hook(u,pc,size,user)
 def frame(self,s):
  self.u.reg_write(UC_ARM64_REG_X1,0);self.invoke(s['_offline_frame_refresh'],self.base)
 def native_ready(self):
  self.put64(self.owner+0x78,0x20098000)
  # Original notice code reads the selection definition's flag string.
  self.put64(self.slide+0x8e1e8+23*64+0x20,self.slide+0x21901)
def main():
 b,_,s=repair((ROOT/'binaries/ArcaeaPractice.dylib').read_bytes(),(ROOT/'diagnostics.o').read_bytes());cases=[]
 for slide in [0x1000000,0x123000000,0x700000000]:
  m=Startup(b,slide);m.put32(0x28038,23);m.frame(s);assert m.frames==[1] and m.get32(0x28038)==23 and not m.applied
  m.native_ready();m.frame(s);assert m.applied==[23] and m.get32(0x2803c)==23 and m.get32(0x28038)==0xffffffff
  cases.append(dict(test='selection_applied_before_menu_bounds_available_with_retry_until_native_owner_ready',slide=hex(slide)))
  for idx in [0,23,128,129,0xffffffff]:
   m=Startup(b,slide);m.put32(0x28038,idx);m.frame(s);assert m.frames==[int(idx<=128)]
   cases.append(dict(test='early_restore_only_valid_pending_choices',slide=hex(slide),index=idx))
  m=Startup(b,slide);m.setup_partner_views();m.u.mem_write(m.scene+0x338,struct.pack('<I',99));m.put64(m.scene+0x300,0x20098000);m.put64(m.scene+0x308,0x20099000);m.u.mem_write(m.profile+0x40,struct.pack('<I',99));m.u.mem_write(m.profile+0xb8,b'\1\0')
  m.invoke(s['_refresh_partner_views']);m.invoke(s['_refresh_partner_views']);assert not m.portrait_calls and not m.avatar_calls
  cases.append(dict(test='correct_initial_portrait_and_avatar_are_not_rebuilt_or_faded',slide=hex(slide)))
  m.u.mem_write(m.char+0xc9,b'\0\1');m.put32(0x2803c,24);m.invoke(s['_refresh_partner_views']);assert len(m.portrait_calls)==1 and len(m.avatar_calls)==1
  cases.append(dict(test='same_character_form_change_still_refreshes_once',slide=hex(slide)))
  m=Startup(b,slide);m.setup_partner_views();m.invoke(s['_refresh_partner_views']);assert len(m.portrait_calls)==1 and len(m.avatar_calls)==1;m.invoke(s['_refresh_partner_views']);assert len(m.portrait_calls)==1
  cases.append(dict(test='stale_portrait_avatar_still_repaired_once',slide=hex(slide)))
  m=Startup(b,slide);m.put32(0x2803c,23);m.put32(0x285f0,1);m.u.reg_write(UC_ARM64_REG_X21,slide+0x28000);m.enter(0x2ea8,0x2f2c);assert not m.notices and m.get32(0x285f0)==0
  cases.append(dict(test='successful_partner_notice_consumed_without_creating_bottom_banner',slide=hex(slide)))
  for own,caller,valid in [(True,True,True),(False,True,True),(True,False,True),(True,True,False)]:
    m=Startup(b,slide);m.setup_partner_views();m.u.mem_write(m.profile+0x109,bytes([own]));m.put32(0x2803c,23 if valid else 0xffffffff)
    m.u.reg_write(UC_ARM64_REG_X21,m.profile);m.u.reg_write(UC_ARM64_REG_X8,0x2009b000);m.u.reg_write(UC_ARM64_REG_X2,0);m.u.reg_write(UC_ARM64_REG_X0,0x2009c000);m.u.reg_write(UC_ARM64_REG_LR,m.base+(0x23140 if caller else 0x660a4));m.stop_at=0x1ada8
    m.u.emu_start(slide+0x1ada4,m.stop+4,count=1000);assert m.u.reg_read(UC_ARM64_REG_PC)==slide+0x1ada8
    expected=own and caller and valid;assert m.x(0)==(m.char if expected else 0x2009c000);assert m.x(8)==0x2009b000;assert m.x(2)==int(expected);assert m.u.mem_read(m.profile+0x40,4)==struct.pack('<I',99 if expected else 0)
    cases.append(dict(test='first_self_icon_uses_selected_partner_before_texture_lookup',slide=hex(slide),self_profile=own,exact_caller=caller,valid_selection=valid))
 report=dict(passed=True,checks=len(cases),scope=__doc__,cases=cases);(ROOT/'startup-partner-regression.json').write_text(json.dumps(report,indent=2)+'\n');print('Startup partner/banner regression PASS',len(cases))
if __name__=='__main__':main()
