from pathlib import Path
import numpy as np,subprocess,json,re
import argparse,tempfile
p=argparse.ArgumentParser();p.add_argument('--renderer',type=Path,required=True);p.add_argument('--report',type=Path);args=p.parse_args()
temporary=tempfile.TemporaryDirectory(prefix='practice-audio-test-');root=Path(temporary.name);hz=48000;duration=12;t=np.arange(hz*duration)/hz
signal=.35*np.sin(2*np.pi*600*t)+.15*np.sin(2*np.pi*18000*t)
stereo=np.column_stack([signal,.8*signal]).astype('<f4');src=root/'synthetic.f32';src.write_bytes(stereo.tobytes());rows=[]
for pitch,rates in [(False,[.25,.37,.5,.75,1.01,1.25,1.5,2.]),(True,[.25,.5,1.5,2.])]:
 for rate in rates:
  out=root/f'test-{rate}-{pitch}.f32';text=subprocess.check_output([str(args.renderer.resolve()),str(src),str(out),str(hz),'2',str(rate),str(int(pitch))],text=True)
  audio=np.fromfile(out,dtype='<f4').reshape(-1,2);expected=round(len(stereo)/np.float32(rate));assert abs(len(audio)-expected)<=2,(rate,len(audio),expected)
  assert np.isfinite(audio).all() and np.abs(audio).max()<1
  stereo_error=float(np.max(abs(audio[:,1]-.8*audio[:,0])))
  # Joint spectral reconstruction has a small numerical/noise-floor residual.
  # Bound it below -60 dBFS and preserve its measured value in the report.
  assert stereo_error<1e-3, (rate,pitch,"stereo relationship changed")
  segment=audio[len(audio)//3:len(audio)//3+hz*2,0];n=len(segment);freq=np.fft.rfftfreq(n,1/hz);spectrum=abs(np.fft.rfft(segment*np.hanning(n)))*4/n
  fundamental=600*rate if pitch else 600;peak=freq[np.argmax(spectrum[(freq>fundamental-15)&(freq<fundamental+15)])+np.where(freq>fundamental-15)[0][0]]
  assert abs(peak-fundamental)<2,(rate,pitch,peak)
  high=18000*rate if pitch else 18000
  highamp=float(np.max(spectrum[(freq>high-30)&(freq<high+30)])) if high<hz/2 else None
  if not pitch:assert highamp>.08,(rate,highamp)
  rows.append(dict(rate=rate,changes_pitch=pitch,output_frames=len(audio),expected_frames=expected,fundamental_hz=float(peak),treble_amplitude=highamp,peak_amplitude=float(abs(audio).max()),stereo_error_peak=stereo_error,processing_seconds=float(re.search('seconds=([0-9.]+)',text)[1])))

# Independent bass and melody detect pitch drift hidden by a single harmonic.
composite=.3*np.sin(2*np.pi*50*t)+.1*np.sin(2*np.pi*437*t)
source=root/'composite.f32';source.write_bytes(np.column_stack([composite,.8*composite]).astype('<f4').tobytes());polyphonic=[]
for rate in [.25,.37,.5,1.33,2.]:
 out=root/'composite-output.f32'
 subprocess.run([str(args.renderer.resolve()),str(source),str(out),str(hz),'2',str(rate),'0'],check=True,capture_output=True)
 audio=np.fromfile(out,dtype='<f4').reshape(-1,2)[:,0];segment=audio[len(audio)//3:len(audio)//3+hz*2];n=len(segment)
 freq=np.fft.rfftfreq(n,1/hz);spectrum=abs(np.fft.rfft(segment*np.hanning(n)))*4/n;tones=[]
 for tone,amplitude in [(50,.3),(437,.1)]:
  band=np.where((freq>tone-10)&(freq<tone+10))[0];peak=band[np.argmax(spectrum[band])]
  assert abs(freq[peak]-tone)<=1 and spectrum[peak]>amplitude*.8,(rate,tone,freq[peak],spectrum[peak])
  tones.append({'source_hz':tone,'output_hz':float(freq[peak]),'amplitude':float(spectrum[peak])})
 polyphonic.append({'rate':rate,'tones':tones})

# Sparse percussion catches the attack loss that a steady sine cannot reveal.
rng=np.random.default_rng(7);pulse=(rng.normal(0,1,720)*np.hanning(720)*.22).astype('<f4')
percussion=np.zeros((hz*6,2),dtype='<f4')
for second in range(1,6):percussion[second*hz:second*hz+720,0]=pulse;percussion[second*hz:second*hz+720,1]=pulse*.8
percussion_path=root/'percussion.f32';percussion_path.write_bytes(percussion.tobytes())
source_attack=np.where(abs(pulse)>.04)[0][0]/hz
transients=[]
for hundredths in range(101,201):
 rate=hundredths/100.;out=root/'percussion-output.f32'
 subprocess.run([str(args.renderer.resolve()),str(percussion_path),str(out),str(hz),'2',str(rate),'0'],check=True,capture_output=True)
 audio=np.fromfile(out,dtype='<f4').reshape(-1,2)[:,0];errors=[]
 for second in range(1,6):
  expected=(second+source_attack)/rate;start=max(0,int((expected-.1)*hz));end=min(len(audio),int((expected+.1)*hz))
  onsets=np.where(abs(audio[start:end])>.04)[0];assert len(onsets),(rate,second,'missing percussion attack')
  errors.append(((start+onsets[0])/hz-expected)*1000)
 assert max(abs(x) for x in errors)<25,(rate,errors)
 transients.append({'rate':rate,'attacks_detected':len(errors),'max_onset_error_ms':round(max(abs(x) for x in errors),4)})
print('PASS: 100 acceleration steps, 500 sparse percussion attacks retained')

print('PASS:',len(rows),'rendered audio cases; pitch, duration, stereo and 18kHz treble verified')
report={'processor':'Signalsmith Stretch 1.3.2 / SoundTouch 2.4.1 native production renderer','sample_rate':hz,'source_seconds':duration,'result':'passed','cases':rows,'polyphonic':polyphonic,'accelerated_transients':transients,'limitations':'Synthetic spectral/duration measurements do not establish perceptual equivalence on all music'}
if args.report:args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
temporary.cleanup()
