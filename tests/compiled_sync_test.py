"""Exercise final plugin clock hooks against the original game clocks in Unicorn.
Quantised FMOD positions are simulated; this is not a physical GPU benchmark.
"""
import argparse,struct,math,json
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
from native_clock_test import load

def exercise(plugin,game,profile,expect_smooth=True):
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
 queries=[0];music=[0];fake_position=0x7101f000
 uc.mem_write(0x60004000+0x2c0,struct.pack('<Q',0x60008000))
 uc.mem_write(0x60008038,struct.pack('<QQ',0x60008400,0x60008410))
 uc.mem_write(0x60008400,struct.pack('<QQ',0x60009000,0x60009100))
 setvar('_ZL16getMusicPosition',fake_position)
 def callback(uc,address,size,user):
  if address==fake_position:
   queries[0]+=1;uc.mem_write(uc.reg_read(UC_ARM64_REG_X1),struct.pack('<I',max(0,music[0])));uc.reg_write(UC_ARM64_REG_W0,0)
  elif address==tick_fn:uc.reg_write(UC_ARM64_REG_W0,now[0])
  elif address==start_fn:starts[0]+=1
  elif address in reverse:
   name=reverse[address]
   if name=='lround':
    value=struct.unpack('<d',struct.pack('<Q',uc.reg_read(UC_ARM64_REG_D0)))[0];uc.reg_write(UC_ARM64_REG_X0,(math.floor(value+.5) if value>=0 else math.ceil(value-.5))&0xffffffffffffffff)
   elif name in ['__android_log_print','pthread_mutex_lock','pthread_mutex_unlock']:uc.reg_write(UC_ARM64_REG_W0,0)
   else:raise AssertionError(('unexpected imported call',name))
  else:return
  uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR))
 uc.hook_add(UC_HOOK_CODE,callback)
 def call():
  uc.reg_write(UC_ARM64_REG_X0,clock);uc.reg_write(UC_ARM64_REG_SP,0x7001f000);uc.reg_write(UC_ARM64_REG_LR,0x70000000);uc.emu_start(sym('_ZL9clockHookPv'),0x70000000,count=100000)
 def read(off):return struct.unpack('<i',uc.mem_read(clock+off,4))[0]
 def write(off,val):uc.mem_write(clock+off,struct.pack('<i',val))

 records=[]
 for rate in [.5,1.,2.]:
  uc.mem_write(clock,b'\0'*64);uc.mem_write(clock+0x2d,b'\1');write(0x30,0);uc.mem_write(chart+0xc4,struct.pack('<i',0))
  setvar('_ZL17offsetCalibration.0',0,'<i');setvar('_ZL17offsetCalibration.1',0,'<i');setvar('_ZL17offsetCalibration.2',0,'<i')
  setvar('_ZL5speed',rate,'<f');setvar('_ZL9lastSpeed',rate,'<f');setvar('_ZL9lastClock',0);setvar('_ZL8fraction',0.,'<d');setvar('_ZL12musicSyncing',0,'<B');setvar('_ZL9wasPaused',0,'<B')
  now[0]=8000;music[0]=0;call();first=read(0x20)-read(0x28)
  # Lead-in completion and a native pause/resume each start a sync window.
  for phase in ['lead_complete','resume']:
   if phase=='lead_complete':
    setvar('_ZL12musicSyncing',1,'<B')
    try:setvar('_ZL10syncTarget',read(0x20)-read(0x28),'<i')
    except StopIteration:pass
    try:uc.mem_write(sym('_ZL15smoothAudioSync'),b'\0'*40)
    except StopIteration:pass
   else:
    uc.mem_write(clock+0x2c,b'\1');write(0x24,read(0x20)-read(0x28));call()
    now[0]+=5000;call();uc.mem_write(clock+0x2c,b'\0');call()
   initial=read(0x20)-read(0x28);origin=now[0];before=queries[0];times=[initial]
   for frame in range(1,434):
    elapsed=round(frame*1000/144);now[0]=origin+elapsed
    music[0]=int((initial+elapsed*rate)//23)*23
    call();times.append(read(0x20)-read(0x28))
   repeats=sum(a==b for a,b in zip(times,times[1:]));backwards=sum(b<a for a,b in zip(times,times[1:]));jumps=max(b-a for a,b in zip(times,times[1:]))
   record={'rate':rate,'phase':phase,'queries':queries[0]-before,'repeated_chart_frames':repeats,'backward_chart_frames':backwards,'max_chart_step_ms':jumps}
   if expect_smooth:
    assert repeats==0 and backwards==0,(plugin,record)
    assert record['queries']<=95,(plugin,record)
    assert jumps<=math.ceil(8*rate*1.08)+1,(plugin,record)
   records.append(record)
 return records

def main():
 p=argparse.ArgumentParser();p.add_argument('--full-plugin',required=True);p.add_argument('--shell-plugin',required=True);p.add_argument('--full-game',required=True);p.add_argument('--shell-game',required=True);p.add_argument('--report');p.add_argument('--baseline',action='store_true',help='Measure old hooks without requiring smooth timing');a=p.parse_args();records={}
 for name,plugin,game,profile in [('full',a.full_plugin,a.full_game,(0xd6fa64,0x1836b08,0x11998d4,0x1b595c0)),('shell',a.shell_plugin,a.shell_game,(0x109c0d4,0x16121b4,0x16e8c38,0x1964c18))]:
  records[name]=exercise(plugin,game,profile,not a.baseline)
 result={'result':'measured_baseline' if a.baseline else 'passed','method':'Unicorn execution of final compiled clockHook and original game clock, 144 Hz updates with quantised FMOD position','variants':records,'limitations':'No physical GPU/144 Hz device frame-time measurement'}
 output=json.dumps(result,indent=2)+'\n';print(output)
 if a.report:Path(a.report).write_text(output,encoding='utf-8')
if __name__=='__main__':main()
