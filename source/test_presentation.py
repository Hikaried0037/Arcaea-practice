"""Execute native tab wrappers, difficulty accessor and full native level-render control flow. Font/rasterization, string allocation, number formatting and scene lookup use host substitutes; no physical iPad rendering."""
from pathlib import Path
import json,struct,itertools
from test_difficulty import Main,ROOT
from patch_difficulty import repair_main
from unicorn.arm64_const import *
original=(ROOT/'binaries/Arc-mobile').read_bytes();fixed,report=repair_main(original,(ROOT/'difficulty.o').read_bytes());checks=[];matrix=0
def update(n,c):
 u=n.u;u.reg_write(UC_ARM64_REG_X0,n.scene);u.reg_write(UC_ARM64_REG_X1,n.button);u.reg_write(UC_ARM64_REG_X2,0x30100000);u.reg_write(UC_ARM64_REG_LR,n.stop);sp=u.reg_read(UC_ARM64_REG_SP);registers=[UC_ARM64_REG_X0+i for i in range(19,29)]+[UC_ARM64_REG_X29];saved=[u.reg_read(reg) for reg in registers];u.emu_start(n.base+(0x8f0da4 if c==3 else 0x8f22a4),n.stop+4,count=10000);assert u.reg_read(UC_ARM64_REG_PC)==n.stop;assert u.reg_read(UC_ARM64_REG_SP)==sp;assert saved==[u.reg_read(reg) for reg in registers]

# Reproduce the omitted opacity and separate-level-label state in r18.
old,_=repair_main(original,(ROOT/'previous_difficulty_r18.o').read_bytes())
n=Main(old,0x100000000);n.configure(4,[{4}]);update(n,4);assert n.opacity[n.button]==0 and n.u.mem_read(n.labels[4]+0x1c1,1)==b'\0';checks.append('r18_reproduced_texture_rebound_but_button_transparent_and_number_hidden')
for base in [0x100000000,0x123000000,0x700000000]:
 n=Main(fixed,base)
 for mask,current,preferred in itertools.product(range(32),range(5),[0,1]):
  classes={c for c in range(5) if mask&(1<<c)};n.configure(current,[classes]);n.u.mem_write(n.scene+0x404,bytes([preferred]));n.ui_original=(False,False)
  if (3 in classes)!=(4 in classes):visible=3 if 3 in classes else 4
  else:visible=current if current in [3,4] else (4 if preferred else 3)
  for c in [3,4]:
   # Native update can clear opacity/labels before returning on a locked path.
   n.textures=[];update(n,c);shown=c==visible;exists=c in classes
   assert n.u.mem_read(n.button+0x1c1,1)==bytes([shown]);assert n.u.mem_read(n.labels[c]+0x1c1,1)==bytes([shown])
   if shown:
    assert n.opacity[n.button]==(255 if exists else 160)
    assert n.opacity[n.labels[c]]==(255 if exists else 160)
    assert n.u.mem_read(n.textnodes[c]+0x1c1,1)==b'\1'
    assert n.level_text[n.textnodes[c]]==(str(7+c) if exists else '--')
    prefix='layouts/1080/songselect/difficulty_selector_'+str(c)
    selected=exists and current==c
    assert n.textures[-1]==(prefix+('_selected' if selected else '')+'.png',prefix+'_selected.png',prefix+'_selected.png')
   matrix+=1
 checks.append(hex(base)+'_all_masks_actual_class_name_number_opacity_selection_and_missing_state')
 # Both charts: changing saved mode, row and song must not retain stale digits.
 for turn in range(100):
  c=3+turn%2;n.configure(c,[{3,4}]);diff=0x30140000+c*0x180;n.wi(diff+0x110,9+turn%4);n.u.mem_write(diff+0x114,bytes([turn%2]));n.wi(n.state+0x38,7-c)
  for entry in [3,4]:update(n,entry)
  assert n.level_text[n.textnodes[c]]==str(9+turn%4)+('+' if turn%2 else '')
  assert n.u.mem_read(n.labels[7-c]+0x1c1,1)==b'\0'
 checks.append(hex(base)+'_100_song_mode_changes_refresh_real_rating_plus_and_hide_alternate_label')
 # Missing scene label panel safely skips label access, preserving texture.
 n.configure(4,[{4}]);n.w(n.scene+0x2d0,0);update(n,4);assert n.opacity[n.button]==255
 checks.append(hex(base)+'_uninitialized_label_panel_guarded')
result=dict(passed=True,checks=len(checks),matrix_cases=matrix,cases=checks,main_sha256=report['output_sha256'],scope=__doc__)
(ROOT/'presentation-regression.json').write_text(json.dumps(result,indent=2)+'\n');print('Native complete-tab presentation PASS',len(checks),'+',matrix,'matrix cases')
