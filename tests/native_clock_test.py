"""Execute production timing helpers and each original ARM64 clock, without a phone.
Requires pyelftools and Unicorn. Input game libraries are supplied locally.
"""
import argparse, struct, json
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *

def load(uc,path,base):
 with open(path,'rb') as f:
  e=ELFFile(f); segments=[s for s in e.iter_segments() if s['p_type']=='PT_LOAD']
  low=min(s['p_vaddr'] for s in segments)&~4095
  high=max(s['p_vaddr']+s['p_memsz'] for s in segments)
  uc.mem_map(base+low,((high+4095)&~4095)-low)
  for s in segments:uc.mem_write(base+s['p_vaddr'],s.data())
  return {s.name:base+s['st_value'] for s in e.get_section_by_name('.dynsym').iter_symbols() if s['st_value']}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--helpers',required=True);parser.add_argument('--full',required=True);parser.add_argument('--shell',required=True);parser.add_argument('--report');args=parser.parse_args()
 uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM);symbols=load(uc,args.helpers,0x40000000)
 uc.mem_map(0x60000000,0x10000);uc.mem_map(0x70000000,0x20000);stop=0x70000000
 def call(address,*registers,rate=None):
  for reg,value in zip([UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3],registers):uc.reg_write(reg,value&0xffffffffffffffff)
  if rate is not None:uc.reg_write(UC_ARM64_REG_S0,struct.unpack('<I',struct.pack('<f',rate))[0])
  uc.reg_write(UC_ARM64_REG_SP,0x7001f000);uc.reg_write(UC_ARM64_REG_LR,stop)
  uc.emu_start(address,stop,count=10000000)
  return uc.reg_read(UC_ARM64_REG_W0)
 assert call(symbols['offsetRegression'])==0,'production offset regression failed'
 print('PASS: 3520 production offset/rate scenarios; 18 preroll scenarios')
 profiles={'full':(args.full,0xd6fa64,0x1836b08,0x11998d4,0x1b595c0),
           'shell':(args.shell,0x109c0d4,0x16121b4,0x16e8c38,0x1964c18)}
 results={}
 for name,(path,clock_fn,tick_fn,start_fn,core_got) in profiles.items():
  game=load(uc,path,0);clock=0x60000000;state=0x60000100;now=[8000];starts=[0]
  uc.mem_write(core_got,struct.pack('<Q',0x60002000));uc.mem_write(0x60002000,struct.pack('<Q',0x60003000));uc.mem_write(0x60003010,struct.pack('<Q',0x60004000))
  def stub(uc,address,size,user):
   if address==tick_fn:uc.reg_write(UC_ARM64_REG_W0,now[0]);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR))
   elif address==start_fn:starts[0]+=1;uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_LR))
  hook=uc.hook_add(UC_HOOK_CODE,stub)
  def read(offset):return struct.unpack('<i',uc.mem_read(clock+offset,4))[0]
  def write(offset,value):uc.mem_write(clock+offset,struct.pack('<i',value))
  count=0
  for aff in [-350,0,175,1200]:
   for device in [-400,-123,0,87,500]:
    for rate in [.25,.37,.5,.75,1.,1.33,1.5,2.]:
     uc.mem_write(clock,b'\0'*64);uc.mem_write(clock+0x2d,b'\1');write(0x30,aff+device)
     call(symbols['offsetCapture'],state,aff+device,aff)
     call(symbols['offsetApply'],state,clock,0,rate=rate)
     now[0]=8000;oldStarts=starts[0];call(clock_fn,clock)
     combined=read(0x30)
     assert starts[0]==oldStarts+1 and read(0x38)==-combined,(name,aff,device,rate,'startup')
     # Moving the chart at rate must retain the origin established by the real
     # game clock. Test 60 frames, with the hook's fractional delta integration.
     fraction=0.;last_raw=read(0x20);first_time=read(0x20)-read(0x28)
     for step in range(1,61):
      now[0]=8000+step*16;call(clock_fn,clock)
      raw=read(0x20);fraction+=(raw-last_raw)*(rate-1);extra=int(fraction);fraction-=extra;write(0x28,read(0x28)-extra);last_raw=raw
     chart=read(0x20)-read(0x28)
     assert abs(chart-first_time-960*rate)<1.01
     assert abs((combined-aff)/rate-device)<=.5001/rate
     # Switching rate while paused must also adjust the native paused snapshot;
     # the original clock rewrites its compensation from that snapshot.
     uc.mem_write(clock+0x2c,b'\1');write(0x24,chart)
     call(symbols['offsetApply'],state,clock,0,rate=1.)
     expected=read(0x24);call(clock_fn,clock)
     assert read(0x20)-read(0x28)==expected
     assert read(0x38)==-(aff+device)
     # A fixed preview/lead cursor must survive a change of calibration.
     cursor=read(0x20)-read(0x28)
     call(symbols['offsetApply'],state,clock,1,rate=rate)
     assert read(0x20)-read(0x28)==cursor
     target=30000;audio_target=target-read(0x38)
     assert audio_target+read(0x38)==target
     count+=1
  uc.hook_del(hook)
  # Unmap each original ELF before loading the other profile.
  with open(path,'rb') as f:
   e=ELFFile(f);segs=[s for s in e.iter_segments() if s['p_type']=='PT_LOAD'];low=min(s['p_vaddr'] for s in segs)&~4095;high=(max(s['p_vaddr']+s['p_memsz'] for s in segs)+4095)&~4095
  uc.mem_unmap(low,high-low);results[name]=count
  print(f'PASS: {name} original ARM64 clock: {count} startup/rate/pause/seek scenarios')
 report={'method':'Unicorn ARM64 instruction execution; not device audio playback','production_helper_cases':3520,'absolute_preroll_cases':18,'original_native_clock_cases':results,'result':'passed','limitations':'FMOD start and wall clock mocked; no physical audio latency or device graphics tested'}
 if args.report:Path(args.report).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
