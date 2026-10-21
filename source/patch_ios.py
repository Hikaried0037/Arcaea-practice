"""Reproducible fix14 r22 ARM64-only repair. No signing material required."""
from pathlib import Path
import struct,hashlib,json,zipfile,copy,argparse,subprocess,os
from inspect_ipa import macho
EXPECTED='46d3c71cfcaa2d7c6e6e48bcd66e66b5748b8897fbb60b68f5230eac241938df'
BASE=0x94000; STATE=0x93f00; EXTRA=0x4000

def branch(pc,target,link=False):
 d=target-pc;assert d%4==0 and -(1<<27)<=d<(1<<27)
 return struct.pack('<I',(0x94000000 if link else 0x14000000)|((d//4)&0x3ffffff))
def uleb(n):
 b=bytearray()
 while n>=128:b.append((n&127)|128);n>>=7
 b.append(n);return bytes(b)
def link_object(data):
 m=macho(data);sec=next(s for s in m['sections'] if s['name']=='__text');code=bytearray(data[sec['offset']:sec['offset']+sec['size']]);syms=m['symbols'];defined={s['name']:BASE+s['address'] for s in syms if s['section']}
 targets={'_original_init':0x528c,'_tick_nil':0x2f2c,'_objc_getClass':0x200fc,'_sel_registerName':0x20150,'_objc_msgSend':0x20108,'_objc_autoreleasePoolPush':0x200f0,'_objc_autoreleasePoolPop':0x200e4,'_class_addMethod':0x1ffc4,'_tick_body':0x2974,'_engine_body':0x65b8,'_practice_cancel':0x5884,'_partner_not_ready':0xb68c,'_partner_choose':0xb564,'_running_scene':0xcff0,'_normal_kind':0x790c,'_paused_kind':0x7b30,'_action_denied':0x1c9c,'_action_continue':0x1d40,'_offline_frame':0xb5d0,'_native_begin_body':0x6ab4,'_native_begin_original':0x6f88,'_import_inside':0x17238,'_inside_body':0x2f6c,'_icon_body':0x1ada8,'_metadata_string':0xd5b4,'_metadata_integer':0x14164,'_import_log':0xdc68,'_import_entry_body':0xe25c,'_UIImagePNGRepresentation':0x1ff88,'_snprintf':0x2015c,'_load_pointer':0xc348,'_import_request_reload':0xcfdc,'_asset_path_continue':0xcb08,'_asset_path_fallback':0xcc38}
 targets.update(defined)
 pos=32;relocs=None
 for _ in range(struct.unpack_from('<I',data,16)[0]):
  cmd,size=struct.unpack_from('<II',data,pos)
  if cmd==0x19:
   for j in range(struct.unpack_from('<I',data,pos+64)[0]):
    p=pos+72+80*j
    if data[p:p+16].split(b'\0')[0]==b'__text':relocs=struct.unpack_from('<II',data,p+56)
  pos+=size
 assert relocs
 for i in range(relocs[1]):
  off,info=struct.unpack_from('<II',data,relocs[0]+i*8);name=syms[info&0xffffff]['name'];op=struct.unpack_from('<I',code,off)[0]
  assert info>>28==2 and ((info>>27)&1)==1 and ((info>>24)&1)==1 and ((info>>25)&3)==2,(name,hex(info))
  assert op&0x7c000000==0x14000000
  code[off:off+4]=branch(BASE+off,targets[name],bool(op&0x80000000))
 counts={k:0 for k in ['_last_stage_address','_common_mode_data_address','_state_address','_plugin_data_address']}
 for off in range(0,len(code)-3,4):
  w=struct.unpack_from('<I',code,off)[0]
  if w&0x9f000000!=0x10000000:continue
  imm=((w>>5)&0x7ffff)*4+((w>>29)&3)
  if imm&(1<<20):imm-=1<<21
  for name,target in [('_last_stage_address',STATE),('_common_mode_data_address',STATE+8),('_state_address',STATE),('_plugin_data_address',0x28000)]:
   if BASE+off+imm==defined[name]:
    d=target-(BASE+off);assert -(1<<20)<=d<(1<<20);struct.pack_into('<I',code,off,(w&0x9f00001f)|((d&3)<<29)|(((d>>2)&0x7ffff)<<5));counts[name]+=1
 assert all(counts.values()),counts
 return bytes(code),defined

def layout(b,code):
 """Insert a dedicated RX segment; keep all existing code/data addresses stable.
 Only file offsets in LINKEDIT move. Section indexes of existing symbols stay.
 """
 meta=macho(b);oldsize=struct.unpack_from('<I',b,20)[0];commands=bytearray();n=0
 assert not any(b[STATE:STATE+0x100])
 for c in meta['commands']:
  cmd=bytearray(b[c['file_offset']:c['file_offset']+c['size']]);kind=int(c['command'],16)
  if c.get('segment')=='__DATA':
   struct.pack_into('<I',cmd,4,len(cmd)+80);struct.pack_into('<I',cmd,64,struct.unpack_from('<I',cmd,64)[0]+1)
   cmd+=struct.pack('<16s16sQQ8I',b'__practice',b'__DATA',STATE,0x100,STATE,3,0,0,0,0,0,0)
  if c.get('segment')=='__LINKEDIT':
   assert c['fileoff']==c['vmaddr']==BASE
   segment=struct.pack('<II16s4Q4I',0x19,152,b'__PRACFIX',BASE,EXTRA,BASE,EXTRA,5,5,1,0)
   section=struct.pack('<16s16sQQ8I',b'__text',b'__PRACFIX',BASE,len(code),BASE,2,0,0,0x80000400,0,0,0)
   commands+=segment+section;n+=1
   struct.pack_into('<Q',cmd,24,BASE+EXTRA);struct.pack_into('<Q',cmd,40,BASE+EXTRA)
  if kind==0x80000022:
   for field in [8,16,24,32,40]:
    val=struct.unpack_from('<I',cmd,field)[0]
    if val:assert val>=BASE;struct.pack_into('<I',cmd,field,val+EXTRA)
  elif kind==2:
   for field in [8,16]:
    val=struct.unpack_from('<I',cmd,field)[0];assert val>=BASE;struct.pack_into('<I',cmd,field,val+EXTRA)
  elif kind==0xb:
   for field in [32,40,48,56,64,72]:
    val=struct.unpack_from('<I',cmd,field)[0]
    if val:assert val>=BASE;struct.pack_into('<I',cmd,field,val+EXTRA)
  elif kind in [0x26,0x29,0x1d,0x1e,0x2e,0x80000033,0x80000034]:
   val=struct.unpack_from('<I',cmd,8)[0]
   if val:assert val>=BASE;struct.pack_into('<I',cmd,8,val+EXTRA)
  commands+=cmd;n+=1
 foundation=b'/System/Library/Frameworks/Foundation.framework/Foundation\0';length=(24+len(foundation)+7)//8*8
 commands+=struct.pack('<6I',0xc,length,24,0,0,0)+foundation+b'\0'*(length-24-len(foundation));n+=1
 name=b'@loader_path/ArcLibrary.dylib\0';length=(24+len(name)+7)//8*8
 commands+=struct.pack('<6I',0xc,length,24,0,0,0)+name+b'\0'*(length-24-len(name));n+=1
 assert 32+len(commands)<=0x1214 and not any(b[32+oldsize:32+len(commands)])
 b[BASE:BASE]=b'\0'*EXTRA;b[BASE:BASE+len(code)]=code
 b[32:32+len(commands)]=commands;struct.pack_into('<II',b,16,n,len(commands))
 m=macho(b);info=next(c for c in m['commands'] if c['command']=='0x80000022')['file_offset'];off,size=struct.unpack_from('<II',b,info+16);old=bytes(b[off:off+size]);assert old[-1]==0
 ordinal=sum(c['command'] in ['0xc','0x80000018','0x8000001f','0x80000023'] for c in m['commands']);assert ordinal==7
 program=old.rstrip(b'\0')+bytes([0x16,0x40])+b'_NSRunLoopCommonModes\0'+bytes([0x51,0x60,0,0x71])+uleb(STATE+8-0x28000)+bytes([0x90,0])
 program=program[:-1]+bytes([0x17,0x40])+b'_arc_library_open\0'+bytes([0x51,0x60,0,0x71])+uleb(STATE+80-0x28000)+bytes([0x90,0x17,0x40])+b'_arc_library_take_reload\0'+bytes([0x51,0x60,0,0x71])+uleb(STATE+88-0x28000)+bytes([0x90,0])
 start=(len(b)+7)//8*8;b+=b'\0'*(start-len(b))+program;struct.pack_into('<II',b,info+16,start,len(program))
 link=next(c for c in m['commands'] if c.get('segment')=='__LINKEDIT');size=len(b)-link['fileoff'];p=link['file_offset'];struct.pack_into('<Q',b,p+48,size);struct.pack_into('<Q',b,p+32,(size+0x3fff)//0x4000*0x4000)
 return b

def repair(original,object_data):
 assert hashlib.sha256(original).hexdigest()==EXPECTED,'Unknown input dylib'
 code,syms=link_object(object_data);assert len(code)<EXTRA
 b=bytearray(original);edits=[]
 def edit(o,old,new):
  assert b[o:o+len(old)]==old,(hex(o),b[o:o+len(old)].hex(),old.hex());assert len(old)==len(new);b[o:o+len(new)]=new;edits.append({'offset':hex(o),'before':old.hex(),'after':new.hex()})
 def hook(o,name,link=False):edit(o,original[o:o+4],branch(o,syms[name],link))
 edit(0x19184,bytes.fromhex('60000090'),branch(0x19184,0x191a0))
 edit(0x1933c,bytes.fromhex('f40300aa600000d0'),bytes.fromhex('e00319aa')+branch(0x19340,0x19358))
 hook(0x5288,'_bootstrap');hook(0x29a4,'_tick_probe',True);hook(0x1254,'_ui_started',True)
 edit(0x1478,bytes.fromhex('20010090007c1b91'),branch(0x1478,syms['_common_mode'],True)+branch(0x147c,0x14a8))
 hook(0x14c8,'_ui_registered',True);edit(0x1731c,bytes.fromhex('f657bda9'),bytes.fromhex('c0035fd6'));edit(0xd18c,bytes.fromhex('42d141fd'),bytes.fromhex('02106a1e'))
 hook(0x1344,'_register_tick',True);hook(0x1398,'_install_observers',True);hook(0x2970,'_ui_tick_gate');hook(0x65b4,'_engine_gate');hook(0xb644,'_partner_applied',True);hook(0xb688,'_partner_retry');hook(0x55e4,'_state_try_read')
 # Actual pause UI must be attached to its HUD, with all ancestors visible.
 hook(0x7ad0,'_snapshot_pause_gate')
 hook(0x1d2c,'_action_pause_gate')
 hook(0x2c9c,'_fresh_ui_kind',True)
 # A fresh validated pause menu replaces the stale UI-kind veto. Ignore the
 # legacy modal hint in the snapshot; actual attachment still gates kind=2.
 edit(0x7aa8,original[0x7aa8:0x7aac],bytes.fromhex('1f2003d5'))
 hook(0x2c20,'_panel_pending_kind',True)
 edit(0x7b1c,original[0x7b1c:0x7b20],bytes.fromhex('1f2003d5'))
 hook(0x2f68,'_overlay_inside')
 hook(0x6f84,'_native_begin_gate')
 hook(0x66bc,'_offline_frame_refresh',True)
 # Consume the successful selection notice but omit its four-second banner.
 edit(0x2ee0,original[0x2ee0:0x2ee4],branch(0x2ee0,0x2f08))
 hook(0x19ddc,'_hide_partner_lock',True)
 hook(0x1ada4,'_stable_self_icon')
 edit(0x1be08,original[0x1be08:0x1be0c],bytes.fromhex('c0035fd6'))
 edit(0x1c44c,original[0x1c44c:0x1c454],bytes.fromhex('00008052c0035fd6'))
 edit(0x1e598,original[0x1e598:0x1e59c],bytes.fromhex('c0035fd6'))
 # Remove the complete toast view, including its translucent background.
 edit(0x2ab8,original[0x2ab8:0x2abc],branch(0x2ab8,0x2b80))
 edit(0x4180,original[0x4180:0x4184],bytes.fromhex('c0035fd6'))
 edit(0xe258,original[0xe258:0xe260],bytes.fromhex('00008052c0035fd6')) # legacy importer disabled
 hook(0x1752c,'_library_open_bridge')
 hook(0xcb04,'_background_path_gate')
 hook(0xed84,'_metadata_name',True)
 hook(0xf428,'_metadata_json',True)
 hook(0x10e40,'_jacket_lookup',True)
 hook(0x13950,'_write_pack_cover',True)
 hook(0xd0e4,'_reload_catalogs',True)
 # A preview is generated from the jacket when a separate one is absent.
 edit(0x111f8,original[0x111f8:0x111fc],struct.pack('<I',0x7100011f)) # cmp w8,#0
 def replace_text(old,new):
  old=old.encode();new=new.encode();assert len(new)<=len(old)
  off=original.index(old+b'\0');edit(off,old,new+b'\0'*(len(old)-len(new)))
 replace_text('导入','曲库')
 replace_text('压缩包需要且只能包含一份 song.json 或 .arcproj','需一份 songlist.json/.txt、song.json 或 .arcproj')
 replace_text('添加你的谱面\n\n压缩包需带齐：\n谱面信息 song.json / .arcproj\nOGG 音乐 base.ogg\n1–5 张 0.aff 至 4.aff\n曲绘与缩略图两张图片','导入格式：\nsonglist.json / songlist.txt\n兼容 song.json / .arcproj\nbase.ogg 与有效 AFF\nbase.jpg / 1080_base.jpg\n缩略图自动生成')
 b=layout(b,code)
 assert struct.unpack_from('<4Q',b,0x92910)==struct.unpack_from('<4Q',original,0x92910)
 report={'revision':'windowfix-r22','input_dylib_sha256':EXPECTED,'output_dylib_sha256':hashlib.sha256(b).hexdigest(),'code_island_offset':BASE,'code_island_bytes':len(code),'mutable_state_offset':STATE,'edits':edits,'symbols':syms,'signing':'unsigned; re-sign complete app and embedded dylib','scope':['r2 window/runloop fixes retained','detach preview on resign; defer cancellation until active engine frame','strict actual pause-menu visibility','persist successful partner choices with NSUserDefaults; retry cold-start choice until owner ready','nonblocking main-thread snapshot read retains previous complete state when engine lock is busy','actual native pause-node attachment checked for visibility and clicks','defer plugin frame and pending cancel until original audio backend has resumed its mixer','fresh pause entry bypasses obsolete cached-kind veto','actual pause snapshot ignores legacy global modal hint at both veto sites','retain practice panel across native begin hiding the pause node by published active request ID','outer overlay includes actual import button and modal hit regions','restore queued partner selection before menu bounds are available','skip rebuilding already-correct portrait and avatar','correct first self-profile icon lookup for exact UserCell caller','remove entire bottom toast view and disable all shared toast display','preserve type-check class across selector registration; C-ABI caller-saved clobber regression','revision and metadata-stage diagnostics in local import log','verify pack-cover parent directory; fallback to validated jacket PNG if bundled cover unavailable','retry cover atomic-write failure; retain fatal handling and log NSError numeric code on real failure','import songlist JSON/TXT discovery and single-song wrapper normalization','ignore inactive negative-rating difficulty placeholders','resolve conventional jacket filenames and generate preview from one jacket','native partner portrait and self UserCell refresh after restore/selection','partner lock opacity forced to zero; four custom editor buttons and hit targets disabled']}
 return bytes(b),report,syms

def main():
 ap=argparse.ArgumentParser();ap.add_argument('input',type=Path);ap.add_argument('output',type=Path);ap.add_argument('--zig',required=True);ap.add_argument('--sayonara-only',action='store_true');a=ap.parse_args();here=Path(__file__).resolve().parent
 env=dict(os.environ);env.setdefault('ZIG_GLOBAL_CACHE_DIR',str(here/'zig-cache'));subprocess.run([a.zig,'cc','-target','aarch64-ios.12.4','-c',str(here/'diagnostics.s'),'-o',str(here/'diagnostics.o')],env=env,check=True)
 subprocess.run([a.zig,'cc','-target','aarch64-ios.12.4','-c',str(here/'difficulty.s'),'-o',str(here/'difficulty.o')],env=env,check=True)
 obj=(here/'diagnostics.o').read_bytes();assert a.input.resolve()!=a.output.resolve()
 additions={'Payload/Arc-mobile.app/Frameworks/ArcLibrary.dylib':(here/'ArcLibrary.dylib').read_bytes()}
 if not a.sayonara_only:additions['Payload/Arc-mobile.app/ArcLibrary/restore-bundled-catalog']=b'full-catalog-r22\n'
 for name in ['index.html','library.css','catalog.js','ui.js']:additions['Payload/Arc-mobile.app/ArcLibrary/'+name]=(here/name).read_bytes()
 with zipfile.ZipFile(a.input) as src,zipfile.ZipFile(a.output,'w',allowZip64=True) as dst:
  assert hashlib.sha256(src.read('Payload/Arc-mobile.app/Arc-mobile')).hexdigest()=='4b4d50c50f372c95c47db33b48d20981e15ff314570ed4553c8e16f1dba30812'
  from patch_difficulty import repair_main
  main_data,main_report=repair_main(src.read('Payload/Arc-mobile.app/Arc-mobile'),(here/'difficulty.o').read_bytes())
  replacements={'Payload/Arc-mobile.app/Arc-mobile':main_data};removed=[];preserved=[]
  songs_prefix='Payload/Arc-mobile.app/songs/'
  if a.sayonara_only:
   songlist=json.loads(src.read(songs_prefix+'songlist'));songlist['songs']=[v for v in songlist['songs'] if v['id']=='sayonarahatsukoi'];assert len(songlist['songs'])==1
   packlist=json.loads(src.read(songs_prefix+'packlist'));packlist['packs']=[v for v in packlist['packs'] if v['id']==songlist['songs'][0]['set']];assert len(packlist['packs'])==1
   replacements.update({songs_prefix+'songlist':(json.dumps(songlist,ensure_ascii=False,indent=4)+'\n').encode(),songs_prefix+'packlist':(json.dumps(packlist,ensure_ascii=False,indent=4)+'\n').encode()})
  for font in ['Exo-Regular.ttf','NotoSansCJKsc-Regular.otf']:additions['Payload/Arc-mobile.app/ArcLibrary/Fonts/'+font]=src.read('Payload/Arc-mobile.app/Fonts/'+font)
  entries=src.infolist();ordered=sorted(entries,key=lambda e:e.header_offset);ends={e.header_offset:(ordered[i+1].header_offset if i+1<len(ordered) else src.start_dir) for i,e in enumerate(ordered)}
  for e in entries:
   if a.sayonara_only and e.filename.startswith(songs_prefix):
    relative=e.filename[len(songs_prefix):]
    if '/' in relative and relative.split('/')[0] not in {'sayonarahatsukoi','tutorial','random','pack'}:removed.append(e.filename);continue
   if e.filename in replacements:dst.writestr(copy.copy(e),replacements[e.filename]);continue
   if e.filename.endswith('/ArcaeaPractice.dylib'):
    data,report,_=repair(src.read(e),obj);dst.writestr(copy.copy(e),data);continue
   preserved.append(e.filename);src.fp.seek(e.header_offset);dst.fp.seek(dst.start_dir);info=copy.copy(e);info.header_offset=dst.fp.tell();remaining=ends[e.header_offset]-e.header_offset
   while remaining:
    chunk=src.fp.read(min(remaining,8*1024*1024));assert chunk;dst.fp.write(chunk);remaining-=len(chunk)
   dst.filelist.append(info);dst.NameToInfo[info.filename]=info;dst.start_dir=dst.fp.tell();dst._didModify=True
  for name,payload in additions.items():
   entry=zipfile.ZipInfo(name);entry.compress_type=zipfile.ZIP_DEFLATED;entry.create_system=3;entry.external_attr=(0o100755 if name.endswith('.dylib') else 0o100644)<<16;dst.writestr(entry,payload)
 with zipfile.ZipFile(a.input) as src,zipfile.ZipFile(a.output) as dst:
  assert (set(src.namelist())-set(removed))|set(additions)==set(dst.namelist());assert dst.testzip() is None
  for name in preserved:
   e=src.getinfo(name);other=dst.getinfo(name);assert (other.CRC,other.file_size,other.external_attr)==(e.CRC,e.file_size,e.external_attr)
  if a.sayonara_only:
   songs=json.loads(dst.read(songs_prefix+'songlist'))['songs'];assert len(songs)==1 and songs[0]['id']=='sayonarahatsukoi'
   for d in songs[0]['difficulties']:assert songs_prefix+'sayonarahatsukoi/'+str(d['ratingClass'])+'.aff' in dst.namelist()
 report['new_library_sha256']=hashlib.sha256(additions['Payload/Arc-mobile.app/Frameworks/ArcLibrary.dylib']).hexdigest()
 report['legacy_importer_disabled']=True
 report['scope']=['previous practice/lifecycle/partner fixes retained','legacy importer action redirected to independent ArcLibrary.dylib; old importArchive entry hard-disabled','new Android-style catalog model, file picker, ZIP/AFF validation, image normalization and atomic generation commit','migrate Another songs to base, local IDs, song deletion and move, pack/category CRUD, cover replacement, one-step catalog undo','shared native catalog resource redirection and engine-thread reload retained','headless desktop and ARM64 host tests do not prove physical iOS UI or gameplay behavior']
 report['native_difficulty_repair']=main_report
 report.update(preserved_entries=len(preserved),removed_song_entries=len(removed),sayonara_only=a.sayonara_only,catalogs_changed=list(replacements),unchanged_info_plist_other_frameworks=True)
 report.update(ipa_sha256=hashlib.file_digest(a.output.open('rb'),'sha256').hexdigest(),ipa_bytes=a.output.stat().st_size,zip_crc='passed')
 (here/'difficulty-patch.json').write_text(json.dumps(main_report,indent=2)+'\n')
 a.output.with_suffix('.verification.json').write_text(json.dumps(report,indent=2)+'\n');print('Built',a.output,report['output_dylib_sha256'])
if __name__=='__main__':main()
