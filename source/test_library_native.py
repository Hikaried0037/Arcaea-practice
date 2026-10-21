"""Execute newly compiled/linked ARM64 ZIP, Foundation bridge and transaction code.
Foundation/filesystem/UIKit/zlib and SHA for charts larger than 4096 bytes are host substitutes; compiled SHA is checked separately. No real iOS UI execution.
"""
from pathlib import Path
import sys,json,struct,zipfile,io,hashlib,subprocess,os
from test_import_archive import Import
from unicorn.arm64_const import *
from PIL import Image
ROOT=Path(__file__).resolve().parent
class Native(Import):
 def __init__(self):
  super().__init__((ROOT/'binaries/ArcaeaPractice.dylib').read_bytes());self.u.mem_map(0x40000000,0x10000000);self.base=0x60000000;self.meta=json.loads((ROOT/'ArcLibrary.link.json').read_text());self.u.mem_map(self.base,0x100000);self.u.mem_write(self.base,(ROOT/'ArcLibrary.dylib').read_bytes());self.sym=self.meta['symbols'];self.extern={self.base+a:n for n,a in self.meta['calls'].items()};self.canvas=(256,256);self.nsdirs={5:'/Library',9:'/Documents'}
  for bg in ['base_light','base_conflict','nihil']:self.fs['/app/img/bg/1080/'+bg+'.jpg']=b'host built-in fixture'
  for a in self.meta['rebases']:self.u.mem_write(self.base+a,struct.pack('<Q',struct.unpack('<Q',self.u.mem_read(self.base+a,8))[0]+self.base))
  for name,value in [('_root','/import'),('_bundle','/app')]:self.setglobal(name,self.wrap(value))
 def setglobal(self,n,v):self.u.mem_write(self.base+self.sym[n],struct.pack('<Q',v))
 def call(self,name,*args):
  # Production work() resets per-operation failure before invoking these entries.
  if name in ['_prepare','_commit','_prepareCover','_repairBackgrounds']:self.setglobal('_failure',0)
  for i,a in enumerate(args):self.u.reg_write(UC_ARM64_REG_X0+i,a)
  self.u.reg_write(UC_ARM64_REG_LR,self.stop);self.u.emu_start(self.base+self.sym[name],self.stop+4,count=120000000);assert self.u.reg_read(UC_ARM64_REG_PC)==self.stop,(name,'instruction limit');return self.x(0)
 def objc(self):
  target=self.x(0);name=self.cstring(self.x(1));ob=self.objects.get(target,{});k=ob.get('kind');v=lambda i:self.value(self.x(i))
  if name=='allKeys':self.ret(self.wrap(list(ob['values'])));return
  if name=='dataWithBytes:length:':self.ret(self.wrap(bytes(self.u.mem_read(self.x(2),self.x(3)))));return
  if name=='numberWithUnsignedLongLong:':self.ret(self.wrap(self.x(2)));return
  if name=='containsObject:' and k=='Array':self.ret(int(v(2) in self.value(target)));return
  if name=='containsString:':self.ret(int(v(2) in self.value(target)));return
  if name=='stringByDeletingPathExtension':self.ret(self.wrap(self.value(target).rsplit('.',1)[0]));return
  if name=='isEqual:':self.ret(int(self.value(target)==v(2)));return
  if name=='set':self.ret(self.obj('Set',items=set()));return
  if name=='containsObject:':self.ret(int(v(2) in ob['items']));return
  if name=='addObject:' and k=='Set':ob['items'].add(v(2));self.ret();return
  if name=='unsignedLongLongValue':self.ret(ob.get('value',0));return
  if name=='CGImage':self.ret(target);return
  if name=='drawInRect:':self.ret();return
  if name=='initWithData:encoding:':
   encoding={4:'utf-8-sig',10:'utf-16',0x90000100:'utf-16-be'}.get(self.x(3),'utf-8')
   try:self.ret(self.wrap(v(2).decode(encoding)))
   except UnicodeError:self.ret(0)
   return
  super().objc()
 def hook(self,u,pc,size,user):
  if pc==self.base+self.sym.get('_al_sha256',-1) and self.x(1)>4096:
   self.u.mem_write(self.x(2),hashlib.sha256(bytes(self.u.mem_read(self.x(0),self.x(1)))).hexdigest().encode()+b'\0');self.ret();return
  n=getattr(self,'extern',{}).get(pc)
  if n:
   alias={'_objc_getClass':0x200fc,'_sel_registerName':0x20150,'_objc_msgSend':0x20108,'_objc_autoreleasePoolPush':0x200f0,'_objc_autoreleasePoolPop':0x200e4,'_memcpy':0x200a8,'_strcmp':0x20168,'_strlen':0x20174,'_malloc':0x20090,'_free':0x20060,'_inflate':0x2006c,'_inflateEnd':0x20078,'_inflateInit2_':0x20084,'_zlibVersion':0x20198,'_crc32':0x1fff4}
   if n=='_memset':u.mem_write(self.x(0),bytes([self.x(1)&255])*self.x(2));self.ret(self.x(0));return
   if n in alias:super().hook(u,self.slide+alias[n],size,user);return
   if n=='_snprintf':
    fmt=self.cstring(self.x(2));sp=u.reg_read(UC_ARM64_REG_SP);arg=struct.unpack('<Q',u.mem_read(sp,8))[0];value=self.cstring(arg) if '%s' in fmt else arg;out=(fmt%value).encode();u.mem_write(self.x(0),out[:self.x(1)-1]+b'\0');self.ret(len(out));return
   if n in ['_CGImageGetWidth','_CGImageGetHeight']:self.ret(self.objects[self.x(0)]['width' if n.endswith('Width') else 'height']);return
   if n=='_UIGraphicsBeginImageContextWithOptions':self.canvas=tuple(int(struct.unpack('<d',struct.pack('<Q',u.reg_read(UC_ARM64_REG_D0+i)))[0]) for i in range(2));self.ret();return
   if n=='_UIGraphicsGetImageFromCurrentImageContext':self.ret(self.obj('UIImage',width=self.canvas[0],height=self.canvas[1]));return
   if n=='_UIGraphicsEndImageContext':self.ret();return
   if n in ['_UIImageJPEGRepresentation','_UIImagePNGRepresentation']:
    ob=self.objects[self.x(0)];out=io.BytesIO();Image.new('RGB',(ob['width'],ob['height'])).save(out,'JPEG' if 'JPEG' in n else 'PNG');self.ret(self.wrap(out.getvalue()));return
   raise AssertionError(('external',n))
  super().hook(u,pc,size,user)
def main():
 raw=Path(sys.argv[1]).read_bytes();checks=[]
 def scan(data):
  m=Native();p=m.alloc(data);out=m.alloc(128*276);count=m.alloc(4);result=m.call('_al_zip_scan',p,len(data),out,count);return m,result,out,struct.unpack('<I',m.u.mem_read(count,4))[0]
 m,status,entries,count=scan(raw);assert status==0 and count==5;checks.append('compiled_native_zip_scan_original_sample')
 for label,data in [('truncated',raw[:100]),('not_zip',b'x'*100)]:assert scan(data)[1]!=0;checks.append(label+'_rejected')
 def pack(names):
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as z:
   for n,d in names:z.writestr(n,d)
  return out.getvalue()
 for label,names in [('traversal',[('../escape',b'x')]),('absolute',[('/escape',b'x')]),('duplicate',[('a/A.aff',b'x'),('b/a.aff',b'y')]),('too_many',[(str(i),b'') for i in range(129)])]:assert scan(pack(names))[1]!=0;checks.append(label+'_rejected')
 for label,aff,ok in [('valid',b'AudioOffset:26\n-\ntiming(0,179,4);\n(1000,1);',True),('comments',b'//header\nAudioOffset:-26\n-\n// body\ntiming(0,179,4);',True),('no_separator',b'AudioOffset:0\ntiming(0,120,4);',False),('unbalanced',b'AudioOffset:0\n-\ntiming(0,120,4);\nhold(0,10,1;',False),('commented_timing',b'AudioOffset:0\n-\n//timing(0,120,4);',False),('offset_overflow',b'AudioOffset:2147483648\n-\ntiming(0,120,4);',False)]:
  q=Native();assert (q.call('_al_aff_validate',q.alloc(aff),len(aff))==0)==ok;checks.append('compiled_aff_'+label)
 m=Native();result=m.call('_prepare',m.wrap(raw));assert result, m.cstring(struct.unpack('<Q',m.u.mem_read(m.base+m.sym['_failure'],8))[0]);prepared=m.value(result);assert prepared['chartClasses']==[3];assert json.loads(prepared['metadataRaw'])['id']=='seishunnohacking';checks.append('new_compiled_importer_original_sample_prepare')
 for file,dimensions in [('1080_base.jpg',(1080,1080)),('1080_base_256.jpg',(256,256))]:
  path=next(p for p in m.fs if '/staging/' in p and p.endswith('/'+file));assert Image.open(io.BytesIO(m.fs[path])).size==dimensions;checks.append(file+'_native_render_request')
 # Execute a new master/runtime transaction and test complete-generation activation.
 identifier=prepared['id'];prepared['backgrounds']=['base_light','base_conflict','nihil']
 js="const {Catalog}=require('./catalog.js');const fs=require('fs');const p=JSON.parse(fs.readFileSync(0,'utf8'));const c=new Catalog({songs:{songs:[]},packs:{packs:[Catalog.newPack('base','Arcaea','arcaea')]}});c.importSong(p);process.stdout.write(JSON.stringify({master:c.data,runtime:c.runtime()}));"
 result=json.loads(subprocess.run([os.environ.get('NODE_BINARY','node'),'-e',js],input=json.dumps(prepared),capture_output=True,text=True,encoding='utf-8',cwd=ROOT,check=True).stdout)
 master=result['master'];song=master['songs']['songs'][0];runtime=result['runtime']
 assert song['set']=='base' and song['title_localized']['en']=='SEISHUN://NO_HACKING' and song['artist']=='takehirotei' and song['bg']=='nihil'
 assert song['difficulties']==[dict(ratingClass=3,chartDesigner='SEISHUN://NO_HACKER',jacketDesigner='',rating=12,ratingPlus=False,world_unlock=False,hidden_until='')]
 checks.append('actual_sample_metadata_through_production_JS_preserves_credits_bg_and_only_actual_BYD')
 m.fs['/app/songs/songlist']=b'{"songs":[]}';m.fs['/app/songs/packlist']=b'{"packs":[{"id":"base","section":"arcaea"}]}';m.fs['/app/songs/unlocks']=b'{}'
 op={k:json.dumps(v,indent=4)+'\n' for k,v in [('masterText',master),('songText',runtime['songs']),('packText',runtime['packs'])]};op['stage']=identifier
 assert m.call('_commit',m.wrap(op))==1;active=json.loads(m.fs['/import/active.json']);d='/import/catalog/'+active['catalog'];assert json.loads(m.fs[d+'/ArcLibrary.json'])==master;assert json.loads(m.fs[d+'/songs/songlist'])==master['songs'];assert '/import/library/songs/'+identifier+'/3.aff' in m.fs;checks.append('compiled_atomic_generation_and_staged_resources_commit')
 with zipfile.ZipFile(io.BytesIO(raw)) as sample:
  destination='/import/library/songs/'+identifier+'/'
  assert m.fs[destination+'base.ogg']==sample.read('base.ogg')
  original=sample.read('3.aff').decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n').encode()
  assert m.fs[destination+'3.aff']==original
  assert not any(destination+str(c)+'.aff' in m.fs for c in [0,1,2,4])
 checks.append('actual_sample_committed_music_bit_identical_AFF_normalized_no_fake_difficulties')
 # Execute the retained host's real active-generation reader, rather than
 # assuming a successful manager commit makes the native catalog visible.
 from patch_ios import repair
 fixed,_,_=repair((ROOT/'binaries/ArcaeaPractice.dylib').read_bytes(),(ROOT/'diagnostics.o').read_bytes())
 m.u.mem_write(m.slide,fixed);m.sym['_hostLoadPointer']=m.slide+0xc348-m.base
 m.call('_hostLoadPointer')
 host_pointer=struct.unpack('<Q',m.u.mem_read(m.slide+0x32f40,8))[0]
 assert m.value(host_pointer)==d
 checks.append('retained_host_ARM64_loadPointer_accepts_new_songlist_packlist_generation')
 assert m.value(m.call('_loadMaster'))==master;checks.append('compiled_cold_catalog_read_uses_active_master')
 assert '/import/ArcLibrary-undo.json' in m.fs;checks.append('previous_master_saved_for_undo')
 saved_active=m.fs['/import/active.json']
 assert not m.call('_prepare',m.wrap(raw));assert m.fs['/import/active.json']==saved_active
 checks.append('compiled_importer_rejects_same_sample_twice_before_activation')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:files={n:z.read(n) for n in z.namelist()}
 meta=json.loads(files['songlist.json']);meta['id']='renamed_metadata';meta['title_localized']={'en':'renamed'};files['songlist.json']=json.dumps(meta).encode()
 files['3.aff']=original.decode().replace('\n','\r\n').encode('utf-16')
 assert not m.call('_prepare',m.wrap(pack(list(files.items()))));assert m.fs['/import/active.json']==saved_active
 checks.append('compiled_importer_rejects_repacked_renamed_metadata_UTF16_CRLF_identical_chart')
 files['3.aff']=original+b'\n(1000000,1);\n'
 distinct=m.call('_prepare',m.wrap(pack(list(files.items()))));assert distinct
 checks.append('compiled_importer_accepts_distinct_AFF_content')
 # Concurrent active-catalog change after prepare must be checked again at commit.
 m.fs[destination+'3.aff']=files['3.aff']
 raced=dict(op);raced['stage']=m.value(distinct)['id']
 assert not m.call('_commit',m.wrap(raced));assert m.fs['/import/active.json']==saved_active
 checks.append('compiled_commit_rechecks_actual_active_AFF_before_writing_generation')
 m.fs[destination+'3.aff']=original
 
 previous=m.fs['/import/active.json'];bad=dict(op);bad['stage']='wrong';assert m.call('_commit',m.wrap(bad))==0 and m.fs['/import/active.json']==previous;checks.append('invalid_stage_does_not_activate_partial_generation')
 m=Native();m.setglobal('_pickPack',m.wrap('base'))
 with zipfile.ZipFile(io.BytesIO(raw)) as z:cover=m.wrap(z.read('base.jpg'))
 result=m.value(m.call('_prepareCover',cover));name=result['filename'];assert result['pack']=='base'
 for filename in [name,'1080_'+name]:assert Image.open(io.BytesIO(m.fs['/import/library/songs/pack/'+filename])).size==(403,717)
 checks.append('compiled_pack_cover_crops_and_writes_both_native_resolution_names')
 m=Native();m.u.mem_write(m.base+m.sym['_arc_library_reload_request'],struct.pack('<I',1));assert m.call('_arc_library_take_reload')==1 and m.call('_arc_library_take_reload')==0;checks.append('atomic_engine_reload_consumes_request_once')
 report=dict(passed=True,checks=len(checks),cases=checks,scope=__doc__,library_sha256=hashlib.sha256((ROOT/'ArcLibrary.dylib').read_bytes()).hexdigest(),sample_sha256=hashlib.sha256(raw).hexdigest());(ROOT/'library-native-regression.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
