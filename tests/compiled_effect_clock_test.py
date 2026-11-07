"""Execute production preparation hook plus original native 6K interpolation."""
import argparse,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
from native_clock_test import load

def exercise(plugin,game,variant):
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);base=0x40000000;load(u,game,0);load(u,plugin,base)
 u.mem_map(0x60000000,0x20000);u.mem_map(0x70000000,0x20000);u.mem_map(0x71000000,0x20000)
 u.reg_write(UC_ARM64_REG_TPIDR_EL0,0x60010000)
 with open(plugin,'rb') as f:
  e=ELFFile(f);symbols={s.name:base+s['st_value'] for s in e.get_section_by_name('.symtab').iter_symbols() if s['st_value']}
  for section in e.iter_sections():
   if section['sh_type']!='SHT_RELA':continue
   dyn=e.get_section(section['sh_link'])
   for r in section.iter_relocations():
    s=dyn.get_symbol(r['r_info_sym']);target=base+r['r_addend'] if r['r_info_type']==1027 else base+s['st_value']+r['r_addend'] if s['st_value'] else 0x71000000
    u.mem_write(base+r['r_offset'],struct.pack('<Q',target))
 def sym(prefix):return next(v for k,v in symbols.items() if k==prefix or k.startswith(prefix+'Pv') or k.startswith(prefix+'.'))
 def setv(prefix,value,fmt='<i'):u.mem_write(sym(prefix),struct.pack(fmt,value))
 model,clock,scene=0x60002000,0x60004000,0x60006000
 u.mem_write(model+0x30,struct.pack('<Q',clock));u.mem_write(clock+0x2d,b'\1')
 entry,stop,timefn=(0xb9419c,0xb942a0,0x9440b4) if variant=='shell' else (0x198bf04,0x198c07c,0x1634424)
 setv('_ZL5scene',scene,'<Q');setv('_ZL19modelUpdateOriginal',entry,'<Q')
 now=[0];saved={};commit=[False]
 def hook(u,address,size,_):
  if address==timefn:u.reg_write(UC_ARM64_REG_W0,now[0]);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
  elif address==entry:
   saved.update({r:u.reg_read(r) for r in [UC_ARM64_REG_X19,UC_ARM64_REG_X21,UC_ARM64_REG_X26]});u.reg_write(UC_ARM64_REG_X19,model)
  elif variant=='full' and address==0x198bfc0:
   # Skip the unrelated named-song transition; use original generic 6K math.
   u.reg_write(UC_ARM64_REG_PC,0x198c02c)
  elif address==stop:
   if commit[0]:u.mem_write(model+0x54,struct.pack('<i',123456))
   for r,value in saved.items():u.reg_write(r,value)
   u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook)
 def call():
  u.reg_write(UC_ARM64_REG_X0,model);u.reg_write(UC_ARM64_REG_X1,scene);u.reg_write(UC_ARM64_REG_SP,0x7001f000);u.reg_write(UC_ARM64_REG_LR,0x70000000)
  u.emu_start(sym('_ZL15modelUpdateHook'),0x70000000,count=10000)
 def reset():
  for p,f in [('_ZL7priming','<B'),('_ZL16waitingTransport','<B'),('_ZL6leadIn','<B'),('_ZL13leadRequested','<B'),('_ZL10previewing','<i')]:setv(p,0,f)
  setv('_ZL7enabled',1);setv('_ZL18preparingEffectsAt',-2147483648)
 def times(t):now[0]=t;u.mem_write(clock+0x20,struct.pack('<i',t));u.mem_write(clock+0x28,b'\0'*4)
 def params(start,duration,target):
  u.mem_write(model+0x54,struct.pack('<iiff',start,target,float(duration),1.0));u.mem_write(model+0x68,struct.pack('<iif',start,target,float(duration)))
 def values():return struct.unpack('<f',u.mem_read(model+0x60,4))[0],struct.unpack('<f',u.mem_read(model+0x74,4))[0]
 count=0
 for start,duration in [(102654,6824),(129666,284),(157250,2274)]:
  for target in [0,1]:
   for delta in [0,100,duration//2,duration,duration+5000]:
    a=start+delta
    reset();setv('_ZL7enabled',0);params(start,duration,target);times(a);call();expected=values()
    for rate in [.25,.5,1,1.5,2]:
     for mode in ['prime','wait','lead','request','preview','disabled','normal']:
      reset();setv('_ZL1a',a);actual=a-round(3000*rate);times(actual);params(start,duration,target)
      if mode=='prime':setv('_ZL7priming',1,'<B');setv('_ZL18preparingEffectsAt',a)
      elif mode=='wait':setv('_ZL16waitingTransport',1,'<B')
      elif mode=='lead':setv('_ZL6leadIn',1,'<B')
      elif mode=='request':setv('_ZL13leadRequested',1,'<B')
      elif mode=='preview':setv('_ZL10previewing',1)
      elif mode=='disabled':setv('_ZL7enabled',0)
      call();observed=values();epochs=struct.unpack('<i',u.mem_read(model+0x54,4))[0],struct.unpack('<i',u.mem_read(model+0x68,4))[0]
      assert epochs==(start,start),(mode,epochs)
      if mode in ['prime','wait','lead','request']:assert observed==expected,(variant,mode,start,duration,a,rate,observed,expected)
      else:
       reset();setv('_ZL7enabled',0);times(actual);params(start,duration,target);call();assert observed==values(),(variant,mode,'normal path modified')
      count+=1
 # Normal native event commits must not be undone by a temporary epoch scope.
 reset();times(180000);params(157250,2274,1);commit[0]=True;call();assert struct.unpack('<i',u.mem_read(model+0x54,4))[0]==123456
 return dict(cases=count,normal_native_event_preserved=True,original_native_interpolation=True)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for v in ['shell','full']:
  for k in ['plugin','game']:p.add_argument('--'+v+'-'+k,required=True)
 p.add_argument('--report',required=True);a=p.parse_args();result={'result':'passed','variants':{v:exercise(getattr(a,v+'_plugin'),getattr(a,v+'_game'),v) for v in ['shell','full']},'limits':'Native generic 6K evaluator executed; scene/GPU and full named-song transition excluded'}
 Path(a.report).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
