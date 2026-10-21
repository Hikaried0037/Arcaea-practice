"""Actual ARM64 background prepare/commit and retained native fullPath resolver. Foundation/filesystem/UIKit rendering and C++ result construction are host models, not iOS execution."""
from pathlib import Path
import sys,io,json,zipfile,struct,subprocess,os,hashlib
from PIL import Image
from test_library_native import Native,ROOT
from patch_ios import repair
from unicorn.arm64_const import *
class Background(Native):
 def __init__(self):
  super().__init__();fixed,_,_=repair((ROOT/'binaries/ArcaeaPractice.dylib').read_bytes(),(ROOT/'diagnostics.o').read_bytes());self.u.mem_write(self.slide,fixed);self.mainbase=0x70000000;self.u.mem_map(self.mainbase,0x1000000);self.sym['_nativeFullPath']=self.slide+0xc9dc-self.base;self.resolved=None
  for offset,value in [(0x32ef0,self.wrap('/import/library')),(0x32ee8,self.mainbase),(0x32ef8,self.mainbase+0xfff000)]:self.u.mem_write(self.slide+offset,struct.pack('<Q',value))
 def objc(self):
  if self.cstring(self.x(1))=='writeToFile:options:error:' and getattr(self,'fail_write',None)==self.value(self.x(2)):self.ret(0);return
  super().objc()
 def hook(self,u,pc,size,ctx):
  if pc==getattr(self,'mainbase',-1)+0xebdb28:self.resolved=self.cstring(self.x(1));self.ret();return
  if pc==getattr(self,'mainbase',-1)+0xfff000:self.resolved='BUNDLE_FALLBACK';self.ret();return
  super().hook(u,pc,size,ctx)
 def resolve(self,name):
  raw=name.encode();p=self.alloc(24)
  if len(raw)<23:self.u.mem_write(p,raw+bytes(23-len(raw))+bytes([len(raw)]))
  else:self.u.mem_write(p,struct.pack('<QQQ',self.alloc(raw+b'\0'),len(raw),0x8000000000000100))
  self.u.reg_write(UC_ARM64_REG_X8,self.alloc(24));self.resolved=None;self.call('_nativeFullPath',0,p,0);return self.resolved

def jpeg(size=(64,32),fmt='JPEG'):
 b=io.BytesIO();Image.new('RGB',size,(12,56,78)).save(b,fmt);return b.getvalue()
def pack(files):
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
  for name,data in files.items():z.writestr(name,data)
 return b.getvalue()
def basic(bg='new_bg',ext='jpg',include=True):
 song=dict(id='fixture',title_localized={'en':'Fixture'},bg=bg,side=1,difficulties=[dict(ratingClass=3,rating=12,ratingPlus=True)])
 f={'songlist.json':json.dumps({'songs':[song]}).encode(),'3.aff':b'AudioOffset:0\n-\ntiming(0,120,4);\n(1000,1);','base.ogg':b'OggSfixture','1080_base.jpg':jpeg()}
 if include:f[bg+'.'+ext]=jpeg(fmt='PNG' if ext=='png' else 'JPEG')
 return f
checks=[]
def model(prepared):
 script="const {Catalog}=require('./catalog.js');const fs=require('fs');const p=JSON.parse(fs.readFileSync(0,'utf8'));const c=new Catalog({songs:{songs:[]},packs:{packs:[Catalog.newPack('base','Arcaea','arcaea')]}});c.importSong(p);process.stdout.write(JSON.stringify({master:c.data,runtime:c.runtime()}));"
 return json.loads(subprocess.run([os.environ.get('NODE_BINARY','node'),'-e',script],input=json.dumps(prepared),capture_output=True,text=True,encoding='utf-8',cwd=ROOT,check=True).stdout)
def operation(prepared):
 data=model(prepared);op={k:json.dumps(v,indent=4)+'\n' for k,v in [('masterText',data['master']),('songText',data['runtime']['songs']),('packText',data['runtime']['packs'])]};op['stage']=prepared['id'];return data,op
def commit(n,prepared):
 data,op=operation(prepared);assert n.call('_commit',n.wrap(op))==1,n.cstring(struct.unpack('<Q',n.u.mem_read(n.base+n.sym['_failure'],8))[0]);return data
def main():
 n=Background();prepared=n.value(n.call('_prepare',n.wrap(pack(basic()))));assert prepared['newBackgrounds']==['new_bg'] and 'new_bg' in prepared['backgrounds'];assert not any('/library/img/bg/' in p for p in n.fs);checks.append('new_background_prepared_without_writing_active_library')
 commit(n,prepared)
 for folder in ['img/bg/1080','img/bg']:
  p='/import/library/'+folder+'/new_bg.jpg';assert Image.open(io.BytesIO(n.fs[p])).size==(1920,1440);assert n.resolve(folder+'/new_bg.jpg')==p
 assert 'new_bg' in n.value(n.call('_backgrounds'));checks.append('committed_both_resolution_aliases_and_actual_native_fullPath_reads_them')
 assert n.resolve('img/bg/1080/missing.jpg')=='BUNDLE_FALLBACK';assert n.resolve('img/bg/../outside.jpg')=='BUNDLE_FALLBACK';assert n.resolve('img/bg_bad/new_bg.jpg')=='BUNDLE_FALLBACK';assert n.resolve('img')=='BUNDLE_FALLBACK';checks.append('native_resolver_missing_unsafe_unrelated_short_names_fall_back')
 # Existing songs route is preserved, including short C++ string storage.
 n.fs['/import/library/songs/a']=b'fixture';assert n.resolve('songs/a')=='/import/library/songs/a';checks.append('native_song_resource_route_preserved')
 for ext in ['png','jpeg']:
  q=Background();p=q.value(q.call('_prepare',q.wrap(pack(basic(ext=ext)))));assert p['newBackgrounds']==['new_bg'];checks.append(ext+'_converted_for_native_JPG_background_request')
 q=Background();q.fs['/app/img/bg/1080/new_bg.png']=b'existing bundled background';f=basic();f['new_bg.jpg']=b'invalid ignored custom replacement';p=q.value(q.call('_prepare',q.wrap(pack(f))));assert p['newBackgrounds']==[];commit(q,p);assert not any('/import/library/img/bg/' in key for key in q.fs);assert q.fs['/app/img/bg/1080/new_bg.png']==b'existing bundled background';checks.append('builtin_background_wins_without_overwrite_or_custom_validation')
 q=Background();q.fs['/import/library/img/bg/1080/new_bg.jpg']=jpeg();saved=q.fs['/import/library/img/bg/1080/new_bg.jpg'];p=q.value(q.call('_prepare',q.wrap(pack(basic(include=False)))));assert p['newBackgrounds']==[];commit(q,p);assert q.fs['/import/library/img/bg/1080/new_bg.jpg']==saved;checks.append('previously_imported_background_reused_without_archive_image')
 for label,files in [('missing',basic(include=False)),('corrupt',{**basic(),'new_bg.jpg':b'not image'}),('oversized',{**basic(),'new_bg.jpg':jpeg((8193,2))}),('unsafe',basic(bg='../escape'))]:
  q=Background();assert not q.call('_prepare',q.wrap(pack(files)));assert '/import/active.json' not in q.fs and not any('/import/library/img/bg/' in p for p in q.fs);checks.append(label+'_background_rejected_without_active_catalog_change')
 # Song inverse background and only the actual difficulty's overrides are installed.
 f=basic();metadata=json.loads(f['songlist.json']);s=metadata['songs'][0];s['bg_inverse']='inverse';s['difficulties'][0]['bg']='byd_override';s['difficulties'].append(dict(ratingClass=4,bg='unused_missing',rating=-1));f['inverse.png']=jpeg(fmt='PNG');f['byd_override.jpg']=jpeg();f['songlist.json']=json.dumps(metadata).encode();q=Background();p=q.value(q.call('_prepare',q.wrap(pack(f))));assert set(p['newBackgrounds'])=={'new_bg','inverse','byd_override'};commit(q,p);checks.append('song_inverse_and_actual_difficulty_backgrounds_included_inactive_placeholders_ignored')
 for failure in ['missing_staged','write_failure','generic_alias_failure']:
  q=Background();p=q.value(q.call('_prepare',q.wrap(pack(basic()))));data,op=operation(p)
  if failure=='missing_staged':q.fs={key:v for key,v in q.fs.items() if '/_backgrounds/' not in key}
  else:q.fail_write='/import/library/img/bg/'+('new_bg.jpg' if failure=='generic_alias_failure' else '1080/new_bg.jpg')
  assert not q.call('_commit',q.wrap(op));assert '/import/active.json' not in q.fs
  checks.append(failure+'_background_commit_keeps_previous_active_catalog')
  if failure!='missing_staged':
   q.fail_write=None;assert q.call('_commit',q.wrap(op))==1
   for relative in ['img/bg/new_bg.jpg','img/bg/1080/new_bg.jpg']:assert q.resolve(relative)=='/import/library/'+relative
   checks.append(failure+'_retry_writes_complete_background_aliases')
 if len(sys.argv)>1:
  raw=Path(sys.argv[1]).read_bytes();q=Background();p=q.value(q.call('_prepare',q.wrap(raw)));assert p and p['chartClasses']==[3] and p['newBackgrounds']==['roquira'];data=commit(q,p);s=data['master']['songs']['songs'][0];assert s['bg']=='roquira' and s['title_localized']['en']=='RoquiRa : Between Life and Death' and s['difficulties'][0]['rating']==12 and s['difficulties'][0]['ratingPlus'];assert q.resolve('img/bg/1080/roquira.jpg')=='/import/library/img/bg/1080/roquira.jpg';assert q.value(q.call('_loadMaster'))==data['master'];
  with zipfile.ZipFile(io.BytesIO(raw)) as original:assert q.fs['/import/library/img/bg/1080/roquira.jpg']==original.read('roquira.jpg')
  checks.append('supplied_archive_metadata_BYD12plus_background_commit_cold_read_native_resolution')
 report=dict(passed=True,checks=len(checks),cases=checks,library_sha256=hashlib.sha256((ROOT/'ArcLibrary.dylib').read_bytes()).hexdigest(),scope=__doc__)
 (ROOT/'background-regression.json').write_text(json.dumps(report,indent=2)+'\n');print('Native background regression PASS',len(checks))
if __name__=='__main__':main()
