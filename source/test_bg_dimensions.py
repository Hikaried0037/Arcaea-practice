"""Native 1920x1440 background preservation, legacy normalization and source-only restoration. UIKit pixel rendering is modeled, dimensions and control flow execute under ARM64."""
from pathlib import Path
import io,json,hashlib,struct
from PIL import Image
from test_backgrounds import Background,basic,pack,commit,jpeg,ROOT
checks=[]
# Preserve a valid canonical source byte for byte; do not crop or re-encode.
n=Background();raw=jpeg((1920,1440));p=n.call('_backgroundJPEG',n.wrap(raw));assert n.value(p)==raw;checks.append('canonical_1920x1440_JPEG_bit_identical_no_crop')
for size in [(1920,1080),(2560,1440),(1440,1920),(1024,768)]:
 q=Background();out=q.value(q.call('_backgroundJPEG',q.wrap(jpeg(size))));assert Image.open(io.BytesIO(out)).size==(1920,1440)
 checks.append('noncanonical_'+str(size)+'_fills_native_canvas')
# Simulate a complete r20 library with an already committed duplicate chart.
n=Background();f=basic();f['new_bg.jpg']=raw;p=n.value(n.call('_prepare',n.wrap(pack(f))));data=commit(n,p);active=n.fs['/import/active.json'];master=n.value(n.call('_loadMaster'));old=jpeg((1920,1080));canonical='/import/library/img/bg/1080/new_bg.jpg';generic='/import/library/img/bg/new_bg.jpg';n.fs[canonical]=old;n.fs[generic]=old
snapshot=n.value(n.call('_snapshot'));assert snapshot['backgroundsRepaired']==1
assert Image.open(io.BytesIO(n.fs[canonical])).size==(1920,1440);assert n.fs['/import/background-backup-r20/new_bg.jpg']==old;assert n.fs['/import/active.json']==active;assert n.call('_migrateBackgrounds')==0;checks.append('old_private_1080_background_normalized_once_backup_retained_catalog_unchanged')
# Original source in the same archive repairs only the background, never adds a song.
p=n.value(n.call('_prepare',n.wrap(pack(f))));assert p['type']=='backgroundRepair' and p['newBackgrounds']==['new_bg'];assert n.call('_repairBackgrounds',n.wrap({'stage':'expired'}))==0;assert n.fs[canonical]!=raw
assert n.call('_repairBackgrounds',n.wrap({'stage':p['id']}))==1;assert n.fs[canonical]==raw and n.fs[generic]==raw;assert n.fs['/import/active.json']==active and n.value(n.call('_loadMaster'))==master
assert '/import/background-restored-r21/new_bg' in n.fs;assert not n.call('_prepare',n.wrap(pack(f)));checks.append('duplicate_archive_restores_original_full_image_without_duplicate_song_and_then_blocks_repeat')
# Built-in backgrounds are always left untouched, including a matching old-size file.
q=Background();q.fs['/app/img/bg/1080/new_bg.jpg']=raw;q.fs[canonical]=old;assert q.call('_migrateBackgrounds')==0 and q.fs[canonical]==old;checks.append('builtin_named_background_excluded_from_migration')
# Failure does not mark source as restored and can be retried safely.
n=Background();f=basic();f['new_bg.jpg']=raw;p=n.value(n.call('_prepare',n.wrap(pack(f))));commit(n,p);n.fs[canonical]=old;n.fs[generic]=old;n.call('_migrateBackgrounds');p=n.value(n.call('_prepare',n.wrap(pack(f))));n.fail_write=canonical
assert not n.call('_repairBackgrounds',n.wrap({'stage':p['id']}));assert '/import/background-restored-r21/new_bg' not in n.fs;n.fail_write=None;assert n.call('_repairBackgrounds',n.wrap({'stage':p['id']}));assert n.fs[canonical]==raw;checks.append('source_restoration_write_failure_retry_and_marker_order')
result=dict(passed=True,checks=len(checks),cases=checks,scope=__doc__,library_sha256=hashlib.sha256((ROOT/'ArcLibrary.dylib').read_bytes()).hexdigest())
(ROOT/'background-dimensions-regression.json').write_text(json.dumps(result,indent=2)+'\n');print('Native background dimensions regression PASS',len(checks))
