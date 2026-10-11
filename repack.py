"""Repack by copying compressed ZIP records; never decompress 3.7 GB of assets."""
import argparse,copy,struct,zipfile
from pathlib import Path
from rename_package import ORIGINAL_PACKAGE, rename_manifest, rename_resources, validate_package
# APK readers require classic ZIP below 4 GiB. Python defaults to ZIP64 at 2 GiB.
zipfile.ZIP64_LIMIT=0xffffffff
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');p.add_argument('--test',action='store_true');p.add_argument('--package-name',default=ORIGINAL_PACKAGE);args=p.parse_args()
validate_package(args.package_name)
root=Path(__file__).resolve().parent;build=root/'build'
replacements={'classes2.dex':build/'classes2.dex','classes4.dex':build/'dex/classes.dex','lib/arm64-v8a/libarcpractice.so':build/'libarcpractice.so'}
with zipfile.ZipFile(args.source) as src,open(args.source,'rb') as raw,zipfile.ZipFile(args.output,'w',allowZip64=True) as out:
 for info in src.infolist():
  if info.filename in replacements or info.filename.startswith('META-INF/'):continue
  if args.package_name!=ORIGINAL_PACKAGE and info.filename in ('AndroidManifest.xml','resources.arsc'):
   patch=rename_manifest if info.filename=='AndroidManifest.xml' else rename_resources
   data,changes=patch(src.read(info.filename),args.package_name)
   out.writestr(info.filename,data,compress_type=zipfile.ZIP_STORED)
   print(info.filename,changes)
   continue
  if args.test and info.filename.startswith('assets/songs/') and info.filename.endswith('.ogg') and not any('/'+s+'/' in info.filename for s in ['sayonarahatsukoi','grievouslady','testify','pragmatism','fairytale']):
   out.write(root/'support'/'test-silence.ogg',info.filename,compress_type=zipfile.ZIP_STORED)
   continue
  if info.flag_bits&8:raise RuntimeError('Descriptor entries require explicit handling')
  raw.seek(info.header_offset);header=raw.read(30)
  if header[:4]!=b'PK\x03\x04':raise RuntimeError('Invalid local record')
  name,extra=struct.unpack_from('<HH',header,26);length=30+name+extra+info.compress_size
  new=copy.copy(info);new.header_offset=out.fp.tell();out._writecheck(new);out._didModify=True
  raw.seek(info.header_offset)
  while length:
   data=raw.read(min(length,8*1024*1024));out.fp.write(data);length-=len(data)
  out.filelist.append(new);out.NameToInfo[new.filename]=new;out.start_dir=out.fp.tell()
 for name,path in replacements.items():out.write(path,name,compress_type=zipfile.ZIP_STORED)
print(Path(args.output).stat().st_size)
