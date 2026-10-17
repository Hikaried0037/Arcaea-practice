from pathlib import Path
import argparse,json,struct,numpy as np
p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);p.add_argument('--rate',type=float,required=True);p.add_argument('--source-seconds',type=float,required=True);p.add_argument('--sample-rate',type=int,required=True);p.add_argument('--report',type=Path);a=p.parse_args()
data=a.cache.read_bytes();assert data[:4]==b'RIFF' and data[8:12]==b'WAVE';at=12;fmt=None;payload=None
while at+8<=len(data):
 name=data[at:at+4];n=struct.unpack_from('<I',data,at+4)[0];body=data[at+8:at+8+n]
 if name==b'fmt ':fmt=struct.unpack_from('<HHIIHH',body)
 if name==b'data':payload=body
 at+=8+n+(n&1)
assert fmt and payload;kind,ch,hz,_,_,bits=fmt;assert kind==3 and bits==32 and hz==a.sample_rate
pcm=np.frombuffer(payload,'<f4').reshape(-1,ch);expected=round(a.source_seconds*hz/np.float32(a.rate));assert abs(len(pcm)-expected)<=2,(len(pcm),expected,'missing decoded prefix or tail')
# The synthetic fixture has an isolated left-only pulse at 5 source seconds.
# Keep this audio-content check distinct from metadata/duration checks.
first=np.where(abs(pcm[:,0])>.04)[0];assert len(first)
onset=first[0]/hz;error_ms=(onset-5/a.rate)*1000
assert abs(error_ms)<50,(error_ms,'cached audio origin shifted')
report={'result':'passed','sample_rate':hz,'channels':ch,'rate':a.rate,'expected_frames':expected,'actual_frames':len(pcm),'first_source_pulse_seconds':5,'first_cached_pulse_seconds':onset,'onset_error_ms':error_ms,'method':'Actual FMOD-produced cache from generated 42-second fixture; whole PCM duration and first audible pulse','limitations':'Pulse transient shape can change under pitch-preserving processing'}
text=json.dumps(report,indent=2)+'\n';print(text)
if a.report:a.report.write_text(text,encoding='utf-8')
