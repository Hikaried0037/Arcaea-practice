#include "../variants/full/native/transport.h"
#ifndef ARC_TIMING_EMULATED
#include <cstdio>
#endif
#define CHECK(x) do { if(!(x))return __LINE__; } while(false)
extern "C" int offsetRegression(){
 for(int aff:{-350,0,175,1200})for(int device:{-400,-123,0,87,500})
 for(int hundredths=25;hundredths<=200;hundredths++){
  float rate=hundredths/100.f;
  transport::OffsetCalibration offset;offset.capture(aff+device,aff);
  int combined=aff+device,origin=-combined,compensation=8000,pausedTime=20000;
  int correction=offset.apply(rate,combined,origin,compensation,pausedTime,true,false,false);
  CHECK(combined==aff+static_cast<int>(std::lround(device*double(rate))));
  CHECK(origin==-combined);CHECK(compensation==8000+correction);CHECK(pausedTime==20000);
  // At a note's chart time, the wall-time calibration stays the configured
  // device latency (up to one half of a chart millisecond's quantization).
  double latency=(combined-aff)/double(rate);
  CHECK(std::abs(latency-device)<=.5001/rate);
  CHECK(std::abs((combined-aff)-device*double(rate))<=.5001);
  int saved=compensation;
  for(int repeat=0;repeat<50;repeat++)CHECK(offset.apply(rate,combined,origin,compensation,pausedTime,true,false,false)==0);
  CHECK(compensation==saved);
  // A seek keeps the selected chart time, while its corresponding audio seek
  // changes with the calibrated origin. Reapplying must not scale twice.
  int target=30000,audio=target-origin;
  CHECK(audio+origin==target);
  int toNormal=offset.apply(1.f,combined,origin,compensation,pausedTime,true,true,false);
  CHECK(combined==aff+device&&origin==-combined);CHECK(pausedTime==20000-toNormal);
  int held=compensation,heldPause=pausedTime;
  offset.apply(rate,combined,origin,compensation,pausedTime,true,true,true);
  CHECK(compensation==held&&pausedTime==heldPause&&origin==-combined);
  offset.apply(1.f,combined,origin,compensation,pausedTime,true,false,true);
  CHECK(combined==aff+device&&origin==-combined);
  // Startup changes only the offset; the native clock establishes its music
  // origin later. It must not rewrite a stopped/preview clock's cursor.
  offset.capture(aff+device,aff);combined=aff+device;origin=0;compensation=75;pausedTime=125;
  offset.apply(rate,combined,origin,compensation,pausedTime,false,false,false);
  CHECK(origin==0&&compensation==75&&pausedTime==125);
 }
 // A previously scaled/stale combined clock must never become the baseline.
 for(int configured:{-400,-123,0,87,500})for(int aff:{-350,0,175,1200}){
  transport::OffsetCalibration offset;int combined=aff+999,origin=-combined,compensation=8000,paused=30000;
  offset.captureConfigured(combined,aff,configured);
  for(int repeat=0;repeat<3;repeat++)for(int hundredths=25;hundredths<=200;hundredths++){
   float rate=hundredths/100.f;offset.configured(configured);
   offset.apply(rate,combined,origin,compensation,paused,true,true,false);
   CHECK(combined==aff+static_cast<int>(std::lround(double(configured)*rate)));
   CHECK(offset.device==configured&&origin==-combined);
  }
  offset.configured(-configured);offset.apply(.5f,combined,origin,compensation,paused,true,true,false);
  CHECK(combined==aff+static_cast<int>(std::lround(-double(configured)*.5)));
 }
 // The absolute three-second preroll must survive the offset fix unchanged.
 for(float rate:{.25f,.37f,.5f,1.f,1.33f,2.f})for(int target:{0,1000,30000}){
  transport::LeadIn lead;int start=transport::leadStart(target,rate);lead.begin(start,target,1000000000LL);
  CHECK(lead.sample(2500000000LL,false)==start+static_cast<int>(std::lround((target-start)*.5)));
  CHECK(lead.remaining()==1500);
  lead.sample(3500000000LL,true);CHECK(lead.remaining()==1500);
  CHECK(lead.sample(5000000000LL,false)==target&&!lead.active);
 }
 return 0;
}
extern "C" void offsetCapture(void* state,int combined,int aff){static_cast<transport::OffsetCalibration*>(state)->capture(combined,aff);}
extern "C" int offsetApply(void* state,void* nativeClock,float rate,bool fixed){
 auto bytes=static_cast<unsigned char*>(nativeClock);
 auto field=[&](int at)->int&{return *reinterpret_cast<int*>(bytes+at);};
 return static_cast<transport::OffsetCalibration*>(state)->apply(rate,field(0x30),field(0x38),field(0x28),field(0x24),bytes[0x2e],bytes[0x2c],fixed);
}
#ifndef ARC_TIMING_EMULATED
int main(){int result=offsetRegression();if(result)std::printf("FAIL at line %d\n",result);else std::puts("PASS: 3520 offset/rate cases, 10580 configured-baseline checks and 18 absolute lead-in cases");return result;}
#endif
