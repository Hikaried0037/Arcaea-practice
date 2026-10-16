#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
namespace transport {
constexpr int noSeek=std::numeric_limits<int>::min();
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
