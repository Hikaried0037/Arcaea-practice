"""Actual compiled SHA256 and native null-row filtering; framework vector append is a host substitute."""
from pathlib import Path
import hashlib,json,struct,zipfile
from test_library_native import Native
from test_difficulty import Main
from patch_difficulty import repair_main
from unicorn import UcError,UC_HOOK_CODE
from unicorn.arm64_const import *
ROOT=Path(__file__).resolve().parent
checks=[]
m=Native()
for size in [0,1,3,55,56,63,64,65,127,128,129,255,1000,4096]:
 raw=bytes((i*17+3)%256 for i in range(size));out=m.alloc(65);m.call('_al_sha256',m.alloc(raw or b'x'),size,out)
 assert bytes(m.u.mem_read(out,65))==hashlib.sha256(raw).hexdigest().encode()+b'\0'
 checks.append('compiled_SHA256_'+str(size))
original=(ROOT/'binaries/Arc-mobile').read_bytes();fixed,report=repair_main(original,(ROOT/'difficulty.o').read_bytes())
def rows(image,values):
 n=Main(image,0x100000000);array=0x30018000;seen=[]
 for i,v in enumerate(values):
  n.w(array+8*i,v)
  if v:n.wi(v+8,1)
 def hook(u,pc,size,ctx):
  if pc==n.base+0x88567c:seen.append(struct.unpack('<Q',u.mem_read(u.reg_read(UC_ARM64_REG_X1),8))[0]);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif pc==n.base+0x87cbf0:u.emu_stop()
 n.u.hook_add(UC_HOOK_CODE,hook);n.u.reg_write(UC_ARM64_REG_X25,array);n.u.reg_write(UC_ARM64_REG_X26,array+8*len(values));n.u.emu_start(n.base+0x87cbc8,n.stop,count=10000)
 assert n.u.reg_read(UC_ARM64_REG_PC)==n.base+0x87cbf0
 assert seen==[v for v in values if v]
 for v in set(values)-{0}:assert struct.unpack('<I',n.u.mem_read(v+8,4))[0]==1+values.count(v)
try:rows(original,[0])
except UcError:checks.append('original_null_row_retain_crash_reproduced')
else:raise AssertionError('old crash not reproduced')
for values in [[0],[0,0],[0x30020000],[0,0x30020000,0,0x30021000,0x30020000,0]]:
 rows(fixed,values);checks.append('fixed_null_rows_filtered_order_and_real_retain_'+str(len(values)))
# Exercise the real assembly resource binding with framework string/UI calls substituted.
for c in [3,4]:
 for selected in [0,1]:
  n=Main(fixed,0x100000000);n.u.reg_write(UC_ARM64_REG_X0,n.button);n.u.reg_write(UC_ARM64_REG_X1,c);n.u.reg_write(UC_ARM64_REG_X2,selected);n.u.reg_write(UC_ARM64_REG_X3,0);n.u.reg_write(UC_ARM64_REG_LR,n.stop)
  n.u.emu_start(n.base+report['symbols']['_difficulty_textures'],n.stop+4,count=1000)
  assert len(n.deleted)==3 and len(set(n.deleted))==3
  expected='layouts/1080/songselect/difficulty_selector_'+str(c)
  assert n.textures==[(expected+('_selected' if selected else '')+'.png',expected+'_selected.png',expected+'_selected.png')]
  checks.append('native_official_texture_class_'+str(c)+'_selected_'+str(selected))
n=Main(fixed,0x100000000);n.configure(3,[{3},{4}]);n.wi(n.state+0x38,4)
for c,entry in [(3,0x8f0da4),(4,0x8f22a4)]:
 n.u.reg_write(UC_ARM64_REG_X0,n.scene);n.u.reg_write(UC_ARM64_REG_X1,n.button);n.u.reg_write(UC_ARM64_REG_X2,0x30100000);n.u.reg_write(UC_ARM64_REG_LR,n.stop);n.u.emu_start(n.base+entry,n.stop+4,count=1000)
 assert n.u.mem_read(n.button+0x1c1,1)==bytes([int(c==3)])
checks.append('BYD_actual_row_overrides_stale_ETR_filter_for_visible_texture')
with zipfile.ZipFile(__import__('os').environ.get('ORIGINAL_IPA', str(ROOT.parent/'original.ipa'))) as z:
 for c in [3,4]:
  for suffix in ['', '_selected']:assert z.read('Payload/Arc-mobile.app/layouts/1080/songselect/difficulty_selector_'+str(c)+suffix+'.png').startswith(b'\x89PNG')
checks.append('all_four_official_resources_exist_in_host')
result=dict(passed=True,checks=len(checks),cases=checks,scope=__doc__)
(ROOT/'r18-regression.json').write_text(json.dumps(result,indent=2)+'\n');print('R18 regression PASS',len(checks))
