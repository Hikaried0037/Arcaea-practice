"""Full bundled catalog restored into single-song private catalog. Actual compiled merge/commit and production JS; framework/filesystem are host models."""
from pathlib import Path
import zipfile,json,subprocess,os,hashlib
from test_library_native import Native,ROOT
with zipfile.ZipFile(__import__('os').environ.get('ORIGINAL_IPA', str(ROOT.parent/'original.ipa'))) as z:
 prefix='Payload/Arc-mobile.app/songs/';songs=json.loads(z.read(prefix+'songlist'));packs=json.loads(z.read(prefix+'packlist'))
assert len(songs['songs'])==562 and len(packs['packs'])==63
m=Native();oldSong=songs['songs'][0];local=dict(id='local_preserved',idx=1,set='base',title_localized={'en':'Existing local'},difficulties=[dict(ratingClass=3,rating=12)])
old=dict(songs={'songs':[oldSong,local]},packs={'packs':[packs['packs'][0]]})
m.fs['/app/songs/songlist']=json.dumps(songs).encode();m.fs['/app/songs/packlist']=json.dumps(packs).encode();m.fs['/app/ArcLibrary/restore-bundled-catalog']=b'full';m.fs['/import/active.json']=b'{"catalog":"generation_old"}';m.fs['/import/catalog/generation_old/ArcLibrary.json']=json.dumps(old).encode();m.fs['/import/library/songs/local_preserved/3.aff']=b'unchanged resource'
merged=m.value(m.call('_loadMaster'));assert len(merged['songs']['songs'])==563 and len(merged['packs']['packs'])==63 and merged['practice_restore_bundled']==1;assert json.loads(m.fs['/import/ArcLibrary-pre-full-restore.json'])==old
script="const {Catalog}=require('./catalog.js');const fs=require('fs');const c=new Catalog(JSON.parse(fs.readFileSync(0,'utf8')));process.stdout.write(JSON.stringify({master:c.data,runtime:c.runtime(),restored:c.restoredBundled,migrated:c.migrated,virtual:c.packs.filter(p=>p.id==='single'&&p.practice_virtual).length}));"
r=json.loads(subprocess.run([os.environ.get('NODE_BINARY','node'),'-e',script],input=json.dumps(merged),cwd=ROOT,text=True,capture_output=True,check=True).stdout)
assert r['restored'] and r['migrated'] and r['virtual']==1 and len(r['master']['packs']['packs'])==64 and len(r['runtime']['packs']['packs'])==63
op={k:json.dumps(v,indent=4)+'\n' for k,v in [('masterText',r['master']),('songText',r['runtime']['songs']),('packText',r['runtime']['packs'])]};op.update(bundledRestore=True,virtualPackCount=1);assert m.call('_commit',m.wrap(op))==1
cold=m.value(m.call('_loadMaster'));assert cold==r['master'];assert len({s['idx'] for s in cold['songs']['songs']})==563;assert m.fs['/import/library/songs/local_preserved/3.aff']==b'unchanged resource';assert '/import/full-catalog-restored-r22' in m.fs
# The one-time marker allows later normal deletion; restoration must not undo it.
cold['songs']['songs']=[s for s in cold['songs']['songs'] if s['id']!='lostcivilization'];active=json.loads(m.fs['/import/active.json']);m.fs['/import/catalog/'+active['catalog']+'/ArcLibrary.json']=json.dumps(cold).encode();assert m.value(m.call('_loadMaster'))==cold
result=dict(passed=True,checks=7,bundled_songs=562,bundled_packs=63,manager_virtual_memory_archive=1,cases=['compiled_merge_restores_all_bundled_songs_and_packs','original_private_catalog_backed_up','production_JS_accepts_reserved_Memory_Archive_without_native_duplicate_pack','compiled_commit_and_cold_master_match','imported_ID_and_resource_preserved','presentation_indexes_unique','one_time_marker_preserves_future_deletion'],scope=__doc__,library_sha256=hashlib.sha256((ROOT/'ArcLibrary.dylib').read_bytes()).hexdigest())
(ROOT/'full-catalog-regression.json').write_text(json.dumps(result,indent=2)+'\n');print('Full catalog regression PASS 7; 562 bundled songs / 63 packs')
