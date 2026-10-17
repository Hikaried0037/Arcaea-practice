#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
namespace transport {
// FMOD reports buffered/quantised positions. Snapping the render clock to every
// report makes 144 Hz rendering repeat frames and then jump by an audio block.
// Sample at most once per 32 ms; slew only drift outside one audio-block margin.
struct SmoothAudioSync {
 static constexpr int pollMs=32,windowMs=3000;
 bool started=false;int began=0,nextSample=0,lastFrame=0;
 double pending=0,remainder=0;
 unsigned samples=0;
 void reset(){*this=SmoothAudioSync{};}
 bool due(int wall){
  if(!started||wall<lastFrame){reset();started=true;began=lastFrame=nextSample=wall;}
  return !expired(wall)&&wall>=nextSample;
 }
 bool expired(int wall)const{return started&&int64_t(wall)-began>=windowMs;}
 void observe(int wall,int64_t music,int chart,float rate,bool available){
  nextSample=wall+pollMs;++samples;
  double error=double(music)-chart;
  // Compare a bounded output-time delay in source-time units. A fixed
  // 120-source-ms cutoff rejected legitimate startup buffers at fast rates.
  if(!available||std::abs(error)>std::max(120.0,250.0*rate)){pending=0;return;} // stale async seek
  double margin=24.0*rate;
  pending=error-std::clamp(error,-margin,margin);
 }
 int advance(int wall,float rate){
  double elapsed=std::clamp<int64_t>(int64_t(wall)-lastFrame,0,50);lastFrame=wall;
  double limit=elapsed*rate*.08; // preserve at least 92% of forward motion
  double step=std::clamp(pending,-limit,limit);pending-=step;remainder+=step;
  int correction=static_cast<int>(remainder);remainder-=correction;return correction;
 }
};
}
