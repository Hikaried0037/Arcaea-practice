"""Fingerprint-locked native ETR/BYD tab repair; no invented difficulty records."""
from pathlib import Path
import struct,hashlib,json
from inspect_ipa import macho
INPUT='4b4d50c50f372c95c47db33b48d20981e15ff314570ed4553c8e16f1dba30812'
ISLAND_FILE=0x1652000
ISLAND=0x16aa000 # VM offset differs from file offset after zero-fill DATA

def branch(pc,target,link=False):
 d=target-pc;assert d%4==0 and -(1<<27)<=d<(1<<27)
 return struct.pack('<I',(0x94000000 if link else 0x14000000)|((d//4)&0x3ffffff))

def repair_main(original,obj):
 assert hashlib.sha256(original).hexdigest()==INPUT,'Unrecognized main executable'
 host=macho(original);rx=next(c for c in host['commands'] if c.get('segment')=='__PRACCODE');assert rx['vmaddr']-0x100000000+ISLAND_FILE-rx['fileoff']==ISLAND;assert struct.unpack_from('<I',original,rx['file_offset']+60)[0]&4
 m=macho(obj);sec=next(s for s in m['sections'] if s['name']=='__text');code=bytearray(obj[sec['offset']:sec['offset']+sec['size']]);syms=m['symbols'];defined={s['name']:ISLAND+s['address'] for s in syms if s['section']};targets={**defined,'_difficulty_apply':0x8eb8a8,'_difficulty_change':0x86af60,'_difficulty_sound':0xb6bde8,'_byd_update_body':0x8f0da8,'_etr_update_body':0x8f22a8,'_row_continue':0x87cbd0,'_row_next':0x87cbe4,'_string_construct':0xebdb28,'_button_load_textures':0xeb75bc,'_string_delete':0x11b1e38,'_song_difficulty':0x84ed30,'_native_level_render':0x8f3e54,'_label_set_string':0xe4c02c}
 p=32;relocs=None
 for _ in range(struct.unpack_from('<I',obj,16)[0]):
  cmd,size=struct.unpack_from('<II',obj,p)
  if cmd==0x19:
   for j in range(struct.unpack_from('<I',obj,p+64)[0]):
    q=p+72+80*j
    if obj[q:q+16].split(b'\0')[0]==b'__text':relocs=struct.unpack_from('<II',obj,q+56)
  p+=size
 assert relocs
 for i in range(relocs[1]):
  off,info=struct.unpack_from('<II',obj,relocs[0]+i*8);name=syms[info&0xffffff]['name'];assert info>>28==2 and (info>>27)&1
  op=struct.unpack_from('<I',code,off)[0];assert op&0x7c000000==0x14000000
  code[off:off+4]=branch(ISLAND+off,targets[name],bool(op&0x80000000))
 for label in ['_catalog_owner_page','_sound_owner_page']:
  pc=defined[label];d=((0x1678000&~4095)-(pc&~4095))>>12;assert -(1<<20)<=d<(1<<20);w=0x90000009|((d&3)<<29)|(((d>>2)&0x7ffff)<<5);struct.pack_into('<I',code,pc-ISLAND,w)
 b=bytearray(original);edits=[]
 def change(at,expected,new,reason):
  assert bytes(b[at:at+len(expected)])==expected,(hex(at),'fingerprint mismatch');b[at:at+len(expected)]=new;edits.append(dict(offset=at,old=expected.hex(),new=new.hex(),reason=reason))
 assert len(code)<=0x1000 and not any(b[ISLAND_FILE:ISLAND_FILE+len(code)])
 change(ISLAND_FILE,bytes(len(code)),bytes(code),'Bounded native catalog availability guard and repeated-tab routing in unused existing RX space')
 change(0x8f778c,bytes.fromhex('011040b9'),branch(0x8f778c,defined['_difficulty_tab']),'Main difficulty tab callback: repeat ETR or BYD toggles the alternate class')
 change(0x8f7884,branch(0x8f7884,0x8eb8a8),branch(0x8f7884,defined['_difficulty_guard']),'Existing swap callback shares target-availability guard')
 change(0x8f0da4,bytes.fromhex('ffc307d1'),branch(0x8f0da4,defined['_byd_update']),'Repair BYD visibility/enabled state after every original UI refresh return path')
 change(0x8f22a4,bytes.fromhex('ff0305d1'),branch(0x8f22a4,defined['_etr_update']),'Repair ETR visibility/enabled state after every original UI refresh return path')
 change(0x87cbcc,original[0x87cbcc:0x87cbd0],branch(0x87cbcc,defined['_song_row_nonnull']),'Skip null row before vector append and native retain')
 assert len(b)==len(original)
 report=dict(passed=True,island_file_offset=ISLAND_FILE,island_vm_offset=ISLAND,input_sha256=INPUT,output_sha256=hashlib.sha256(b).hexdigest(),edits=edits,symbols=defined,scope='Verified callbacks and post-refresh tab states; force native list re-filtering instead of activating the the missing difficulty of the current row. No new UI overlay, placeholder AFF, fabricated chart difficulty or per-frame catalog scan.')
 return bytes(b),report
