"""Execute original/patched ARM64 window selection against a synthetic UIKit model.
This does not run UIKit, dyld, signing, or gameplay on an iOS device.
"""
from pathlib import Path
import json,struct,sys
from unicorn import Uc,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import *
ROOT=Path(__file__).resolve().parent
ORIGINAL=ROOT/'binaries/ArcaeaPractice.dylib'
def patched(data):
 b=bytearray(data)
 # The game uses a valid UIWindow with direct Cocos subviews and no root VC.
 # Continue to existing bounds checks without requiring a root controller.
 assert b[0x19184:0x19188].hex()=='60000090'
 b[0x19184:0x19188]=struct.pack('<I',0x14000000+((0x191a0-0x19184)//4))
 # Search the window's subviews, rather than rootViewController.view.
 assert b[0x1933c:0x19344].hex()=='f40300aa600000d0'
 b[0x1933c:0x19340]=struct.pack('<I',0xaa1903e0) # mov x0,x25
 b[0x19340:0x19344]=struct.pack('<I',0x14000000+((0x19358-0x19340)//4))
 return bytes(b)
class Model:
 def __init__(self,data,slide=0):
  self.slide=slide;self.u=Uc(UC_ARCH_ARM64,UC_MODE_ARM);u=self.u;u.mem_map(slide,0xc0000);u.mem_write(slide,data);u.mem_map(0x20000000,0x200000);u.reg_write(UC_ARM64_REG_SP,0x201f0000);self.objects={};self.next=0x20010000;self.calls=[];self.classes={};self.stop=slide+0xbff00
  u.mem_write(slide+0x92948,struct.pack('<Q',0x20000000));u.mem_write(0x20000000,struct.pack('<Q',0x12345678))
  # These are pointer globals, not addresses. They start nil, avoiding any rebase.
  self.app=self.obj('UIApplication');self.scenes=[];self.windows=[];self.files={};self.writes=0;self.native_result=None;self.nil_stop=False;self.prefs={};self.pref_writes=0;self.observers=[]
  u.hook_add(UC_HOOK_CODE,self.hook)
 def obj(self,kind,**props):
  p=self.next;self.next+=0x100;self.objects[p]=dict(kind=kind,**props);return p
 def array(self,items):return self.obj('Array',items=list(items))
 def string(self,value):
  p=self.next;self.next+=0x100;self.u.mem_write(p,value.encode()+b'\0');return self.obj('String',string=p)
 def cstring(self,p):
  if not p:return ''
  out=bytearray()
  while (b:=bytes(self.u.mem_read(p+len(out),1)))!=b'\0':
   out+=b
   if len(out)>4096:raise ValueError('unterminated selector')
  return out.decode('utf-8')
 def x(self,n):return self.u.reg_read(UC_ARM64_REG_X0+n)
 def ret(self,x=0,d=None):
  u=self.u;u.reg_write(UC_ARM64_REG_X0,x)
  if d is not None:
   for i,v in enumerate(d):u.reg_write(UC_ARM64_REG_D0+i,struct.unpack('<Q',struct.pack('<d',v))[0])
  u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))
 def hook(self,u,pc,size,user):
  a=pc-self.slide
  if pc==self.stop:u.emu_stop();return
  if a==0x528c and self.native_result is not None:self.ret(self.native_result);return
  if a==0x2f2c and self.nil_stop:u.emu_stop();return
  if a==0x200f0:self.ret(0x20001000);return
  if a==0x200e4:self.ret();return
  if a==0x20150:self.ret(self.x(0));return # sel_registerName returns a stable string
  if a==0x200fc:
   name=self.cstring(self.x(0));self.ret(self.classes.setdefault(name,self.obj('Class',name=name)));return
  if a==0x20108:
   target=self.x(0);sel=self.cstring(self.x(1));self.calls.append(sel)
   if not target:self.ret(0,(0.,0.,0.,0.));return
   ob=self.objects[target];k=ob['kind']
   if sel in ('retain','autorelease'):self.ret(target);return
   if sel=='release':self.ret();return
   if sel=='standardUserDefaults':self.ret(self.obj('NSUserDefaults'));return
   if sel=='objectForKey:':
    key=self.cstring(self.objects[self.x(2)]['string']);v=self.prefs.get(key);self.ret(self.obj('Number',value=v) if v is not None else 0);return
   if sel=='integerValue':self.ret(ob['value']);return
   if sel=='setInteger:forKey:':
    self.prefs[self.cstring(self.objects[self.x(3)]['string'])]=self.x(2);self.pref_writes+=1;self.ret();return
   if sel=='defaultCenter':self.ret(self.obj('NSNotificationCenter'));return
   if sel=='addObserver:selector:name:object:':
    self.observers.append((self.x(2),self.cstring(self.x(3)),self.cstring(self.objects[self.x(4)]['string'])));self.ret();return
   if sel in ['removeFromSuperview','endEditing:']:ob['detached']=True;self.ret();return
   if sel=='setHidden:':ob['hidden']=self.x(2);self.ret();return
   if sel=='sharedApplication':self.ret(self.app);return
   if sel=='respondsToSelector:':self.ret(1);return
   if sel=='connectedScenes':self.ret(self.array(self.scenes));return
   if sel=='allObjects':self.ret(target);return
   if sel=='windows':self.ret(self.array(ob.get('windows',self.windows)));return
   if sel=='count':self.ret(len(ob['items']));return
   if sel=='objectAtIndex:':self.ret(ob['items'][self.x(2)]);return
   if sel=='activationState':self.ret(ob.get('state',0));return
   if sel=='isHidden':self.ret(ob.get('hidden',0));return
   if sel=='alpha':self.ret(d=(ob.get('alpha',1.),));return
   if sel=='windowLevel':self.ret(d=(ob.get('level',0.),));return
   if sel=='bounds':self.ret(d=(0.,0.,ob.get('width',1024.),ob.get('height',768.)));return
   if sel=='rootViewController':self.ret(ob.get('controller',0));return
   if sel=='view':self.ret(ob.get('view',0));return
   if sel=='windowScene':self.ret(ob.get('scene',0));return
   if sel=='window':self.ret(ob.get('window',0));return
   if sel=='subviews':self.ret(self.array(ob.get('subviews',[])));return
   if sel=='layer':self.ret(ob.get('layer',0));return
   if sel=='name':self.ret(ob.get('name',0));return
   if sel=='UTF8String':self.ret(ob['string']);return
   if sel=='isKeyWindow':self.ret(ob.get('key',0));return
   if sel=='class':self.ret(self.classes.setdefault(k,self.obj('Class',name=k)));return
   if sel=='description':self.ret(self.string(ob.get('name',k)));return
   if sel=='defaultManager':self.ret(self.obj('NSFileManager'));return
   if sel=='URLsForDirectory:inDomains:':
    assert self.x(2)==9 and self.x(3)==1
    self.ret(self.array([self.obj('URL',path='/sandbox/Documents')]));return
   if sel=='path':self.ret(self.string(ob['path']));return
   if sel=='stringWithUTF8String:':self.ret(self.string(self.cstring(self.x(2))));return
   if sel=='stringByAppendingPathComponent:':self.ret(self.string(self.cstring(ob['string'])+'/'+self.cstring(self.objects[self.x(2)]['string'])));return
   if sel=='writeToFile:atomically:encoding:error:':
    assert self.x(3)==1 and self.x(4)==4 and self.x(5)==0
    self.files[self.cstring(self.objects[self.x(2)]['string'])]=self.cstring(ob['string']);self.writes+=1;self.ret(1);return
   raise AssertionError((k,sel))
 def run(self,address,arg=0):
  u=self.u;u.reg_write(UC_ARM64_REG_X0,arg);u.reg_write(UC_ARM64_REG_LR,self.stop);u.emu_start(self.slide+address,self.stop+4,count=250000)
  assert u.reg_read(UC_ARM64_REG_PC) in (self.stop,self.slide+0x2f2c) if self.nil_stop else u.reg_read(UC_ARM64_REG_PC)==self.stop,'execution did not return'
  return self.x(0)
 def window(self,root=True,state=0,**kw):
  scene=self.obj('Scene',state=state,windows=[]);view=self.obj('CCEAGLView',subviews=[]);controller=self.obj('Controller',view=view) if root else 0
  window=self.obj('Window',controller=controller,subviews=[view],scene=scene,**kw);self.objects[view]['window']=window;self.objects[scene]['windows']=[window];self.scenes.append(scene);self.windows.append(window);return window
def main():
 from patch_ios import repair
 original=ORIGINAL.read_bytes();fixed,_,symbols=repair(original,(ROOT/'diagnostics.o').read_bytes());results=[]
 for slide in [0x1000000,0x123000000,0x700000000]:
  for hasroot in [False,True]:
   for props,expected in [({},True),({'hidden':1},False),({'alpha':0.0},False),({'level':1.0},False),({'width':32.},False),({'height':32.},False)]:
    for label,data in [('original',original),('fixed',fixed)]:
     model=Model(data,slide);w=model.window(root=hasroot,**props);actual=bool(model.run(0x190fc,w));want=expected and (hasroot or label=='fixed');assert actual==want,(label,hasroot,props,actual,want);results.append({'test':'normal_window','slide':hex(slide),'root_controller':hasroot,'properties':props,'build':label,'accepted':actual})
   for label,data in [('original',original),('fixed',fixed)]:
    model=Model(data,slide);w=model.window(root=hasroot,key=1);actual=model.run(0x18ccc);want=w if hasroot or label=='fixed' else 0;assert actual==want,(label,hasroot,hex(actual),hex(want))
    if label=='fixed':
     assert 'subviews' in model.calls,'window tree not inspected'
     # Cached window should avoid a repeated tree scan.
     model.calls.clear();assert model.run(0x18ccc)==w;assert 'subviews' not in model.calls
    results.append({'test':'game_window_selection_and_cache','slide':hex(slide),'root_controller':hasroot,'build':label,'found':bool(actual)})
  for native in [0,1]:
   model=Model(fixed,slide);model.native_result=native;model.run(symbols['_bootstrap']);boot=model.files['/sandbox/Documents/ArcPrac-startup.txt'];assert ('success' if native else 'failure') in boot
   model.nil_stop=True;model.run(symbols['_tick_probe'],0);assert 'no eligible' in model.files['/sandbox/Documents/ArcPrac-window.txt'];assert model.u.reg_read(UC_ARM64_REG_PC)==slide+0x2f2c
   w=model.window(root=False);assert model.run(symbols['_tick_probe'],w)==w;assert 'window found' in model.files['/sandbox/Documents/ArcPrac-window.txt'];count=model.writes
   assert model.run(symbols['_tick_probe'],w)==w;assert model.writes==count,'repeated per-frame file write'
   # Callee-saved registers and stack are preserved by diagnostic code.
   for r in [UC_ARM64_REG_X19,UC_ARM64_REG_X20,UC_ARM64_REG_X21,UC_ARM64_REG_X22,UC_ARM64_REG_X23,UC_ARM64_REG_X24]:model.u.reg_write(r,0x55aa55aa)
   sp=model.u.reg_read(UC_ARM64_REG_SP);model.run(symbols['_tick_probe'],w);assert model.u.reg_read(UC_ARM64_REG_SP)==sp
   for r in [UC_ARM64_REG_X19,UC_ARM64_REG_X20,UC_ARM64_REG_X21,UC_ARM64_REG_X22,UC_ARM64_REG_X23,UC_ARM64_REG_X24]:assert model.u.reg_read(r)==0x55aa55aa
   results.append({'test':'bootstrap_and_tick_diagnostics_no_repeat_and_ABI','slide':hex(slide),'native_init_result':native,'passed':True})
 report={'passed':True,'checks':len(results),'method':'Original and final patched ARM64 instructions executed with Unicorn and synthetic Objective-C/UIKit/Foundation responses, three ASLR slides','scope':'Window selection/cache and startup diagnostic control flow only; not an iOS runtime or full gameplay test','results':results};(ROOT/'window-regression.json').write_text(json.dumps(report,indent=2)+'\n');(ROOT/'binaries/ArcaeaPractice-windowfix.dylib').write_bytes(fixed);print('Window/diagnostics ARM64 regression PASS',len(results))
if __name__=='__main__':main()
