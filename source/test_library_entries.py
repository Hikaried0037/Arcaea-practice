"""Execute real ARM64 manager entry, UIKit message selectors and async callbacks.
UIKit/Foundation/GCD are strict host models, not a signed iPad execution.
"""
import json,struct,hashlib,io,zipfile
from pathlib import Path
from test_library_native import Native,ROOT
from unicorn.arm64_const import *
class Entries(Native):
 def __init__(self,old=False):
  super().__init__()
  if old:
   r=ROOT.parent/'r13';self.meta=json.loads((r/'ArcLibrary.link.json').read_text());self.sym=self.meta['symbols'];self.extern={self.base+a:n for n,a in self.meta['calls'].items()};self.u.mem_write(self.base,(r/'ArcLibrary.dylib').read_bytes())
   for a in self.meta['rebases']:self.u.mem_write(self.base+a,struct.pack('<Q',struct.unpack('<Q',self.u.mem_read(self.base+a,8))[0]+self.base))
  self.queue=[];self.events=[];self.results=[];self.unavailable=set();self.presentations=0
  self.game=self.obj('UIWindow',scene=self.obj('UIWindowScene'));self.objects[self.app]['state']=0;self.objects[self.app]['key']=self.game
  self.sender=self.obj('UIButton',window=self.game)
  self.setglobal('_root',self.wrap('/import'));self.setglobal('_bundle',self.wrap('/app'))
  self.fs['/app/songs/packlist']=b'{"packs":[{"id":"base","section":"arcaea"}]}'
 def g(self,n):return struct.unpack('<Q',self.u.mem_read(self.base+self.sym[n],8))[0]
 def integer(self,n):return struct.unpack('<I',self.u.mem_read(self.base+self.sym[n],4))[0]
 def objc(self):
  target=self.x(0);name=self.cstring(self.x(1));ob=self.objects.get(target,{});k=ob.get('kind');v=lambda i:self.value(self.x(i))
  self.events.append((k,name))
  if not target:self.ret(0,(0.,0.,0.,0.));return
  if name=='respondsToSelector:':self.ret(int(self.cstring(self.x(2)) not in self.unavailable));return
  if name=='sharedApplication':self.ret(self.app);return
  if name=='applicationState':self.ret(ob.get('state',0));return
  if name=='keyWindow':self.ret(ob.get('key',0));return
  if name=='windowScene':self.ret(ob.get('scene',0));return
  if name=='window':self.ret(ob.get('window',0));return
  if name=='bounds':self.ret(d=(0.,0.,1194.,834.));return
  if name=='initWithWindowScene:':ob['scene']=self.x(2);self.ret(target);return
  if name in ['setWindowLevel:','setAutoresizingMask:','setOpaque:','setHidden:','setModalPresentationStyle:','setAllowsMultipleSelection:']:
   ob[name]=self.x(2);self.ret();return
  if name=='view':
   if 'view' not in ob:ob['view']=self.obj('UIView')
   self.ret(ob['view']);return
  if name=='setRootViewController:':
   ob['controller']=self.x(2);co=self.objects[self.x(2)];co['view']=self.obj('UIView',window=target);self.ret();return
  if name=='userContentController':
   if 'content' not in ob:ob['content']=self.obj('WKUserContentController')
   self.ret(ob['content']);return
  if name=='addScriptMessageHandler:name:':ob['handler']=self.x(2);self.ret();return
  if name=='removeScriptMessageHandlerForName:':ob.pop('handler',None);self.ret();return
  if name=='initWithFrame:configuration:':ob['config']=self.x(3);self.ret(target);return
  if name=='configuration':self.ret(ob['config']);return
  if name=='addSubview:':self.objects[self.x(2)]['window']=ob.get('window',0);self.ret();return
  if name=='fileURLWithPath:':self.ret(self.obj('URL',path=v(2)));return
  if name=='loadFileURL:allowingReadAccessToURL:':self.ret();return
  if name in ['makeKeyAndVisible','makeKeyWindow']:self.ret();return
  if name=='body':self.ret(ob['body']);return
  if name=='presentedViewController':self.ret(ob.get('presented',0));return
  if name=='initWithDocumentTypes:inMode:':ob['types']=v(2);ob['mode']=self.x(3);self.ret(target);return
  if name=='setDelegate:':ob['delegate']=self.x(2);self.ret();return
  if name=='presentViewController:animated:completion:':
   assert k=='UIViewController' and self.x(3)==1 and self.x(4)==0
   assert not ob.get('presented');ob['presented']=self.x(2);self.presentations+=1;self.ret();return
  if name=='presentViewController:animated:completionHandler:':raise AssertionError('UIKit unrecognized selector: '+name)
  if name=='isKindOfClass:' and k=='URL' and self.objects[self.x(2)].get('name')=='NSURL':self.ret(1);return
  if name=='isFileURL':self.ret(int(ob.get('file',True)));return
  if name=='startAccessingSecurityScopedResource':ob['access']=ob.get('access',0)+1;self.ret(1);return
  if name=='stopAccessingSecurityScopedResource':ob['access']-=1;self.ret();return
  if name=='dataWithContentsOfURL:options:error:':self.ret(self.wrap(self.fs.get(self.objects[self.x(2)]['path'])));return
  if name=='evaluateJavaScript:completionHandler:':
   js=v(2);assert js.startswith('window.receive(') and js.endswith(');');self.results.append(json.loads(js[15:-2]));self.ret();return
  super().objc()
 def hook(self,u,pc,size,user):
  n=getattr(self,'extern',{}).get(pc)
  if n=='_dispatch_get_global_queue':self.ret(7);return
  if n=='_dispatch_async_f':self.queue.append((self.x(2),self.x(1)));self.ret();return
  if n=='_objc_allocateClassPair':self.ret(self.obj('Class',name=self.cstring(self.x(1))));return
  if n in ['_class_addMethod','_class_addProtocol']:self.ret(1);return
  if n=='_objc_getProtocol':self.ret(self.obj('Protocol'));return
  if n=='_objc_registerClassPair':self.ret();return
  super().hook(u,pc,size,user)
 def drain(self):
  for _ in range(20):
   if not self.queue:return
   address,ctx=self.queue.pop(0);self.sym['_callback']=address-self.base;self.call('_callback',ctx)
  raise AssertionError('runaway dispatch')
 def open(self):self.call('_arc_library_open',0,0,self.sender)
 def action(self,op):self.call('_received',0,0,0,self.obj('WKScriptMessage',body=self.wrap(op)))
 def dismiss(self):
  co=self.g('_controller')
  if co:self.objects[co]['presented']=0
 def cancel(self):
  p=self.g('_activePicker');self.dismiss();self.call('_pickerCancel',0,0,p);self.drain()

def main():
 checks=[]
 def ok(name):checks.append(name)
 if (ROOT.parent/'r13/ArcLibrary.dylib').exists() and (ROOT.parent/'r13/ArcLibrary.link.json').exists():
  old=Entries(True);old.open()
  try:old.action({'action':'pickZip'})
  except AssertionError as e:assert 'unrecognized selector' in str(e);ok('reproduces_r13_exact_device_crash_selector')
  else:raise AssertionError('old failure was not reproduced')
 else:print('SKIP historical r13 reproducer: old binary is not exported')
 m=Entries();m.open();assert m.g('_web') and m.g('_controller');ok('actual_arm64_open_constructs_window_webview_and_runtime_delegates')
 w=m.g('_window');m.open();assert m.g('_window')==w;ok('repeat_open_reuses_existing_window')
 m.action({'action':'refresh'});assert m.integer('_busy')==1;m.drain();assert m.results[-1]['type']=='catalog' and not m.integer('_busy');ok('refresh_worker_main_callback_route')
 for action,pack,mode in [('pickZip',None,1),('pickCover','base',2)]:
  m.action({'action':action,**({'pack':pack} if pack else {})});p=m.g('_activePicker');assert p and m.objects[p]['types']==['public.image' if mode==2 else 'public.data'];assert m.objects[p]['mode']==0
  assert m.objects[p]['delegate']==m.g('_bridge');ok(action+'_uses_valid_selector_delegate_and_import_copy_mode')
  presentations=m.presentations
  for op in [{'action':'pickZip'},{'action':'pickCover','pack':'base'},{'action':'refresh'},{'action':'undo'},{'action':'reload'},{'action':'close'}]:m.action(op)
  assert m.presentations==presentations and not m.queue and m.g('_window')==w and m.integer('_arc_library_reload_request')==0;ok(action+'_duplicate_actions_and_close_reload_guarded')
  m.cancel();assert not m.g('_activePicker') and m.results[-1]['type']=='cancel';ok(action+'_cancel_unlocks_without_importing')
  m.call('_pickerCancel',0,0,p);assert not m.queue;ok(action+'_stale_callback_ignored')
 m.action({'action':'pickZip'});p=m.g('_activePicker');m.dismiss();m.call('_picked',0,0,p,m.wrap([]));m.drain();assert m.results[-1]['type']=='cancel' and not m.g('_activePicker');ok('empty_selection_is_cancel_not_permanent_busy')
 m.action({'action':'pickZip'});p=m.g('_activePicker');m.dismiss();m.call('_picked',0,0,p,m.wrap(['bad-url']));m.drain();assert m.results[-1]['type']=='error';ok('invalid_document_result_is_error_not_objc_exception')
 for state in [1,2]:
  m.objects[m.app]['state']=state;n=m.presentations;m.action({'action':'pickZip'});m.drain();assert m.presentations==n and m.results[-1]['type']=='error';ok('inactive_'+str(state)+'_does_not_present')
 m.objects[m.app]['state']=0;m.action({'action':'pickCover','pack':123});m.drain();assert m.results[-1]['type']=='error';ok('nonstring_cover_id_does_not_send_UTF8String_to_number')
 m.unavailable.add('presentViewController:animated:completion:');m.action({'action':'pickZip'});m.drain();assert m.results[-1]['type']=='error';m.unavailable.clear();ok('unavailable_system_selector_reports_error')
 m.action({'action':'pickZip'});p=m.g('_activePicker');m.dismiss();url=m.obj('URL',path='/sample.zip');m.fs['/sample.zip']=b'not a zip';m.call('_picked',0,0,p,m.array([url]));assert m.integer('_busy')==1;m.drain();assert m.results[-1]['type']=='error' and m.objects[url]['access']==0 and not m.integer('_busy');ok('file_read_invalid_zip_error_and_security_scope_balanced')
 # Full callback -> ZIP -> AFF -> staged resources with a small valid fixture.
 image=io.BytesIO();from PIL import Image;Image.new('RGB',(32,32)).save(image,'PNG');fixture=io.BytesIO()
 with zipfile.ZipFile(fixture,'w',zipfile.ZIP_DEFLATED) as z:
  for name,data in [('0.aff',b'AudioOffset:0\n-\ntiming(0,120,4);\n(1000,1);'),('base.png',image.getvalue()),('base.ogg',b'OggS'+b'fixture'),('songlist.txt',b'{"title_localized":{"en":"Callback test"},"artist":"Artist"}')]:z.writestr(name,data)
 m.action({'action':'pickZip'});p=m.g('_activePicker');m.dismiss();m.fs['/sample.zip']=fixture.getvalue();m.call('_picked',0,0,p,m.array([url]));m.drain();assert m.results[-1]['type']=='prepared' and m.results[-1]['chartClasses']==[0] and m.objects[url]['access']==0;ok('full_document_callback_async_zip_aff_metadata_and_image_prepare')
 m.action({'action':'undo'});m.drain();assert m.results[-1]['type']=='error';ok('undo_without_history_returns_error')
 m.action({'action':'commit'});m.drain();assert m.results[-1]['type']=='error';ok('malformed_commit_does_not_modify_catalog')
 m.action({'action':'reload'});assert not m.g('_window') and m.call('_arc_library_take_reload')==1;ok('reload_closes_manager_and_sets_engine_request_once')
 assert any(n=='removeScriptMessageHandlerForName:' for k,n in m.events);ok('close_detaches_web_message_handler')
 m.action({'action':'pickZip'});assert not m.queue;ok('message_after_close_is_ignored')
 m.open();m.action({'action':'close'});assert not m.g('_window');ok('reopen_and_return_to_game')
 report=dict(passed=True,checks=len(checks),cases=checks,scope=__doc__,library_sha256=hashlib.sha256((ROOT/'ArcLibrary.dylib').read_bytes()).hexdigest())
 (ROOT/'library-entries-regression.json').write_text(json.dumps(report,indent=2)+'\n');print('Native entry regression PASS',len(checks))
if __name__=='__main__':main()
