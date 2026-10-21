"""Run native callback, selected-tab state and bounded catalog walk under ARM64.
System UI rendering and the native list rebuild itself are host substitutes; real callback, post-refresh wrapper, Node visibility and Widget enabled setters execute under actual Mach-O permissions.
"""
from pathlib import Path
import struct,json,itertools,hashlib
from unicorn import Uc,UcError,UC_ERR_FETCH_PROT,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
from patch_difficulty import repair_main,branch,ISLAND,ISLAND_FILE
from inspect_ipa import macho
ROOT=Path(__file__).resolve().parent
class Main:
 def __init__(self,data,base):
  self.base=base;self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
  # Honor VM addresses, zero-fill DATA and initprot; never map the flat file.
  self.segments=[]
  for seg in macho(data)['commands']:
   if not seg.get('vmsize') or seg.get('segment')=='__PAGEZERO':continue
   address=base+seg['vmaddr']-0x100000000;size=seg['vmsize'];permissions=struct.unpack_from('<I',data,seg['file_offset']+60)[0]
   self.u.mem_map(address,size,7)
   if seg['filesize']:self.u.mem_write(address,data[seg['fileoff']:seg['fileoff']+seg['filesize']])
   self.u.mem_protect(address,size,permissions);self.segments.append((address,address+size,permissions,seg['segment']))
  self.u.mem_map(0x20000000,0x200000,3);self.u.mem_map(0x30000000,0x200000,3);self.u.reg_write(UC_ARM64_REG_SP,0x201f0000);self.u.hook_add(UC_HOOK_CODE,self.hook)
  self.level_text={};self.opacity={};self.strings={};self.textures=[];self.deleted=[];self.heapnext=0x30040000;self.cap=0x30001000;self.scene=0x30002000;self.manager=0x30003000;self.state=0x30004000;self.owner=0x30005000;self.catalog=0x30006000;self.event=0x30007000;self.sender=0x30008000;self.button=0x30009000;self.stop=base+0x16abf00;self.renderer=base+0x16abf40;self.vtable=0x3000a000;self.core_fail=False;self.ui_original=(False,False);self.calls=[];self.sounds=[]
  self.panel=0x3000c000;self.labels={3:0x3000d000,4:0x3000e000};self.textnodes={3:0x3000f000,4:0x30011000};self.childcall=base+0x16abf50;self.opacitycall=base+0x16abf60;self.positioncall=base+0x16abf70
  self.w(self.scene+0x2d0,self.panel)
  for node in [self.button,self.panel,*self.labels.values(),*self.textnodes.values()]:self.w(node,self.vtable)
  for off,target in [(0x210,self.childcall),(0x470,self.opacitycall),(0xb8,self.positioncall),(0x150,base+0xe6ee38),(0x558,base+0xe0f400),(0x618,self.renderer),(0x628,self.renderer)]:self.w(self.vtable+off,target)
 def w(self,p,v):self.u.mem_write(p,struct.pack('<Q',v))
 def wi(self,p,v):self.u.mem_write(p,struct.pack('<I',v))
 def hook(self,u,pc,size,ctx):
  if pc==self.base+0x8eb8a8:self.selected=(u.reg_read(UC_ARM64_REG_X0),u.reg_read(UC_ARM64_REG_X1),u.reg_read(UC_ARM64_REG_X2));u.emu_stop()
  elif pc==self.base+0x86af60:
   manager,target,force,old=[u.reg_read(UC_ARM64_REG_X0+i) for i in range(4)]
   assert manager==self.manager and force==1
   self.calls.append((target,force,old))
   if not self.core_fail:self.wi(self.state+0x28,target);self.wi(self.state+0x38,target);self.selected=(self.scene,target,self.button)
   u.reg_write(UC_ARM64_REG_X0,int(not self.core_fail));u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.base+0xb6bde8:
   args=[u.reg_read(UC_ARM64_REG_X0+i) for i in range(5)];assert args==[0x3000b000,16,1,0,0];self.sounds.append(args);u.reg_write(UC_ARM64_REG_X0,1);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc in [self.base+0x8f0da8,self.base+0x8f22a8]:
   # Original rendering may take any path and leave the tab hidden/disabled.
   # Return with its first SUB SP undone, as its own complete epilogue does.
   button=u.reg_read(UC_ARM64_REG_X1);self.u.mem_write(button+0x1c1,bytes([self.ui_original[0]]));self.u.mem_write(button+0x2b2,bytes([self.ui_original[1]]))
   c=3 if pc==self.base+0x8f0da8 else 4;self.opacity[button]=0;self.u.mem_write(self.labels[c]+0x1c1,b'\0');self.u.mem_write(self.textnodes[c]+0x1c1,b'\0')
   stack=0x1f0 if pc==self.base+0x8f0da8 else 0x140;u.reg_write(UC_ARM64_REG_SP,u.reg_read(UC_ARM64_REG_SP)+stack);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.childcall:
   node=u.reg_read(UC_ARM64_REG_X0);key=self.strings[u.reg_read(UC_ARM64_REG_X1)];value=self.labels.get(int(key[9]),0) if key.startswith('diffLabel') else next((self.textnodes[c] for c in [3,4] if self.labels[c]==node and key=='label'),0);u.reg_write(UC_ARM64_REG_X0,value);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.opacitycall:
   self.opacity[u.reg_read(UC_ARM64_REG_X0)]=u.reg_read(UC_ARM64_REG_X1);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.positioncall:u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.base+0xbdf960:
   diff=u.reg_read(UC_ARM64_REG_X0);dest=u.reg_read(UC_ARM64_REG_X8);value=str(struct.unpack('<I',u.mem_read(diff+0x110,4))[0])+('+' if u.mem_read(diff+0x114,1)==b'\1' else '');raw=value.encode();u.mem_write(dest,raw+bytes(23-len(raw))+bytes([len(raw)]));u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.base+0xe4c02c:
   self.level_text[u.reg_read(UC_ARM64_REG_X0)]=self.strings[u.reg_read(UC_ARM64_REG_X1)];u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.base+0xbdf550:u.reg_write(UC_ARM64_REG_X0,0xffaabb);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.base+0xe93868:u.mem_write(u.reg_read(UC_ARM64_REG_X0),bytes([200,200,200,255]));u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc in [self.base+0xe4c50c,self.base+0xe4c1d0]:u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.base+0xebdb28:
   dst=u.reg_read(UC_ARM64_REG_X0);src=u.reg_read(UC_ARM64_REG_X1);v=bytes(u.mem_read(src,160)).split(b'\0')[0].decode();self.strings[dst]=v;self.heapnext+=256;heap=self.heapnext;u.mem_write(heap,v.encode()+b'\0');u.mem_write(dst,struct.pack('<QQQ',heap,len(v),0x8000000000000100));u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.base+0xeb75bc:
   self.textures.append(tuple(self.strings[u.reg_read(UC_ARM64_REG_X0+i)] for i in [1,2,3]));u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.base+0x11b1e38:self.deleted.append(u.reg_read(UC_ARM64_REG_X0));u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.renderer:u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==self.stop:u.emu_stop()
 def configure(self,current,charts):
  self.w(self.cap+8,self.scene);self.w(self.scene+0x2f0,self.manager);self.w(self.manager,self.state);self.wi(self.state+0x28,current);self.wi(self.state+0x38,current);self.u.mem_write(self.scene+0x404,bytes([int(current!=3)]));self.w(self.sender,self.button);self.wi(self.event,2)
  self.w(self.base+0x16781d8,self.owner);self.w(self.owner+0x20,self.catalog);end=self.catalog+0x20
  nodes=[0x30010000+i*0x100 for i in range(len(charts))]
  def tree(lo,hi,parent):
   if lo==hi:return 0
   n=(lo+hi)//2;p=nodes[n];self.w(p,tree(lo,n,p));self.w(p+8,tree(n+1,hi,p));self.w(p+0x10,parent);song=0x30100000+n*0x400;self.w(p+0x38,song);self.u.mem_write(song+0x250,bytes(int(c in charts[n]) for c in range(5)));return p
  for n,classes in enumerate(charts):
   song=0x30100000+n*0x400
   for c in range(5):
    diff=0x30140000+(n*5+c)*0x180;self.w(song+0x228+c*8,diff if c in classes else 0);self.wi(diff+0x110,7+c);self.wi(diff+0x124,c);self.wi(diff+0x128,c)
  root=tree(0,len(charts),end);self.w(end,root);self.w(self.catalog+0x18,nodes[0] if nodes else end)
 def run(self,pc,requested=4,event=2,raw=False):
  self.selected=None;self.wi(self.cap+0x10,requested);self.wi(self.event,event)
  for n in range(3,19):self.u.reg_write(UC_ARM64_REG_X0+n,0x123400+n)
  self.u.reg_write(UC_ARM64_REG_X0,self.scene if raw else self.cap);self.u.reg_write(UC_ARM64_REG_X1,requested if raw else self.sender);self.u.reg_write(UC_ARM64_REG_X2,self.button if raw else self.event);self.u.reg_write(UC_ARM64_REG_LR,self.stop)
  saved=[self.u.reg_read(UC_ARM64_REG_X0+n) for n in range(19,29)];self.u.emu_start(self.base+pc,self.stop+4,count=600000);assert self.u.reg_read(UC_ARM64_REG_PC) in [self.stop,self.base+0x8eb8a8],hex(self.u.reg_read(UC_ARM64_REG_PC));assert saved==[self.u.reg_read(UC_ARM64_REG_X0+n) for n in range(19,29)]
  return None if self.selected is None else self.selected[1]

def main():
 original=(ROOT/'binaries/Arc-mobile').read_bytes();fixed,patch=repair_main(original,(ROOT/'difficulty.o').read_bytes());checks=[];matrix=0
 # Exact device failure: r15 branched to a file offset lying inside RW DATA.
 bad=bytearray(fixed);bad[0x8f778c:0x8f7790]=branch(0x8f778c,ISLAND_FILE)
 failure=Main(bytes(bad),0x100000000);failure.configure(4,[{0,1,2,4},{3}])
 try:failure.run(0x8f7778,4)
 except UcError as e:assert e.errno==UC_ERR_FETCH_PROT and failure.u.reg_read(UC_ARM64_REG_PC)==failure.base+ISLAND_FILE
 else:raise AssertionError('r15 DATA execution was not reproduced')
 assert next(seg for seg in failure.segments if seg[0]<=failure.base+ISLAND_FILE<seg[1])[3]=='__DATA'
 checks.append('r15_device_instruction_abort_reproduced_with_real_DATA_nonexecute_permissions')
 old=Main(original,0x100000000);old.configure(4,[{0,1,2,4},{3}]);assert old.run(0x8f7778,4)==4
 # The callback used to select Eternal again; it did not reach the BYD-only row.
 checks.append('reproduces_old_selected_ETR_callback_requests_ETR_again')
 for base in [0x100000000,0x123000000,0x700000000]:
  m=Main(fixed,base)
  assert next(seg for seg in m.segments if seg[0]<=base+ISLAND<seg[1])[2]&4
  assert bytes(m.u.mem_read(base+ISLAND,16))==fixed[ISLAND_FILE:ISLAND_FILE+16]
  checks.append(hex(base)+'_new_branch_target_is_loaded_from_RX_segment_at_actual_VM_address')
  for current,requested,mask in itertools.product(range(5),range(5),range(32)):
   charts=[set(c for c in range(5) if mask&(1<<c))];m.configure(current,charts)
   expected=7-requested if requested>=3 and current==requested else requested
   if expected>=3 and expected not in charts[0]:expected=None
   result=m.run(0x8f7778,requested);assert result==expected,(hex(base),current,requested,mask,result,expected)
   if result is not None:assert m.selected[0]==m.scene and m.selected[2]==m.button
   matrix+=1
  m.configure(4,[{0,1,2,4},{3}]);assert m.run(0x8f7778,4)==3;checks.append(hex(base)+'_ETR_repeated_tap_reaches_distinct_BYD_only_song')
  m.configure(3,[{0,1,2,4},{3}]);assert m.run(0x8f7778,3)==4;checks.append(hex(base)+'_BYD_repeated_tap_returns_ETR')
  for shape in [[set(),set(),{3},set(),set()],[set(),set(),set(),set(),{3}],[{3},set(),set(),set(),set()]]:
   m.configure(4,shape);assert m.run(0x8f7778,4)==3
  checks.append(hex(base)+'_native_tree_left_right_and_parent_successor_walk')
  for charts in [[],[{4}],[set(),set()]]:
   m.configure(4,charts);assert m.run(0x8f7778,4) is None
  checks.append(hex(base)+'_missing_target_and_empty_catalog_keep_current_selection')
  for event in [0,1,3]:m.configure(4,[{3,4}]);assert m.run(0x8f7778,4,event) is None
  checks.append(hex(base)+'_only_release_event_changes_difficulty')
  for requested in [5,0xffffffff]:m.configure(4,[{3,4}]);assert m.run(0x8f7778,requested) is None
  checks.append(hex(base)+'_invalid_difficulty_rejected')
  for address in [m.cap+8,m.scene+0x2f0,m.manager,m.base+0x16781d8,m.owner+0x20]:
   m.configure(4,[{3,4}]);m.w(address,0);assert m.run(0x8f7778,4) is None
  checks.append(hex(base)+'_uninitialized_scene_manager_and_catalog_guarded')
  m.configure(4,[set(),set()]);node=0x30010000;m.w(node+8,node);assert m.run(0x8f7778,4) is None;checks.append(hex(base)+'_cyclic_tree_exits_at_bounded_budget')
  for target in [3,4]:
   m.configure(4,[{3,4}]);assert m.run(0x8f7884,target,raw=True)==target
   m.configure(4,[]);assert m.run(0x8f7884,target,raw=True) is None
  checks.append(hex(base)+'_existing_swap_button_shares_availability_guard')
  # Execute post-refresh wrappers and actual native Node/Widget state setters.
  for filtered,preferred,original_visible,original_enabled in itertools.product([0,2,3,4],[0,1],[False,True],[False,True]):
   m.configure(filtered,[{0,1,2,4},{3}]);m.u.mem_write(m.scene+0x404,bytes([preferred]));m.ui_original=(original_visible,original_enabled)
   expected_class=4
   for c,entry in [(3,0x8f0da4),(4,0x8f22a4)]:
    m.u.reg_write(UC_ARM64_REG_X0,m.scene);m.u.reg_write(UC_ARM64_REG_X1,m.button);m.u.reg_write(UC_ARM64_REG_X2,0x30100000);m.u.reg_write(UC_ARM64_REG_LR,m.stop);m.u.emu_start(base+entry,m.stop+4,count=3000)
    assert m.u.reg_read(UC_ARM64_REG_PC)==m.stop
    expected=int(c==expected_class)
    assert m.u.mem_read(m.button+0x1c1,1)==bytes([expected]) and m.u.mem_read(m.button+0x2b2,1)==bytes([expected])
  checks.append(hex(base)+'_all_refresh_outcomes_repaired_with_real_native_Node_and_Widget_setters')
  # The selected row may be a fallback; the global filter remains authoritative.
  m.configure(2,[{0,1,2,4},{3}]);m.wi(m.state+0x38,4);assert m.run(0x8f7778,4)==3
  checks.append(hex(base)+'_ETR_filter_with_FTR_fallback_row_still_toggles_BYD')
  m.configure(4,[{0,1,2,4},{3}]);m.core_fail=True;previous=bytes(m.u.mem_read(m.scene+0x404,1));assert m.run(0x8f7778,4) is None;assert bytes(m.u.mem_read(m.scene+0x404,1))==previous;m.core_fail=False
  checks.append(hex(base)+'_failed_native_rebuild_preserves_previous_mode_preference')
  # Continuous switching, with original refreshes disabling/hiding tabs each time.
  for mode in ['matching_selected_row','fallback_FTR_selected_row']:
   m.configure(4,[{0,1,2,4},{3}]);m.calls=[]
   for turn in range(100):
    current=struct.unpack('<I',m.u.mem_read(m.state+0x38,4))[0]
    if mode=='fallback_FTR_selected_row' and current==4:m.wi(m.state+0x28,2)
    assert m.run(0x8f7778,current)==7-current
    filtered=7-current
    for c,entry in [(3,0x8f0da4),(4,0x8f22a4)]:
     m.ui_original=(False,False);m.u.reg_write(UC_ARM64_REG_X0,m.scene);m.u.reg_write(UC_ARM64_REG_X1,m.button);m.u.reg_write(UC_ARM64_REG_X2,0x30100400 if filtered==3 else 0x30100000);m.u.reg_write(UC_ARM64_REG_LR,m.stop);m.u.emu_start(base+entry,m.stop+4,count=3000)
     assert m.u.mem_read(m.button+0x1c1,1)==bytes([int(c==filtered)]) and m.u.mem_read(m.button+0x2b2,1)==bytes([int(c==filtered)])
   assert len(m.calls)==100
   checks.append(hex(base)+'_'+mode+'_100_consecutive_switches_survive_every_refresh')
  m.configure(4,[{3,4}]);m.w(m.owner+0x10,0x3000b000);m.sounds=[];assert m.run(0x8f7778,4)==3 and len(m.sounds)==1;m.w(m.owner+0x10,0)
  checks.append(hex(base)+'_successful_change_retains_native_click_feedback')
  for entry in [0x8f0da4,0x8f22a4]:
   for null_arg in range(3):
    m.configure(4,[{3,4}]);args=[m.scene,m.button,0x30100000];args[null_arg]=0
    for n,value in enumerate(args):m.u.reg_write(UC_ARM64_REG_X0+n,value)
    m.u.reg_write(UC_ARM64_REG_LR,m.stop);m.u.emu_start(base+entry,m.stop+4,count=3000);assert m.u.reg_read(UC_ARM64_REG_PC)==m.stop
  checks.append(hex(base)+'_uninitialized_UI_update_arguments_return_without_entering_renderer')
  # Cross-check native flag accessor, not a guessed class-bit encoding.
  m.configure(4,[{3}]);song=0x30100000
  for c in range(5):
   m.u.reg_write(UC_ARM64_REG_X0,song);m.u.reg_write(UC_ARM64_REG_X1,c);m.u.reg_write(UC_ARM64_REG_LR,m.stop);m.u.emu_start(base+0x84eb80,m.stop+4,count=100);assert m.u.reg_read(UC_ARM64_REG_X0)==int(c==3)
  checks.append(hex(base)+'_availability_bytes_match_real_native_getter')
 allowed=set()
 for edit in patch['edits']:allowed.update(range(edit['offset'],edit['offset']+len(bytes.fromhex(edit['new']))))
 assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(original,fixed)));checks.append('all_main_changes_restricted_to_declared_ranges')
 result=dict(passed=True,checks=len(checks),matrix_cases=matrix,cases=checks,scope=__doc__,main_sha256=patch['output_sha256']);(ROOT/'difficulty-regression.json').write_text(json.dumps(result,indent=2)+'\n');print('Native difficulty regression PASS',len(checks),'cases +',matrix,'matrix combinations')
if __name__=='__main__':main()
