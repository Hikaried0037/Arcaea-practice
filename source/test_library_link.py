"""Inspect every emitted ARM64 relocation, dyld bind, rebase and export address."""
from pathlib import Path
import struct,json
from inspect_ipa import macho
from test_macho import dyld_targets,read_uleb
r=Path(__file__).resolve().parent;b=(r/'ArcLibrary.dylib').read_bytes();report=json.loads((r/'ArcLibrary.link.json').read_text());m=macho(b);segments=[c for c in m['commands'] if 'segment'in c];info=next(c for c in m['commands'] if c['command']=='0x80000022')['file_offset'];checks=[]
assert [c['segment'] for c in segments]==['__TEXT','__DATA','__LINKEDIT']
for x,y in zip(segments,segments[1:]):assert x['vmaddr']+x['vmsize']<=y['vmaddr'] and x['fileoff']+x['filesize']<=y['fileoff']
for s in segments:assert s['fileoff']+s['filesize']<=len(b)
checks.append('segments_and_file_bounds')
ro,rs,bo,bs=struct.unpack_from('<4I',b,info+8);rebases=dyld_targets(b[ro:ro+rs]);bind=dyld_targets(b[bo:bo+bs],True)
assert [segments[s]['vmaddr']+o for s,o,_,_ in rebases]==sorted(report['rebases']);assert {n:segments[s]['vmaddr']+o for s,o,n,_ in bind}==report['pointers'];assert all(1<=ordinal<=7 for s,o,n,ordinal in bind);checks.append('all_rebases_and_bind_slots_match_link_manifest')
assert '__dispatch_main_q' in report['undefined'] and '_dispatch_get_main_queue' not in report['undefined'];checks.append('dispatch_main_queue_uses_exported_object_not_inline_C_helper')
for x in report['relocations']:
 pc,dest,typ=x['pc'],x['target'],x['type']
 if typ==0:assert struct.unpack_from('<Q',b,pc)[0]==dest
 else:
  w=struct.unpack_from('<I',b,pc)[0]
  if typ==2:
   v=w&0x3ffffff;v=v-(1<<26) if v&(1<<25) else v;assert pc+4*v==dest
  elif typ in [3,5]:
   v=((w>>5)&0x7ffff)*4+((w>>29)&3);v=v-(1<<21) if v&(1<<20) else v;assert (pc&~4095)+(v<<12)==dest&~4095
  elif typ in [4,6]:
   scale=(w>>30)&3 if w&0x3b000000==0x39000000 else 0
   if w&0x3b000000==0x39000000 and w&(1<<26) and w&(1<<23):scale=4
   assert (((w>>10)&4095)<<scale)==dest&4095
checks.append('every_relocation_decodes_to_expected_target')
eo,es=struct.unpack_from('<II',b,info+40);trie=b[eo:eo+es];size,p=read_uleb(trie,0);assert size==0;n=trie[p];p+=1;found={}
for i in range(n):
 e=trie.index(0,p);name=trie[p:e].decode();child,p=read_uleb(trie,e+1);terminal,q=read_uleb(trie,child);flags,q=read_uleb(trie,q);address,q=read_uleb(trie,q);assert flags==0 and terminal>0;found[name]=address
assert found==report['exported'];checks.append('export_trie_open_and_reload_match_symbols')
assert set(s['name'] for s in m['symbols'] if s['type']&1)==set(found);checks.append('only_plugin_entry_and_reload_are_exported')
result=dict(passed=True,checks=len(checks),cases=checks,relocation_count=len(report['relocations']),bind_count=len(bind),rebase_count=len(rebases),scope=__doc__+' Not an iOS dyld or code-signature execution.');(r/'library-link-regression.json').write_text(json.dumps(result,indent=2)+'\n');print('New dylib link audit PASS',result)

