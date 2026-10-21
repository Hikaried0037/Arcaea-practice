"""Compile audited C objects, then link with the restricted deterministic linker."""
from pathlib import Path
import argparse,subprocess,os
from link_library import build
def main():
 a=argparse.ArgumentParser();a.add_argument('--zig',required=True);o=a.parse_args();r=Path(__file__).resolve().parent
 if os.name=='nt':
  import ctypes
  ctypes.windll.kernel32.SetErrorMode(0x8007)
 env=dict(os.environ);env.setdefault('ZIG_GLOBAL_CACHE_DIR',str(r/'zig-cache'))
 for n in ['library','archive']:
  subprocess.run([o.zig,'cc','-target','aarch64-ios.12.4','-Os','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-c',str(r/(n+'.c')),'-o',str(r/(n+'.o'))],env=env,check=True)
 report=build([r/'library.o',r/'archive.o'],r/'ArcLibrary.dylib');print('Native library built',report['bytes'],report['sha256'])
if __name__=='__main__':main()
