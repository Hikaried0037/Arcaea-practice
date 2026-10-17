"""Exercise final plugin clock hooks against the original game clocks in Unicorn.
The wall-clock/audio-start functions are stubbed; this is not an audio-device test.
"""
import argparse,struct,math,json
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
from native_clock_test import load

def exercise(plugin,game,profile):
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
 def sym(prefix):return next(v for k,v in symbols.items() if k==prefix or k.startswith(prefix+'.'))
 def setvar(prefix,value,fmt='<Q'):uc.mem_write(sym(prefix),struct.pack(fmt,value))
 clock_fn,tick_fn,start_fn,core_got=profile
 uc.mem_write(core_got,struct.pack('<Q',0x60002000));uc.mem_write(0x60002000,struct.pack('<Q',0x60003000));uc.mem_write(0x60003010,struct.pack('<Q',0x60004000))
 clock=0x60000000;scene=0x60005000;model=0x60006000;chart=0x60007000
 uc.mem_write(scene+0x3e0,struct.pack('<Q',model));uc.mem_write(model+0x30,struct.pack('<Q',clock));uc.mem_write(model+0x28,struct.pack('<Q',chart))
 setvar('_ZL5scene',scene);setvar('_ZL4base',0);setvar('_ZL13clockOriginal',clock_fn);setvar('_ZL15calibratedClock',clock);setvar('_ZL7enabled',1,'<I')
 reverse={v:k for k,v in imports.items()};now=[8000];starts=[0]
 def callback(uc,address,size,user):
  if address==tick_fn:uc.reg_write(UC_ARM64_REG_W0,now[0])
  elif address==start_fn:starts[0]+=1
  elif address in reverse:
   name=reverse[address]
   if name=='lround':
    value=struct.unpack('<d',struct.pack('<Q',uc.reg_read(UC_ARM64_REG_D0)))[0];uc.reg_write(UC_ARM64_REG_X0,(math.floor(value+.5) if value>=0 else math.ceil(value-.5))&0xffffffffffffffff)
   elif name=='__android_log_print':uc.reg_write(UC_ARM64_REG_W0,0)
   else:raise AssertionError(('unexpected imported call',name))
  else:return
  uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR))
 uc.hook_add(UC_HOOK_CODE,callback)
 def call():
  uc.reg_write(UC_ARM64_REG_X0,clock);uc.reg_write(UC_ARM64_REG_SP,0x7001f000);uc.reg_write(UC_ARM64_REG_LR,0x70000000);uc.emu_start(sym('_ZL9clockHookPv'),0x70000000,count=100000)
 def read(off):return struct.unpack('<i',uc.mem_read(clock+off,4))[0]
 def write(off,val):uc.mem_write(clock+off,struct.pack('<i',val))
 cases=0
 for aff in [-350,0,175,1200]:
  for device in [-400,-123,0,87,500]:
   for rate in [.25,.37,.5,.75,1.,1.33,1.5,2.]:
    uc.mem_write(clock,b'\0'*64);uc.mem_write(clock+0x2d,b'\1');write(0x30,aff+device);uc.mem_write(chart+0xc4,struct.pack('<i',aff))
    setvar('_ZL17offsetCalibration.0',aff,'<i');setvar('_ZL17offsetCalibration.1',device,'<i');setvar('_ZL17offsetCalibration.2',aff+device,'<i')
    setvar('_ZL5speed',rate,'<f');setvar('_ZL9lastSpeed',rate,'<f');setvar('_ZL9lastClock',0);setvar('_ZL8fraction',0.,'<d');setvar('_ZL12musicSyncing',0,'<B');setvar('_ZL9wasPaused',0,'<B')
    now[0]=8000;before=starts[0];call();assert starts[0]==before+1
    effective=read(0x30);assert read(0x38)==-effective
    assert abs(effective-aff-device*rate)<=.5001
    first=read(0x20)-read(0x28)
    for step in range(1,61):now[0]=8000+step*16;call()
    current=read(0x20)-read(0x28);assert abs(current-first-960*rate)<=1.01,(aff,device,rate,current,first)
    # Change speed during a real native pause. The hook must preserve calibration
    # after the original engine rebuilds its paused compensation field.
    uc.mem_write(clock+0x2c,b'\1');write(0x24,current);setvar('_ZL5speed',1.,'<f');call()
    assert read(0x30)==aff+device and read(0x38)==-(aff+device)
    assert read(0x20)-read(0x28)==read(0x24)
    uc.mem_write(clock+0x2c,b'\0');call();now[0]+=16;call()
    assert read(0x38)==-(aff+device)
    # Disabling practice restores the original 1x calibration, even with a
    # non-1x rate retained in the panel.
    setvar('_ZL5speed',rate,'<f');call();setvar('_ZL7enabled',0,'<I');call()
    assert read(0x30)==aff+device and read(0x38)==-(aff+device)
    setvar('_ZL7enabled',1,'<I');cases+=1
 return cases

def main():
 p=argparse.ArgumentParser();p.add_argument('--full-plugin',required=True);p.add_argument('--shell-plugin',required=True);p.add_argument('--full-game',required=True);p.add_argument('--shell-game',required=True);p.add_argument('--report');a=p.parse_args()
 counts={}
 for name,plugin,game,profile in [('full',a.full_plugin,a.full_game,(0xd6fa64,0x1836b08,0x11998d4,0x1b595c0)),('shell',a.shell_plugin,a.shell_game,(0x109c0d4,0x16121b4,0x16e8c38,0x1964c18))]:
  counts[name]=exercise(plugin,game,profile);print(f'PASS: {name} final compiled hook: {counts[name]} calibration/playback/pause/rate/toggle scenarios')
 if a.report:Path(a.report).write_text(json.dumps({'method':'Unicorn execution of final compiled plugin hook and original game clock','cases':counts,'result':'passed','limitations':'FMOD and physical audio output not executed'},indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
