"""Generate original synthetic test signals; no game resources are needed."""
import argparse,wave
from pathlib import Path
import numpy as np

def write(path,hz,data):
 with wave.open(str(path),'wb') as out:
  out.setnchannels(2);out.setsampwidth(2);out.setframerate(hz)
  out.writeframes((data*32767).astype('<i2').tobytes())

def main():
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 hz=48000;music=np.zeros((42*hz,2));n=2400;t=np.arange(n)/hz
 for second in range(5,38,2):music[second*hz:second*hz+n,0]=.22*np.sin(2*np.pi*360*t)*np.hanning(n)
 write(a.output/'test-music.wav',hz,music)
 (a.output/'0.aff').write_text('AudioOffset:0\n-\ntiming(0,120.00,4.00);\n'+''.join(f'({second*1000},{i%4+1});\n' for i,second in enumerate(range(5,38,2))),encoding='utf-8')
 hz=44100;n=1323;t=np.arange(n)/hz;click=.3*np.sin(2*np.pi*3800*t)*np.hanning(n)
 write(a.output/'reference-click.wav',hz,np.column_stack([np.zeros(n),click]))
 print('Generated 42-second left-channel music, matching AFF, and right-channel reference click')
if __name__=='__main__':main()
