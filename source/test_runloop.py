"""ARM64 UI initializer regression using explicit synthetic runtime contracts.
The CoreFoundation common-mode sentinel uses pointer identity, not just equal
text; see Apple CFRunLoop.c CFRunLoopAddTimer/CFRunLoopAddSource. This is not UIKit.
"""
from pathlib import Path
import json,struct
from test_windows import Model,ROOT
from patch_ios import repair
from unicorn.arm64_const import *
class Runtime(Model):
 def __init__(self,plugin,slide,missing=None):
  super().__init__(plugin,slide);self.missing=missing;self.timer=None;self.registration=None;self.native_api=[];self.button_factories=0;self.label_factories=0;self.pause_at_buttons=False
  self.mainloop=self.obj('RunLoop');self.canonical=self.string('kCFRunLoopCommonModes');self.u.mem_write(0x20000080,struct.pack('<Q',self.canonical));self.u.mem_write(slide+0x93f08,struct.pack('<Q',0x20000080))
  # Rebase only the constant action-name array read by the real UI initializer.
  for off in range(0x8be40,0x8be40+0xc8,8):
   p=struct.unpack('<Q',self.u.mem_read(slide+off,8))[0]
   if p:self.u.mem_write(slide+off,struct.pack('<Q',p+slide))
 def hook(self,u,pc,size,user):
  a=pc-self.slide
  if self.pause_at_buttons and a==0x2b80:u.emu_stop();return
  if a==0x1ffc4:self.native_api.append('class_addMethod');self.ret(1);return
  if a==0x200d8:
   name=self.cstring(self.x(1));c=self.obj('Class',name=name);self.classes[name]=c;self.ret(c);return
  if a==0x20114:self.ret();return
  if a==0x3e3c:
   self.button_factories+=1;self.ret(self.obj('UIButton'));return
  if a==0x3c58:
   self.label_factories+=1;self.ret(self.obj('UILabel'));return
  if a==0x20108:
   target=self.x(0);sel=self.cstring(self.x(1));ob=self.objects.get(target,{})
   if sel=='alloc':self.ret(self.obj(ob['name'],subviews=[]));return
   if sel=='init':self.ret(target);return
   if sel=='mainRunLoop':self.ret(0 if self.missing=='runloop' else self.mainloop);return
   if sel=='displayLinkWithTarget:selector:':
    self.timer=self.obj('DisplayLink',target=self.x(2),selector=self.x(3));self.ret(0 if self.missing=='displaylink' else self.timer);return
   if sel=='setPreferredFramesPerSecond:':
    if target:ob['fps']=self.x(2)
    self.ret();return
   if sel=='addToRunLoop:forMode:':
    mode=self.x(3);text=self.cstring(self.objects[mode]['string']);self.registration={'mode':text,'system_sentinel':mode==self.canonical,'runloop':bool(self.x(2)),'displaylink':bool(target),'fires':bool(target and self.x(2) and (mode==self.canonical or text in ['kCFRunLoopDefaultMode','UITrackingRunLoopMode']))};self.ret();return
   if sel=='addSubview:':
    self.objects[target].setdefault('subviews',[]).append(self.x(2));self.objects[self.x(2)]['window']=target;self.ret();return
   if sel=='setHidden:':self.objects[target]['hidden']=self.x(2);self.ret();return
   if sel=='colorWithRed:green:blue:alpha:':self.ret(self.obj('UIColor'));return
   if sel in ['setTextColor:','setBackgroundColor:','setTextAlignment:','setNumberOfLines:','setUserInteractionEnabled:']:self.ret();return
  super().hook(u,pc,size,user)
 def invoke(self,address,arg=0,stop=None):
  u=self.u;u.reg_write(UC_ARM64_REG_X0,arg);u.reg_write(UC_ARM64_REG_LR,self.stop);u.emu_start(self.slide+address,self.stop+4,count=500000);assert u.reg_read(UC_ARM64_REG_PC)==(self.slide+stop if stop else self.stop)
def main():
 original=(ROOT/'binaries/ArcaeaPractice.dylib').read_bytes();fixed,_,symbols=repair(original,(ROOT/'diagnostics.o').read_bytes());cases=[]
 for slide in [0x1000000,0x123000000,0x700000000]:
  for name,plugin in [('original',original),('fixed',fixed)]:
   m=Runtime(plugin,slide);m.window(root=False,key=True);m.invoke(0x1228);assert m.registration['mode']=='kCFRunLoopCommonModes'
   assert m.registration['fires']==(name=='fixed')
   if name=='fixed':
    assert m.registration['system_sentinel'];assert 'system common-modes constant' in m.files['/sandbox/Documents/ArcPrac-ui.txt']
    m.pause_at_buttons=True;m.invoke(0x2970,stop=0x2b80);assert m.button_factories==2 and m.label_factories==0;assert 'window found' in m.files['/sandbox/Documents/ArcPrac-window.txt']
   cases.append({'test':'real_UI_initializer_and_mode_contract','slide':hex(slide),'build':name,'registration':m.registration,'practice_and_import_factory_calls':m.button_factories})
  for missing in ['runloop','displaylink']:
   m=Runtime(fixed,slide,missing);m.invoke(0x1228);assert not m.registration['fires'];assert ('NSRunLoop is nil' if missing=='runloop' else 'CADisplayLink is nil') in m.files['/sandbox/Documents/ArcPrac-ui.txt'];cases.append({'test':'registration_failure_diagnostic','slide':hex(slide),'missing':missing,'passed':True})
  # Disabled FPS override constructor returns without installing global hooks.
  m=Runtime(fixed,slide);m.invoke(0x1731c);assert not m.native_api and not m.registration;cases.append({'test':'no_global_FPS_override','slide':hex(slide),'passed':True})
 report={'passed':True,'checks':len(cases),'scope':'Real ARM64 UI initialization/tick callers with synthetic Objective-C/runtime methods; button factories are mocked. CoreFoundation sentinel registration semantics explicitly modeled. Not an iOS or UIKit test.','primary_reference':'https://github.com/opensource-apple/CF/blob/master/CFRunLoop.c','cases':cases};(ROOT/'runloop-regression.json').write_text(json.dumps(report,indent=2)+'\n');print('UI/run-loop regression PASS',len(cases))
if __name__=='__main__':main()
