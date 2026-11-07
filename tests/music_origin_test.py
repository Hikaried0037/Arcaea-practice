"""Execute the shared startup helper with each supported original ARM64 clock."""
import argparse,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
from native_clock_test import load
p=argparse.ArgumentParser();p.add_argument('--helper',required=True);p.add_argument('--shell-game',required=True);p.add_argument('--full-game',required=True);p.add_argument('--report',required=True);a=p.parse_args();results={}
for name,path,clockfn,tick,start,core in [('shell',a.shell_game,0x109c0d4,0x16121b4,0x16e8c38,0x1964c18),('full',a.full_game,0xd6fa64,0x1836b08,0x11998d4,0x1b595c0)]:
 u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);load(u,path,0);load(u,a.helper,0x40000000)
 with open(a.helper,'rb') as f:e=ELFFile(f);entry=0x40000000+next(s['st_value'] for s in e.get_section_by_name('.dynsym').iter_symbols() if s.name=='initializeOrigin')
 u.mem_map(0x60000000,0x20000);u.mem_map(0x70000000,0x20000);u.reg_write(UC_ARM64_REG_TPIDR_EL0,0x60010000)
 clock=0x60000000;calls=[0]
 u.mem_write(core,struct.pack('<Q',0x60002000));u.mem_write(0x60002000,struct.pack('<Q',0x60003000));u.mem_write(0x60003010,struct.pack('<Q',0x60004000))
 def hook(u,addr,size,data):
  if addr==tick:u.reg_write(UC_ARM64_REG_W0,8000)
  elif addr==start:calls[0]+=1
  else:return
  u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);count=0
 for aff in [-3000,-1333,-350,0,175,1200]:
  for device in [-400,0,87,500]:
   for rate in [.25,.5,1,1.5,2]:
    for paused in [0,1]:
     combined=aff+round(device*rate);u.mem_write(clock,b'\0'*64);u.mem_write(clock+0x10,struct.pack('<i',8000));u.mem_write(clock+0x30,struct.pack('<i',combined));u.mem_write(clock+0x2d,b'\1');u.mem_write(clock+0x2c,bytes([paused]));before=calls[0]
     def invoke():
      u.reg_write(UC_ARM64_REG_X0,clock);u.reg_write(UC_ARM64_REG_X1,clockfn);u.reg_write(UC_ARM64_REG_SP,0x7001f000);u.reg_write(UC_ARM64_REG_LR,0x70000000);u.emu_start(entry,0x70000000,count=100000)
     invoke();origin=struct.unpack('<i',u.mem_read(clock+0x38,4))[0]
     assert origin==-combined,(name,aff,device,rate,origin)
     assert bytes(u.mem_read(clock+0x2e,1))==b'\1' and bytes(u.mem_read(clock+0x2c,1))==bytes([paused])
     assert calls[0]==before+1
     invoke();assert calls[0]==before+1,'must not start twice'
     count+=1
 results[name]={'cases':count,'negative_aff_included':-1333,'origin_matches_negative_combined_offset':True,'starts_once':True,'pause_preserved':True}
report={'result':'passed','method':'Actual original ARM64 game clocks plus compiled production initializeMusicOrigin helper in Unicorn','variants':results,'limitations':'No physical audio output measurement'};Path(a.report).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
