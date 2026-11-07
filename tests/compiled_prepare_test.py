"""Run real compiled Hold renderer and preparation sound gates in ARM64 Unicorn."""
import argparse,struct,json,math
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
from native_clock_test import load

def exercise(plugin,game,variant):
 uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM);base=0x40000000;load(uc,game,0);load(uc,plugin,base)
 uc.mem_map(0x60000000,0x20000);uc.mem_map(0x70000000,0x20000);uc.mem_map(0x71000000,0x20000)
 uc.reg_write(UC_ARM64_REG_TPIDR_EL0,0x60010000)
 with open(plugin,'rb') as f:
  e=ELFFile(f);symbols={s.name:base+s['st_value'] for s in e.get_section_by_name('.symtab').iter_symbols() if s['st_value']};imports={}
  for section in e.iter_sections():
   if section['sh_type']!='SHT_RELA':continue
   dyn=e.get_section(section['sh_link'])
   for reloc in section.iter_relocations():
    kind=reloc['r_info_type'];name=dyn.get_symbol(reloc['r_info_sym']).name;value=dyn.get_symbol(reloc['r_info_sym'])['st_value']
    if kind==1027:target=base+reloc['r_addend']
    elif kind in [257,1025,1026]:
     if value:target=base+value+reloc['r_addend']
     else:
      if name not in imports:imports[name]=0x71000000+len(imports)*16
      target=imports[name]
    else:raise AssertionError(('unsupported relocation',kind))
    uc.mem_write(base+reloc['r_offset'],struct.pack('<Q',target))
 def sym(prefix):return next(v for k,v in symbols.items() if k==prefix or k.startswith(prefix+'.') or k.startswith(prefix+'Pv'))
 def setvar(prefix,value,fmt='<Q'):uc.mem_write(sym(prefix),struct.pack(fmt,value))

 scene=0x60005000;node=0x60006000;note=0x60007000;vtable=0x60008000
 setvar('_ZL5scene',scene);setvar('_ZL7enabled',1,'<I');setvar('_ZL8autoplay',0,'<I')
 uc.mem_write(node,struct.pack('<Q',vtable));uc.mem_write(node+0x2a8,struct.pack('<Q',note));uc.mem_write(note+0x18,struct.pack('<ii',1000,2000));uc.mem_write(vtable+0x150,struct.pack('<Q',0x7101e000))
 setvar('_ZL18holdVisualOriginal',0x7101e010);setvar('_ZL13soundOriginal',0x7101e020)
 visible=[False];sounds=[0];scheduled=[0];judgements=[0,0,0]
 judgement_paths=['judgement','automaticJudgement','tapJudgement']
 for i,name in enumerate(judgement_paths):
  original=name+'Original'
  setvar(f'_ZL{len(original)}{original}',0x7101e040+16*i)
 def callback(uc,address,size,user):
  if address==0x7101e000:visible[0]=bool(uc.reg_read(UC_ARM64_REG_W1))
  elif address==0x7101e010:visible[0]=True
  elif address==0x7101e020:sounds[0]+=1;uc.reg_write(UC_ARM64_REG_W0,123)
  elif address==0x7101e030:scheduled[0]+=1
  elif address in (0x7101e040,0x7101e050,0x7101e060):
   judgements[(address-0x7101e040)//16]+=1;uc.reg_write(UC_ARM64_REG_W0,1)
  elif address in imports.values():
   name=next(k for k,v in imports.items() if v==address)
   if name=='llround':
    value=struct.unpack('<d',struct.pack('<Q',uc.reg_read(UC_ARM64_REG_D0)))[0];uc.reg_write(UC_ARM64_REG_X0,(math.floor(value+.5) if value>=0 else math.ceil(value-.5))&0xffffffffffffffff)
   elif name=='__android_log_print':uc.reg_write(UC_ARM64_REG_W0,0)
   else:raise AssertionError(name)
  else:return
  uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR))
 uc.hook_add(UC_HOOK_CODE,callback)
 def call(prefix,args):
  for reg,value in zip([UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4],args):uc.reg_write(reg,value&0xffffffffffffffff)
  uc.reg_write(UC_ARM64_REG_SP,0x7001f000);uc.reg_write(UC_ARM64_REG_LR,0x70000000);uc.emu_start(sym(prefix),0x70000000,count=100000)
  return uc.reg_read(UC_ARM64_REG_W0)
 flags=[('_ZL7priming','<B'),('_ZL15simulatorActive','<I'),('_ZL10previewing','<I'),('_ZL16waitingTransport','<B'),('_ZL6leadIn','<B')]
 def reset():
  for prefix,fmt in flags:setvar(prefix,0,fmt)
  setvar('_ZL11pendingSeek',-2147483648,'<i')
 soundcases=0
 for flag in [None]+flags+[('_ZL11pendingSeek','<i')]:
  reset()
  if flag:setvar(flag[0],1,flag[1])
  for effect in [0,1,2,76,500]:
   before=sounds[0];call('_ZL9soundHook',[0,effect,1500,0,0]);assert sounds[0]-before==(0 if flag else 1),(plugin,flag,effect);soundcases+=1
 holdcases=0
 for mode in ['_ZL7priming','_ZL15simulatorActive','_ZL10previewing']:
  for consumed in [0,1]:
   for now in [1000,1500,2000,2500]:
    reset();setvar(mode,1,'<B' if mode=='_ZL7priming' else '<I');uc.mem_write(note+0xc,bytes([consumed]));visible[0]=True
    call('_ZL14holdVisualHook',[node,now]);assert visible[0]==(not consumed and now<2000),(plugin,mode,consumed,now,visible[0]);holdcases+=1
  inputcases=0
 for flag in [None]+flags+[('_ZL11pendingSeek','<i')]:
  reset()
  if flag:setvar(flag[0],1,flag[1])
  blocked=call('Java_moe_practice_PracticeOverlay_inputBlocked',[0,0])
  expected=flag is not None and flag[0] not in ['_ZL15simulatorActive','_ZL10previewing']
  assert bool(blocked)==expected,(plugin,flag,blocked)
  setvar('_ZL10previewing',1,'<I')
  assert not call('Java_moe_practice_PracticeOverlay_inputBlocked',[0,0]),'scrubbing must remain interactive'
  inputcases+=2
 judgementcases=0
 for flag in [None]+flags+[('_ZL11pendingSeek','<i'),('_ZL13transitioning','<B')]:
  reset();setvar('_ZL13transitioning',0,'<B')
  if flag:setvar(flag[0],1,flag[1])
  if flag and flag[0]=='_ZL15simulatorActive':setvar('_ZL7priming',1,'<B')
  for i,name in enumerate(judgement_paths):
   hook=name+'Hook';before=judgements[i]
   result=call(f'_ZL{len(hook)}{hook}',[0x6000b000,note,7])
   assert judgements[i]-before==(0 if flag else 1),(plugin,flag,name)
   if name=='tapJudgement':assert bool(result)==(flag is None)
   judgementcases+=1
 reset()
 # Old nested ArcTaps must be consumed even when their containing arc ended.
 preparecases=0;arc_type=0x1918058 if variant=='shell' else 0x1a62438
 uc.mem_write(note,struct.pack('<Q',arc_type));uc.mem_write(note+0x120,struct.pack('<QQ',0x6000b000,0x6000b010));uc.mem_write(0x6000b000,struct.pack('<QQ',0x6000c000,0x6000d000))
 for end,target,tap_times in [(3000,138482,[2000,3000]),(160000,138482,[2000,138482])]:
  uc.mem_write(note+0x1c,struct.pack('<i',end));uc.mem_write(note+0xc,b'\0')
  for addr,t in zip([0x6000c000,0x6000d000],tap_times):uc.mem_write(addr+0x18,struct.pack('<i',t));uc.mem_write(addr+0xc,b'\0')
  call('_ZL11prepareNote',[note,target])
  for addr,t in zip([0x6000c000,0x6000d000],tap_times):assert bool(uc.mem_read(addr+0xc,1)[0])==(t<target)
  preparecases+=1
 # Actual compiled provider hook mutates its by-value event vector to output ms.
 setvar('_ZN11scheduledFxL16scheduleOriginalE',0x7101e030);setvar('_ZL13buildingScene',1,'<B');setvar('_ZL7enabled',1,'<I')
 uc.mem_write(0x60009000,struct.pack('<QQQ',0x6000a000,0x6000a060,0x6000a060));schedulecases=0
 for hundredths in range(25,201):
  rate=hundredths/100;setvar('_ZL5speed',rate,'<f');actual_rate=struct.unpack('<f',struct.pack('<f',rate))[0]
  for i,t in enumerate([0,10000,138482]):uc.mem_write(0x6000a000+i*32+24,struct.pack('<i',t))
  before=scheduled[0];call('_ZN11scheduledFxL8scheduleE',[0x60005000,0x60009000]);assert scheduled[0]==before+1
  for i,t in enumerate([0,10000,138482]):assert struct.unpack('<i',uc.mem_read(0x6000a000+i*32+24,4))[0]==math.floor(t/actual_rate+.5)
  schedulecases+=1
 return {'scheduled_fx_rate_cases':schedulecases,'nested_arctap_prepare_cases':preparecases,'input_gate_cases':inputcases,'sound_gate_cases':soundcases,'judgement_gate_cases':judgementcases,'hold_visibility_cases':holdcases,'native_renderer_forced_to_reenable_old_hold':True}

p=argparse.ArgumentParser();p.add_argument('--shell-plugin',required=True);p.add_argument('--full-plugin',required=True);p.add_argument('--shell-game',required=True);p.add_argument('--full-game',required=True);p.add_argument('--report',required=True);a=p.parse_args()
r={'result':'passed','method':'Real compiled ARM64 production sound/hold hooks; fake original renderer deliberately makes every Hold visible','variants':{n:exercise(getattr(a,n+'_plugin'),getattr(a,n+'_game'),n) for n in ['shell','full']},'limitations':'Renderer dependency stubbed; native window/input and GPU behavior require runtime checks'}
Path(a.report).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
