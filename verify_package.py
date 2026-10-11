"""Check the completed package without expanding the song collection."""
import argparse, hashlib, json, struct, zipfile
from pathlib import Path
from rename_package import ORIGINAL_PACKAGE, rename_manifest, rename_resources
p = argparse.ArgumentParser()
p.add_argument('source', type=Path)
p.add_argument('target', type=Path)
p.add_argument('--package-name', default=ORIGINAL_PACKAGE)
args = p.parse_args()
source, target = args.source, args.target
replaced = {'classes2.dex'}
if args.package_name != ORIGINAL_PACKAGE:
    replaced.update(('AndroidManifest.xml', 'resources.arsc'))
def payload_hash(raw, info):
    raw.seek(info.header_offset)
    header = raw.read(30)
    name, extra = struct.unpack_from('<HH', header, 26)
    raw.seek(name + extra, 1)
    h, remaining = hashlib.sha256(), info.compress_size
    while remaining:
        chunk = raw.read(min(remaining, 8 * 1024 * 1024))
        if not chunk:
            raise RuntimeError('Truncated ZIP entry: ' + info.filename)
        h.update(chunk)
        remaining -= len(chunk)
    return h.digest()
with zipfile.ZipFile(source) as a, zipfile.ZipFile(target) as b, source.open('rb') as ra, target.open('rb') as rb:
    preserved = 0
    for n in a.infolist():
        if n.filename.startswith('META-INF/') or n.filename in replaced:
            continue
        m = b.getinfo(n.filename)
        assert (n.CRC, n.file_size) == (m.CRC, m.file_size), n.filename
        assert n.compress_type == m.compress_type, n.filename
        assert payload_hash(ra, n) == payload_hash(rb, m), n.filename
        preserved += 1
    for name, local in [('classes4.dex', 'build/dex/classes.dex'),
                        ('classes2.dex', 'build/classes2.dex'),
                        ('lib/arm64-v8a/libarcpractice.so', 'build/libarcpractice.so')]:
        assert b.read(name) == (Path(__file__).parent / local).read_bytes(), name
    if args.package_name != ORIGINAL_PACKAGE:
        assert b.read('AndroidManifest.xml') == rename_manifest(a.read('AndroidManifest.xml'), args.package_name)[0]
        assert b.read('resources.arsc') == rename_resources(a.read('resources.arsc'), args.package_name)[0]
    assert len(b.namelist()) == len(set(b.namelist())), 'Duplicate ZIP entries'
report = {'original': str(source), 'package': str(target), 'application_id': args.package_name, 'preserved_entries': preserved,
          'all_original_assets_preserved': True, 'compressed_payloads_sha256_match': True,
          'injected_files_match_build': True,
          'size': target.stat().st_size,
          'sha256': hashlib.file_digest(target.open('rb'), 'sha256').hexdigest()}
dest = target.parent / ('package-verification.json' if args.package_name == ORIGINAL_PACKAGE else 'standalone-package-verification.json')
dest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
