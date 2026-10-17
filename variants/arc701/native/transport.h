#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
namespace transport {
constexpr int noSeek=std::numeric_limits<int>::min();
// AFF AudioOffset is chart time; the device calibration is real elapsed time.
// Native clocks store their sum. Scale only the device part when music is sped
// up/slowed down, and keep seek/start/synchronization on that same clock origin.
struct OffsetCalibration {
 int chart=0,device=0,applied=0;
 void capture(int combined,int aff){chart=aff;device=combined-aff;applied=combined;}
 // Read the unscaled user calibration from the native settings, never from
 // an already rate-adjusted clock or the AFF header. Keep settings immutable.
 void captureConfigured(int combined,int aff,int configured){chart=aff;device=configured;applied=combined;}
 void configured(int original){device=original;}
 int combinedAt(float rate)const{return chart+static_cast<int>(std::lround(double(device)*rate));}
 int apply(float rate,int& combined,int& audioOrigin,int& compensation,int& pausedTime,
           bool started,bool paused,bool fixedTimeline){
  int wanted=combinedAt(rate),delta=wanted-applied;
  combined=wanted;applied=wanted;
  if(started){
   audioOrigin-=delta;
   if(!fixedTimeline){compensation+=delta;if(paused)pausedTime-=delta;}
  }
  return delta;
 }
};
inline int leadStart(int a,float speed){return a-static_cast<int>(std::lround(3000.0*speed));}
struct LeadIn {
 bool active=false;int start=0,end=0;int64_t lastNs=0,elapsedNs=0;
 void begin(int from,int to,int64_t now){start=from;end=to;lastNs=now;elapsedNs=0;active=true;}
 int sample(int64_t now,bool paused){
  if(!active)return end;
  if(!paused)elapsedNs+=std::max<int64_t>(0,now-lastNs);
  lastNs=now;
  double fraction=std::min(1.0,elapsedNs/3000000000.0);
  int time=start+static_cast<int>(std::lround((end-start)*fraction));
  if(elapsedNs>=3000000000LL)active=false;
  return time;
 }
 int remaining()const{return active?static_cast<int>(std::max<int64_t>(0,3000000000LL-elapsedNs)/1000000):0;}
};
}
