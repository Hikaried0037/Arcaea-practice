import struct, pathlib, json, zipfile, plistlib, hashlib, io
ROOT=pathlib.Path(__file__).resolve().parent
class Parts(io.RawIOBase):
 def __init__(self):
  self.parts=[open(ROOT/('ArcPrac-import-fix14-arm64-unsigned.ipa.part%03d'%n),'rb') for n in range(1,5)];self.pos=0;self.length=3799826120
 def seekable(self):return True
 def readable(self):return True
 def tell(self):return self.pos
 def seek(self,n,w=0):self.pos=n if w==0 else self.pos+n if w==1 else self.length+n;return self.pos
 def read(self,n=-1):
  n=min(n if n>=0 else self.length,self.length-self.pos);result=bytearray()
  while n:
   index,off=divmod(self.pos,1073741824);f=self.parts[index];f.seek(off);chunk=f.read(min(n,1073741824-off))
   if not chunk:raise IOError('Part not fully downloaded at offset %d'%self.pos)
   result+=chunk;self.pos+=len(chunk);n-=len(chunk)
  return bytes(result)
def macho(data):
 magic,cpu,sub,typ,n,sz,flags,res=struct.unpack_from('<8I',data)
 assert magic==0xfeedfacf,hex(magic)
 commands=[];sections=[];symbols=[];pos=32;sym=None
 for _ in range(n):
  cmd,size=struct.unpack_from('<II',data,pos);item={'command':hex(cmd),'size':size,'file_offset':pos}
  if cmd in (0xc,0xd,0x18,0x80000018,0x8000001c,0x8000001f,0x20,0x80000023):
   off=struct.unpack_from('<I',data,pos+8)[0];item['name']=data[pos+off:pos+size].split(b'\0')[0].decode(errors='replace')
  if cmd==0x19:
   seg=data[pos+8:pos+24].split(b'\0')[0].decode();vm,vms,off,fs=struct.unpack_from('<4Q',data,pos+24);count=struct.unpack_from('<I',data,pos+64)[0];item.update(segment=seg,vmaddr=vm,vmsize=vms,fileoff=off,filesize=fs)
   for j in range(count):
    secpos=pos+72+j*80;sec=data[secpos:secpos+16].split(b'\0')[0].decode();addr,length=struct.unpack_from('<QQ',data,secpos+32);fo=struct.unpack_from('<I',data,secpos+48)[0];sections.append({'segment':seg,'name':sec,'addr':addr,'size':length,'offset':fo})
  if cmd==2:sym=struct.unpack_from('<4I',data,pos+8)
  if cmd==0x2c:item.update(zip_offset=struct.unpack_from('<I',data,pos+8)[0],cryptsize=struct.unpack_from('<I',data,pos+12)[0],cryptid=struct.unpack_from('<I',data,pos+16)[0])
  commands.append(item);pos+=size
 if sym:
  so,ns,st,ss=sym
  for i in range(ns):
   no,t,s,d,value=struct.unpack_from('<IBBHQ',data,so+i*16);name=data[st+no:st+ss].split(b'\0')[0].decode(errors='replace');symbols.append({'name':name,'type':t,'section':s,'address':value})
 return {'cpu':hex(cpu),'type':typ,'commands':commands,'sections':sections,'symbols':symbols}
if __name__=='__main__':
 ipa=ROOT/'original.ipa';out=ROOT/'binaries';out.mkdir(exist_ok=True)
 with zipfile.ZipFile(ipa if ipa.exists() else Parts()) as z:
  info=plistlib.loads(z.read('Payload/Arc-mobile.app/Info.plist'));print(json.dumps({k:info.get(k) for k in ['CFBundleExecutable','CFBundleIdentifier','CFBundleVersion','MinimumOSVersion']},indent=2))
  for item in z.infolist():
   name=item.filename
   if name.endswith('.dylib') or name=='Payload/Arc-mobile.app/'+info['CFBundleExecutable']:
    data=z.read(name);target=out/pathlib.Path(name).name;target.write_bytes(data)
    if data[:4]!=b'\xcf\xfa\xed\xfe':print(name,'non-thin-mach-o',data[:4].hex());continue
    parsed=macho(data);(out/(target.name+'.json')).write_text(json.dumps(parsed,indent=2),encoding='utf-8');print(name,len(data),hashlib.sha256(data).hexdigest());print(json.dumps([c for c in parsed['commands'] if 'name' in c],indent=2))
