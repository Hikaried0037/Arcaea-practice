#include "../native/playback_sync.h"
#include <cstdio>
#include <cstdlib>
#define CHECK(x) do{if(!(x)){std::fprintf(stderr,"failed line %d\n",__LINE__);return 1;}}while(0)
int main(){
 int cases=0,oldRepeats144=0,newRepeats144=0,queries144=0;
 for(int fps:{60,90,120,144,165,240})for(float rate:{.25f,.5f,1.f,1.5f,2.f})for(int delay:{-220,-90,0,90,220}){
  int drift=int(std::lround(delay*rate));
  transport::SmoothAudioSync sync;int offset=0,previous=-1000,previousOld=-1000,repeats=0,oldRepeats=0;
  for(int frame=0;frame<=fps*3;frame++){
   int wall=int(std::lround(frame*1000.0/fps));int chart=int(std::floor(wall*double(rate)))+offset;
   int audio=int(std::lround((wall/23)*23*double(rate)))+drift;
   if(sync.due(wall))sync.observe(wall,audio,chart,rate,true);
   int correction=sync.advance(wall,rate);CHECK(std::abs(correction)<=int(std::ceil(1000.0/fps*rate*.08))+1);
   offset+=correction;chart+=correction;
   if(frame){CHECK(chart>=previous);if(chart==previous)repeats++;if(audio==previousOld)oldRepeats++;}
   previous=chart;previousOld=audio;
  }
  CHECK(sync.expired(3000));CHECK(sync.samples<=94);
  CHECK(std::abs(offset-drift)<=std::max<double>(24*rate+35*rate+2, std::abs(drift)-3000*rate*.08+2));
  if(fps==144&&rate==1.f&&drift==0){oldRepeats144=oldRepeats;newRepeats144=repeats;queries144=sync.samples;CHECK(repeats==0);CHECK(oldRepeats>250);}
  // Resume must start a fresh bounded window, without carrying stale drift.
  sync.reset();CHECK(sync.due(50000));sync.observe(50000,900000,100,rate,true);CHECK(sync.pending==0);
  CHECK(sync.advance(50000,rate)==0);CHECK(!sync.due(50001));CHECK(sync.expired(53000));cases++;
 }
 transport::SmoothAudioSync unavailable;for(int ms=0;ms<=3000;ms+=7){if(unavailable.due(ms))unavailable.observe(ms,0,ms,1.f,false);CHECK(unavailable.advance(ms,1.f)==0);}CHECK(unavailable.expired(3000));
 std::printf("{\"passed\":true,\"cases\":%d,\"fps\":[60,90,120,144,165,240],\"quantized_audio_ms\":23,\"at_144hz\":{\"old_repeated_time_frames\":%d,\"new_repeated_time_frames\":%d,\"audio_queries_in_3s\":%d},\"limitations\":\"Synthetic transport test, not physical GPU FPS measurement\"}\n",cases,oldRepeats144,newRepeats144,queries144);
}


