"""Execute importArchive ARM64 with supplied ZIP bytes and in-memory Foundation.
zlib, filesystem, JSON and UIKit image decoding/rendering are host substitutes.
No device document picker, dyld, sandbox permissions or actual reload is tested.
"""
from pathlib import Path
import sys,io,json,struct,zlib,posixpath,zipfile,hashlib,re
from PIL import Image
from test_windows import Model,ROOT
from patch_ios import repair
from unicorn.arm64_const import *
class Import(Model):
 def __init__(self,b,slide=0x1000000):
  super().__init__(b,slide);self.u.mem_map(0x30000000,0x10000000);self.heap=0x30000000;self.fs={};self.logs=[];self.uuid=0;self.showing=[];self.rendered=0
  self.fs['/app/songs/songlist']=b'{"songs":[]}'
  self.fs['/app/songs/packlist']=b'{"packs":[]}'
  self.fs['/app/songs/pack/1080_select_base.png']=b'pack-image'
  self.fs['/app/songs/unlocks']=b'{}'
 def alloc(self,d):
  if isinstance(d,int):d=b'\0'*d
  p=self.heap;self.heap+=(len(d)+15)//16*16+16;self.u.mem_write(p,d);return p
 def cstring(self,p):
  if not p:return ''
  out=bytearray()
  while len(out)<8*1024*1024:
   data=bytes(self.u.mem_read(p+len(out),256));end=data.find(b'\0')
   if end>=0:return (out+data[:end]).decode('utf-8')
   out+=data
  raise ValueError('unterminated string')
 def string(self,v):return self.obj('String',string=self.alloc(v.encode()+b'\0'))
 def wrap(self,v):
  if v is None:return 0
  if isinstance(v,str):return self.string(v)
  if isinstance(v,bytes):return self.obj('NSData',data=v,ptr=self.alloc(v))
  if isinstance(v,dict):return self.obj('Dictionary',values={k:self.wrap(x) for k,x in v.items()})
  if isinstance(v,list):return self.array([self.wrap(x) for x in v])
  return self.obj('Number',value=v)
 def value(self,p):
  if not p:return None
  o=self.objects[p];k=o['kind']
  if k=='String':return self.cstring(o['string'])
  if k=='Dictionary':return {a:self.value(v) for a,v in o['values'].items()}
  if k=='Array':return [self.value(v) for v in o['items']]
  if k=='Number':return o['value']
  if k=='NSData':return o['data']
  return o
 def objc(self):
  x=self.x;target=x(0);sel=self.cstring(x(1));ob=self.objects.get(target,{});k=ob.get('kind');v=lambda n:self.value(x(n))
  if not target:self.ret(0,(0.,0.,0.,0.));return
  if sel in ['retain','autorelease','init']:self.ret(target);return
  if sel=='release':self.ret();return
  if sel=='alloc':self.ret(self.obj(ob['name']));return
  if sel=='isKindOfClass:':
   cls=self.objects.get(x(2),{}).get('name','InvalidClass');self.ret(int(k in {'NSMutableDictionary':['Dictionary'],'NSMutableArray':['Array'],'NSDictionary':['Dictionary'],'NSArray':['Array'],'NSString':['String'],'NSNumber':['Number'],'NSData':['NSData']}.get(cls,[])));return
  if sel=='stringWithUTF8String:':self.ret(self.wrap(self.cstring(x(2))));return
  if sel=='UTF8String':self.ret(ob['string']);return
  if sel=='initWithBytes:length:encoding:':self.ret(self.wrap(bytes(self.u.mem_read(x(2),x(3))).decode('utf-8')));return
  if sel=='initWithData:encoding:':self.ret(self.wrap(v(2).decode('utf-8-sig')));return
  if sel=='dataUsingEncoding:':self.ret(self.wrap(self.value(target).encode()));return
  if sel=='data':self.ret(self.wrap(b''));return
  if sel=='dictionary':self.ret(self.wrap({}));return
  if sel=='array':self.ret(self.wrap([]));return
  if sel=='objectForKey:':self.ret(ob['values'].get(v(2),0));return
  if sel=='setObject:forKey:':ob['values'][v(3)]=x(2);self.ret();return
  if sel=='addObject:':ob['items'].append(x(2));self.ret();return
  if sel=='addObjectsFromArray:':ob['items']+=self.objects[x(2)]['items'];self.ret();return
  if sel=='count':self.ret(len(ob.get('items',ob.get('values',{}))));return
  if sel=='objectAtIndex:':self.ret(ob['items'][x(2)]);return
  if sel=='mutableCopy':self.ret(self.wrap(self.value(target)));return
  if sel in ['numberWithLongLong:','numberWithBool:']:self.ret(self.wrap(x(2) if x(2)<2**63 else x(2)-2**64));return
  if sel=='numberWithDouble:':self.ret(self.wrap(struct.unpack('<d',struct.pack('<Q',self.u.reg_read(UC_ARM64_REG_D0)))[0]));return
  if sel in ['longLongValue','integerValue','boolValue']:self.ret(int(ob['value'])&0xffffffffffffffff);return
  if sel=='doubleValue':self.ret(d=(float(ob['value']),));return
  if sel in ['stringByAppendingPathComponent:','stringByAppendingString:']:
   self.ret(self.wrap((self.value(target).rstrip('/')+'/'+v(2)) if sel.endswith('Component:') else self.value(target)+v(2)));return
  if sel=='lastPathComponent':self.ret(self.wrap(posixpath.basename(self.value(target))));return
  if sel=='stringByDeletingLastPathComponent':self.ret(self.wrap(posixpath.dirname(self.value(target))));return
  if sel=='pathExtension':self.ret(self.wrap(posixpath.splitext(self.value(target))[1][1:]));return
  if sel=='lowercaseString':self.ret(self.wrap(self.value(target).lower()));return
  if sel in ['hasPrefix:','hasSuffix:']:self.ret(int(self.value(target).startswith(v(2)) if sel=='hasPrefix:' else self.value(target).endswith(v(2))));return
  if sel=='stringByReplacingOccurrencesOfString:withString:':self.ret(self.wrap(self.value(target).replace(v(2),v(3))));return
  if sel=='replaceCharactersInRange:withString:':
   text=self.value(target);text=text[:x(2)]+v(4)+text[x(2)+x(3):];ob['string']=self.alloc(text.encode()+b'\0');self.ret();return
  if sel=='componentsJoinedByString:':self.ret(self.wrap(v(2).join(self.value(target))));return
  if sel=='componentsSeparatedByString:':self.ret(self.wrap(self.value(target).split(v(2))));return
  if sel=='defaultManager':self.ret(self.obj('NSFileManager'));return
  if sel=='createDirectoryAtPath:withIntermediateDirectories:attributes:error:':self.ret(1);return
  if sel=='removeItemAtPath:error:':
   root=v(2);self.fs={p:d for p,d in self.fs.items() if p!=root and not p.startswith(root+'/')};self.ret(1);return
  if sel=='moveItemAtPath:toPath:error:':
   src,dst=v(2),v(3);pairs={dst+p[len(src):]:d for p,d in self.fs.items() if p==src or p.startswith(src+'/')};self.fs={p:d for p,d in self.fs.items() if not(p==src or p.startswith(src+'/'))};self.fs.update(pairs);self.ret(1);return
  if sel=='fileExistsAtPath:':self.ret(int(v(2) in self.fs));return
  if sel=='contentsOfDirectoryAtPath:error:':
   root=v(2).rstrip('/')+'/';self.ret(self.wrap(sorted({p[len(root):].split('/')[0] for p in self.fs if p.startswith(root)})));return
  if sel=='dataWithContentsOfURL:options:error:':self.ret(self.wrap(ob.get('data',self.fs.get(v(2)))) if k=='URL' else self.wrap(self.fs.get(v(2))));return
  if sel=='dataWithContentsOfFile:options:error:':self.ret(self.wrap(self.fs.get(v(2))));return
  if sel=='dataWithBytesNoCopy:length:freeWhenDone:':self.ret(self.wrap(bytes(self.u.mem_read(x(2),x(3)))));return
  if sel=='bytes':self.ret(ob['ptr']);return
  if sel=='length':self.ret(len(ob.get('data',self.value(target))));return
  if sel=='code':self.ret(ob.get('code',0));return
  if sel=='writeToFile:options:error:':self.fs[v(2)]=ob['data'];self.ret(1);return
  if sel=='writeToFile:atomically:':self.fs[v(2)]=ob['data'];self.ret(1);return
  if sel=='JSONObjectWithData:options:error:':
   try:r=self.wrap(json.loads(v(2)))
   except Exception:r=0;self.u.mem_write(x(4),struct.pack('<Q',self.obj('Error')))
   self.ret(r);return
  if sel=='dataWithJSONObject:options:error:':self.ret(self.wrap(json.dumps(v(2),ensure_ascii=False,indent=4).encode()));return
  if sel=='whitespaceAndNewlineCharacterSet':self.ret(self.obj('Charset',chars=' \r\n\t'));return
  if sel=='characterSetWithCharactersInString:':self.ret(self.obj('Charset',chars=v(2)));return
  if sel=='componentsSeparatedByCharactersInSet:':self.ret(self.wrap(re.split('['+re.escape(self.objects[x(2)]['chars'])+']',self.value(target))));return
  if sel=='stringByTrimmingCharactersInSet:':self.ret(self.wrap(self.value(target).strip(self.objects[x(2)]['chars'])));return
  if sel=='regularExpressionWithPattern:options:error:':self.ret(self.obj('Regex',pattern=v(2)));return
  if sel=='matchesInString:options:range:':self.ret(self.array([self.obj('Match',match=m) for m in re.finditer(ob['pattern'],v(2))]));return
  if sel in ['rangeAtIndex:','range']:
   a,b=ob['match'].span(x(2) if sel=='rangeAtIndex:' else 0);self.ret(a);self.u.reg_write(UC_ARM64_REG_X1,b-a);return
  if sel=='substringWithRange:':self.ret(self.wrap(self.value(target)[x(2):x(2)+x(3)]));return
  if sel=='numberOfMatchesInString:options:range:':self.ret(len(re.findall(ob['pattern'],v(2))));return
  if sel=='mainBundle':self.ret(self.obj('NSBundle'));return
  if sel=='bundlePath':self.ret(self.wrap('/app'));return
  if sel=='UUID':self.uuid+=1;self.ret(self.obj('UUID',n=self.uuid));return
  if sel=='UUIDString':self.ret(self.wrap('uuid'+str(ob['n'])));return
  if sel=='timeIntervalSinceReferenceDate':self.ret(d=(12345.,));return
  if sel=='imageWithData:':
   try:im=Image.open(io.BytesIO(v(2)));im.load();self.ret(self.obj('UIImage',width=im.width,height=im.height))
   except Exception:self.ret(0)
   return
  if sel=='initWithSize:':self.ret(target);return
  if sel=='JPEGDataWithCompressionQuality:actions:':
   # UIKit rendering is substituted with a valid 256px JPEG. Not a layout test.
   out=io.BytesIO();Image.new('RGB',(256,256)).save(out,'JPEG');self.rendered+=1;self.ret(self.wrap(out.getvalue()));return
  raise AssertionError((k,sel))
 def hook(self,u,pc,size,user):
  a=pc-self.slide;x=self.x
  if a==0xdadc:self.ret(self.wrap('/import'));return
  if a==0xdf38:self.ret(self.wrap('/import/log'));return
  if a==0x1ff88:
   ob=self.objects[x(0)];out=io.BytesIO();Image.new('RGB',(ob['width'],ob['height'])).save(out,'PNG');self.ret(self.wrap(out.getvalue()));return
  if a==0xdc68:self.logs.append(self.cstring(x(0)));self.ret();return
  if a==0x20108:self.objc();return
  if a==0x1ffac:u.mem_write(x(0),b'\0'*x(1));self.ret();return
  if a==0x20090:self.ret(self.alloc(x(0)));return
  if a==0x20060:self.ret();return
  if a==0x200a8:u.mem_write(x(0),bytes(u.mem_read(x(1),x(2))));self.ret(x(0));return
  if a==0x200b4:u.mem_write(x(0),bytes([x(1)&255])*x(2));self.ret(x(0));return
  if a==0x2009c:
   l,r=bytes(u.mem_read(x(0),x(2))),bytes(u.mem_read(x(1),x(2)));self.ret(0 if l==r else 1);return
  if a==0x20168:self.ret(0 if self.cstring(x(0))==self.cstring(x(1)) else 1);return
  if a in [0x20180,0x2018c]:
   text=self.cstring(x(0));num=re.match(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)',text);end=len(num[0]) if num else 0
   if x(1):u.mem_write(x(1),struct.pack('<Q',x(0)+end))
   num=float(num[0]) if num else 0
   if a==0x20180:self.ret(d=(num,))
   else:self.ret(int(num)&0xffffffffffffffff)
   return
  if a==0x20174:self.ret(len(self.cstring(x(0)).encode()));return
  if a==0x20198:self.ret(self.alloc(b'1.2.13\0'));return
  if a==0x20084:self.ret(0);return
  if a==0x2006c:
   p=x(0);src,ln=struct.unpack('<QI',u.mem_read(p,12));dst=struct.unpack('<Q',u.mem_read(p+24,8))[0];buf=zlib.decompress(bytes(u.mem_read(src,ln)),-15);u.mem_write(dst,buf);u.mem_write(p+16,struct.pack('<Q',ln));u.mem_write(p+40,struct.pack('<Q',len(buf)));self.ret(1);return
  if a==0x20078:self.ret(0);return
  if a==0x1fff4:self.ret(zlib.crc32(bytes(u.mem_read(x(1),x(2))),x(0)));return
  if a==0x2015c:
   fmt=self.cstring(x(2));sp=u.reg_read(UC_ARM64_REG_SP);arg=struct.unpack('<Q',u.mem_read(sp,8))[0]
   if fmt=='%s':s=self.cstring(arg)
   elif '%lld' in fmt:s=fmt.replace('%lld',str(arg))
   elif '%d' in fmt or '%u' in fmt:s=fmt.replace('%d',str(arg&0xffffffff)).replace('%u',str(arg&0xffffffff))
   else:raise AssertionError(('format',fmt))
   out=s.encode()[:x(1)-1];u.mem_write(x(0),out+b'\0');self.ret(len(out));return
  super().hook(u,pc,size,user)
 def run_zip(self,data):
  url=self.wrap('/input.zip');self.fs['/input.zip']=data;err=self.alloc(1024);self.u.reg_write(UC_ARM64_REG_X0,url);self.u.reg_write(UC_ARM64_REG_X1,err);self.u.reg_write(UC_ARM64_REG_X2,1024);self.u.reg_write(UC_ARM64_REG_LR,self.stop);self.u.emu_start(self.slide+0xe258,self.stop+4,count=30000000)
  assert self.u.reg_read(UC_ARM64_REG_PC)==self.stop,'instruction budget exhausted'
  return self.x(0),self.cstring(err)
class ClobberImport(Import):
 def hook(self,u,pc,size,user):
  a=pc-self.slide
  if a==0x20150:
   self.ret(self.x(0))
   for i in range(1,18):u.reg_write(UC_ARM64_REG_X0+i,0)
   return
  super().hook(u,pc,size,user)
def main():
 source=Path(sys.argv[1]);raw=source.read_bytes();b,_,syms=repair((ROOT/'binaries/ArcaeaPractice.dylib').read_bytes(),(ROOT/'diagnostics.o').read_bytes());cases=[]
 with zipfile.ZipFile(io.BytesIO(raw)) as z:files={n:z.read(n) for n in z.namelist()}
 meta=json.loads(files['songlist.json']);songid=meta['id']
 def pack(f):
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
   for n,d in f.items():z.writestr(n,d)
  return out.getvalue()
 def check(label,data,success,expected=None,plugin=b,model=Import):
  m=model(plugin);ok,error=m.run_zip(data);assert bool(ok)==success,(label,error)
  rec=dict(test=label,success=bool(ok),error=error)
  if success:
   active=json.loads(m.fs['/import/active.json']);catalog='/import/'+active['catalog']+'/songs/songlist'
   if catalog not in m.fs:catalog=next(p for p in m.fs if '/catalog/' in p and p.endswith('/songs/songlist'))
   song=json.loads(m.fs[catalog])['songs'][-1];assert song['id']==songid and song['artist']==meta['artist'];assert [d['ratingClass'] for d in song['difficulties']]==[3]
   root='/import/library/songs/'+songid+'/';assert all(root+n in m.fs for n in ['3.aff','base.ogg','1080_base.jpg','1080_base_256.jpg'])
   assert Image.open(io.BytesIO(m.fs[root+'1080_base_256.jpg'])).size==(256,256)
   rec.update(committed_resources=True,active_catalog=True,valid_difficulties=[3],preview_dimensions=[256,256])
  elif expected:assert expected in error,(label,error)
  cases.append(rec);print(label,'PASS',flush=True)
 check('provided_archive_original_bytes',raw,True)
 # Smaller AFF fixture exercises the same import path without repeatedly parsing
 # all 6201 original arcs. The original archive above is tested unmodified.
 small=dict(files);small['3.aff']=b'AudioOffset:26\n-\ntiming(0,179,4);\n(1000,1);\n'
 comparison=ROOT/'binaries/ArcaeaPractice-r8-comparison.dylib'
 if comparison.exists():check('r8_reproduces_valid_JSON_rejection_when_selector_call_clobbers_x2',pack(small),False,'谱面信息无效',comparison.read_bytes(),ClobberImport)
 check('current_import_survives_all_selector_caller_saved_register_clobbers',pack(small),True,model=ClobberImport)
 for name in ['songlist.txt','song.txt','song.json','SONGLIST.JSON']:
  f=dict(small);f[name]=f.pop('songlist.json');check('metadata_filename_'+name,pack(f),True)
 for label,obj in [('single_song_wrapper',{'songs':[meta]}),('single_song_array',[meta])]:
  f=dict(small);f['songlist.json']=json.dumps(obj).encode();check(label,pack(f),True)
 f=dict(small);f.pop('base_256.jpg');check('missing_separate_preview_generated',pack(f),True)
 f={'nested/'+n:d for n,d in small.items()};check('nested_metadata_and_assets',pack(f),True)
 f=dict(small);f['songlist.json']=b'{bad json';check('invalid_json_rejected',pack(f),False)
 f=dict(small);f['../escape.txt']=b'unsafe';check('path_traversal_still_rejected',pack(f),False,'路径')
 broken=bytearray(pack(small));off=0
 while True:
  off=broken.find(b'PK\x01\x02',off);assert off>=0
  size=struct.unpack_from('<H',broken,off+28)[0]
  if broken[off+46:off+46+size]==b'base.jpg':break
  off+=46+size
 broken[off+16]^=1;check('corrupt_resource_CRC_still_rejected',bytes(broken),False,'CRC')
 f=dict(small);f['songlist.json']=json.dumps({'songs':[meta,meta]}).encode();check('ambiguous_multi_song_document_rejected',pack(f),False)
 # Verify actual tick no longer creates the UILabel/background at all, and the
 # shared notice method returns without UIKit calls even for failure messages.
 from test_runloop import Runtime
 m=Runtime(b,0x1000000);m.window(root=False,key=True);m.invoke(0x1228);m.pause_at_buttons=True;m.invoke(0x2970,stop=0x2b80);assert m.label_factories==0
 before=len(m.calls);m.invoke(0x4180);assert len(m.calls)==before;cases.append(dict(test='whole_bottom_banner_never_created_or_shown',success=True))
 report=dict(passed=True,checks=len(cases),scope=__doc__,input_archive_sha256=hashlib.sha256(raw).hexdigest(),cases=cases)
 (ROOT/'import-archive-regression.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('Import archive regression PASS',len(cases))
if __name__=='__main__':main()
