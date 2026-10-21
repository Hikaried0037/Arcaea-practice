"""Rebuild and check the exported current iOS source without prior releases."""
from pathlib import Path
import argparse, subprocess, sys, os, zipfile, hashlib, json

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'source'

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--ipa',type=Path,required=True)
    p.add_argument('--zig',required=True)
    p.add_argument('--node',default='node')
    p.add_argument('--ui',action='store_true')
    a=p.parse_args()
    env=dict(os.environ,ORIGINAL_IPA=str(a.ipa.resolve()),NODE_BINARY=a.node,PYTHONUTF8='1')
    runs=[]
    def run(args):
        r=subprocess.run(args,cwd=SRC,env=env,text=True,encoding='utf-8',errors='replace',capture_output=True)
        runs.append({'command':[str(x) for x in args], 'returncode':r.returncode,'output':r.stdout+r.stderr})
        print('PASS' if r.returncode==0 else 'FAIL',Path(str(args[1])).name,flush=True)
        if r.returncode:
            print(r.stdout+r.stderr);raise RuntimeError('check failed')
    try:
        (SRC/'binaries').mkdir(exist_ok=True)
        with zipfile.ZipFile(a.ipa) as z:
            for name in ['Arc-mobile','Frameworks/ArcaeaPractice.dylib']:
                (SRC/'binaries'/Path(name).name).write_bytes(z.read('Payload/Arc-mobile.app/'+name))
            if a.ui:
                (SRC/'Fonts').mkdir(exist_ok=True)
                for name in ['Exo-Regular.ttf','NotoSansCJKsc-Regular.otf']:
                    (SRC/'Fonts'/name).write_bytes(z.read('Payload/Arc-mobile.app/Fonts/'+name))
        run([sys.executable,'build_library.py','--zig',a.zig])
        for name in ['diagnostics','difficulty','previous_difficulty_r18']:
            run([a.zig,'cc','-target','aarch64-ios.12.4','-c',name+'.s','-o',name+'.o'])
        run([a.node,'test_catalog.cjs'])
        for name in ['windows','runloop','native_entry','scan_budget','lifecycle_partner','pause_audio','entry_partner','ui_routing','startup_partner','macho','library_link','dyld_layout','library_entries','difficulty','r18','presentation','migration_r18','backgrounds','bg_dimensions','full_catalog']:
            run([sys.executable,'test_'+name+'.py'])
        if a.ui:
            for name in ['ui_entries','ui']:run([a.node,'test_'+name+'.cjs'])
        report={'passed':True,'runs':runs,'library_sha256':hashlib.sha256((SRC/'ArcLibrary.dylib').read_bytes()).hexdigest(),'scope':'Exported current-source checks on host; historical r12/r13 binaries and private sample-specific test are not included; no device execution.'}
    except Exception:
        report={'passed':False,'runs':runs}
        raise
    finally:
        (SRC/'export-checks-local.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
