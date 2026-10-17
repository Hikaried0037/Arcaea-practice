"""Initial plugin injection for the exact user-supplied Arc701 7.0.1c shell."""
import argparse,hashlib,json,re,subprocess,sys,zipfile
from pathlib import Path
import xml.etree.ElementTree as E
from android_package import rename_resources

ROOT=Path(__file__).resolve().parent
ORIGINAL='moe.low.Arc701'
PACKAGE=ORIGINAL+'.practice'
GAME_SHA='fa7ab65059ae2639a54b2daf37c0cd2d2084f620c2c322e8252f740e713fc6a1'

def patch(decoded):
 ns='{http://schemas.android.com/apk/res/android}';E.register_namespace('android',ns[1:-1]);p=decoded/'AndroidManifest.xml';tree=E.parse(p);root=tree.getroot()
 assert root.get('package')==ORIGINAL
 for node in root.iter():
  for key,value in list(node.attrib.items()):
   if value==ORIGINAL or value.startswith(ORIGINAL+'.'):node.set(key,PACKAGE+value[len(ORIGINAL):])
 root.set('package',PACKAGE)
 app=root.find('application');activity=next(x for x in app.findall('activity') if x.get(ns+'name')=='low.moe.AppActivity')
 bootstrap=E.Element('activity',{ns+'name':'moe.practice.ExternalBootstrap',ns+'screenOrientation':'sensorLandscape',ns+'theme':'@style/AppTheme',ns+'exported':'true'})
 filters=[x for x in activity.findall('intent-filter') if any(y.get(ns+'name')=='android.intent.action.MAIN' for y in x.findall('action'))]
 assert len(filters)==1
 activity.remove(filters[0]);bootstrap.append(filters[0]);app.append(bootstrap);tree.write(p,encoding='utf-8',xml_declaration=True)
 p=decoded/'smali_classes2/low/moe/AppActivity.smali';s=p.read_text(encoding='utf-8');needle='    invoke-static {p0}, Lorg/fmod/FMOD;->init(Landroid/content/Context;)V';assert s.count(needle)==1
 s=s.replace(needle,needle+'\n\n    invoke-static {p0}, Lmoe/practice/PracticeOverlay;->attach(Landroid/app/Activity;)V').replace('"moe.low.arc.provider"','"'+PACKAGE+'.provider"').replace('"'+ORIGINAL+'.provider"','"'+PACKAGE+'.provider"');p.write_text(s,encoding='utf-8')
 p=decoded/'smali_classes2/org/cocos2dx/lib/Cocos2dxRenderer.smali';s=p.read_text(encoding='utf-8');needle='    invoke-static {}, Lorg/cocos2dx/lib/Cocos2dxRenderer;->nativeRender()V';assert s.count(needle)==2
 p.write_text(s.replace(needle,'    invoke-static {}, Lmoe/practice/PracticeOverlay;->frame()V\n\n'+needle),encoding='utf-8')
 for p in (decoded/'smali_classes2').rglob('BuildConfig.smali'):
  s=p.read_text(encoding='utf-8')
  if p.as_posix().endswith('/moe/low/arcdev/BuildConfig.smali'):
   s,count=re.subn(r'(APPLICATION_ID:Ljava/lang/String; = )"[^"]+"',lambda m:m[1]+'"'+PACKAGE+'"',s);assert count==1;p.write_text(s,encoding='utf-8')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base-apk',type=Path,required=True);p.add_argument('--apktool',type=Path,required=True);p.add_argument('--java-home',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a,options=p.parse_known_args()
 if any(x in options for x in ['--variant','--base-apk','--compile-only']):p.error('These options are controlled by the initial injector')
 with zipfile.ZipFile(a.base_apk) as z:assert hashlib.sha256(z.read('lib/arm64-v8a/libcocos2dcpp.so')).hexdigest()==GAME_SHA
 work=a.output.resolve()/'initial-arc701';work.mkdir(parents=True,exist_ok=True);decoded=work/'decoded';framework=work/'framework';java=a.java_home/'bin'/('java.exe' if sys.platform=='win32' else 'java')
 def run(*cmd):subprocess.run([str(x) for x in cmd],check=True)
 run(java,'-jar',a.apktool,'d','-f','--no-assets','-p',framework,'-o',decoded,a.base_apk)
 patch(decoded);patched=work/'bootstrap.apk';run(java,'-jar',a.apktool,'b','-p',framework,'-o',patched,decoded)
 base=work/'injected-base.apk'
 with zipfile.ZipFile(a.base_apk) as before,zipfile.ZipFile(patched) as after,zipfile.ZipFile(base,'w') as out:
  replacements={'AndroidManifest.xml':after.read('AndroidManifest.xml'),'resources.arsc':rename_resources(before.read('resources.arsc'),PACKAGE,ORIGINAL)[0],'classes2.dex':after.read('classes2.dex'),'classes3.dex':before.read('classes2.dex')}
  # classes3 is a build-only placeholder, always replaced before signing.
  for entry in before.infolist():
   if entry.filename in replacements or entry.filename.startswith('META-INF/'):continue
   out.writestr(entry,before.read(entry))
  for name,data in replacements.items():out.writestr(name,data,compress_type=zipfile.ZIP_STORED)
 run(sys.executable,ROOT/'build.py','--variant','arc701','--base-apk',base,'--java-home',a.java_home,'--output',a.output,*options)
 final=a.output/'arc701/Arcaea-Practice-arc701.apk'
 with zipfile.ZipFile(a.base_apk) as before,zipfile.ZipFile(final) as after:
  preserved=0
  for entry in before.infolist():
   if entry.filename in replacements or entry.filename.startswith('META-INF/'):continue
   other=after.getinfo(entry.filename);assert (entry.CRC,entry.file_size)==(other.CRC,other.file_size);preserved+=1
 report=a.output/'arc701/verification.json';d=json.loads(report.read_text());d.update(initial_injection=True,original_apk_sha256=hashlib.sha256(a.base_apk.read_bytes()).hexdigest(),original_entries_preserved=preserved,package=PACKAGE,external_root='/storage/emulated/0/Arc701/')
 report.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');print('Arc701 initial injection and original-entry validation completed')
if __name__=='__main__':main()
