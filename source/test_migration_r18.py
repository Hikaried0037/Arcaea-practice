"""Compiled snapshot resource hashes through production JS legacy-duplicate migration and native commit."""
from pathlib import Path
import json,subprocess,os
from test_library_native import Native,ROOT
m=Native();chart=b'AudioOffset:0\n-\ntiming(0,120,4);\n(1000,1);'
songs=[]
for i,name in enumerate(['local_first','local_second','local_distinct']):
 songs.append(dict(id=name,idx=i,set='base',title_localized={'en':name},difficulties=[dict(ratingClass=3,rating=10)]))
 m.fs['/import/library/songs/'+name+'/3.aff']=chart+(b'\n(2000,2);' if i==2 else b'')
m.fs['/app/songs/songlist']=json.dumps({'songs':songs}).encode();m.fs['/app/songs/packlist']=b'{"packs":[{"id":"base","section":"arcaea","name_localized":{"en":"Arcaea"}}]}'
resources={p:v for p,v in m.fs.items() if p.endswith('.aff')}
snapshot=m.value(m.call('_snapshot'))['data'];assert snapshot['songs']['songs'][0]['practice_chart_hashes']==snapshot['songs']['songs'][1]['practice_chart_hashes']
script="const {Catalog}=require('./catalog.js');const fs=require('fs');const c=new Catalog(JSON.parse(fs.readFileSync(0,'utf8')));process.stdout.write(JSON.stringify({master:c.data,runtime:c.runtime(),removed:c.duplicatesRemoved}));"
result=json.loads(subprocess.run([os.environ.get('NODE_BINARY','node'),'-e',script],cwd=ROOT,input=json.dumps(snapshot),capture_output=True,text=True,encoding='utf-8',check=True).stdout)
assert result['removed']==1;master=result['master'];assert [s['id'] for s in master['songs']['songs']]==['local_first','local_distinct'];assert master['songs']['practice_duplicate_archive'][0]['id']=='local_second'
op={k:json.dumps(v,indent=4)+'\n' for k,v in [('masterText',master),('songText',result['runtime']['songs']),('packText',result['runtime']['packs'])]}
assert m.call('_commit',m.wrap(op))==1;assert m.value(m.call('_loadMaster'))==master
assert all(m.fs[p]==v for p,v in resources.items());assert '/import/ArcLibrary-undo.json' in m.fs
result=dict(passed=True,checks=5,cases=['native_snapshot_hashes_actual_existing_AFF','JS_merges_only_complete_identical_local_hash_sets','metadata_archived_distinct_chart_kept','native_commit_and_cold_master_match_clean_catalog','all_original_AFF_resources_and_undo_preserved'],scope=__doc__)
(ROOT/'migration-r18-regression.json').write_text(json.dumps(result,indent=2)+'\n');print('R18 migration regression PASS 5')
