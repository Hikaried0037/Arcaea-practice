#pragma once
#include "SoundTouch.h"
#include "signalsmith-stretch.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <stdexcept>
#include <vector>
namespace quality {
constexpr unsigned blockFrames=4096;
inline void configure(soundtouch::SoundTouch& engine,int sampleRate,int channels,float rate,bool changesPitch){
 if(sampleRate<8000||sampleRate>192000||channels<1||channels>8||!std::isfinite(rate)||rate<.25f||rate>2.f)throw std::runtime_error("invalid audio format/rate");
 engine.setSampleRate(sampleRate);engine.setChannels(channels);
 engine.setSetting(SETTING_USE_QUICKSEEK,0);
 engine.setSetting(SETTING_USE_AA_FILTER,1);engine.setSetting(SETTING_AA_FILTER_LENGTH,128);
 engine.setRate(rate);
}
inline uint64_t identity(const char* data,uint64_t value=14695981039346656037ULL){for(;*data;++data){value^=static_cast<unsigned char>(*data);value*=1099511628211ULL;}return value;}
inline uint32_t sourceTime(uint32_t processed,float rate){return static_cast<uint32_t>(std::min<double>(UINT32_MAX,std::llround(double(processed)*rate)));}
inline uint32_t outputTime(uint32_t source,float rate){return static_cast<uint32_t>(std::min<double>(UINT32_MAX,std::llround(double(source)/rate)));}
// Decoder supplies source PCM at its native sample rate. Tempo processing runs
// before any output resampling, so 2x pitch-preserving playback retains treble.
// flush() removes the algorithm's queued tail; it is not a live DSP delay.
struct InterleavedView {
 float* samples;int channels;
 struct Channel {float* samples;int stride;float& operator[](int i){return samples[i*stride];}};
 Channel operator[](int channel){return {samples+channel,channels};}
};
// Push-based stages keep memory bounded even when a long track is slowed down.
// Two stages below 0.5x avoid the library's extreme-stretch phase randomisation.
template<class Writer> class SpectralStage {
 signalsmith::stretch::SignalsmithStretch<double> engine{0};
 int channels,seek;float rate;Writer write;
 std::vector<float> initial,output;uint64_t total=0,emitted=0;
 void send(unsigned n){
  for(size_t i=0;i<size_t(n)*channels;i++)if(!std::isfinite(output[i]))throw std::runtime_error("non-finite spectral audio");
  if(n)write(output.data(),n);emitted+=n;
 }
public:
 SpectralStage(int hz,int ch,float speed,Writer writer):channels(ch),rate(speed),write(writer){
  engine.presetDefault(ch,double(hz));seek=engine.outputSeekLength(speed);
  initial.reserve(size_t(seek)*ch);output.resize((size_t(std::ceil(blockFrames/.25))+2)*ch);
 }
 void push(const float* input,unsigned n){
  if(total<uint64_t(seek)){
   unsigned take=std::min<unsigned>(n,unsigned(seek-total));initial.insert(initial.end(),input,input+size_t(take)*channels);
   total+=take;input+=size_t(take)*channels;n-=take;
   if(total<uint64_t(seek))return;
   engine.outputSeek(InterleavedView{initial.data(),channels},seek);
  }
  while(n){
   unsigned count=std::min<unsigned>(n,blockFrames);total+=count;
   uint64_t target=std::llround((total-seek)/double(rate));unsigned generated=unsigned(target-emitted);
   engine.process(InterleavedView{const_cast<float*>(input),channels},count,InterleavedView{output.data(),channels},generated);
   send(generated);input+=size_t(count)*channels;n-=count;
  }
 }
 uint64_t finish(){
  if(total<uint64_t(seek)){
   initial.resize(size_t(seek)*channels,0.f);engine.outputSeek(InterleavedView{initial.data(),channels},seek);
  }
  unsigned tail=unsigned(std::llround(total/double(rate))-emitted);output.resize(size_t(tail)*channels);
  engine.flush(InterleavedView{output.data(),channels},tail,rate);send(tail);return emitted;
 }
};
template<class Reader,class Writer>
uint64_t renderPolyphonic(int sampleRate,int channels,float rate,Reader read,Writer write){
 std::vector<float> input(blockFrames*channels);
 auto pump=[&](auto& stage){unsigned n;while((n=read(input.data(),blockFrames))!=0){if(n>blockFrames)throw std::runtime_error("invalid decoded block");stage.push(input.data(),n);}return stage.finish();};
 if(rate<.5f){
  SpectralStage<Writer> finalStage(sampleRate,channels,.5f,write);
  auto forward=[&](const float* samples,unsigned n){finalStage.push(samples,n);};
  SpectralStage<decltype(forward)> firstStage(sampleRate,channels,rate*2.f,forward);pump(firstStage);
  return finalStage.finish();
 }
 SpectralStage<Writer> stage(sampleRate,channels,rate,write);return pump(stage);
}

template<class Reader,class Writer>
uint64_t render(int sampleRate,int channels,float rate,bool changesPitch,Reader read,Writer write){
 if(sampleRate<8000||sampleRate>192000||channels<1||channels>8||!std::isfinite(rate)||rate<.25f||rate>2.f)throw std::runtime_error("invalid audio format/rate");
 if(!changesPitch){uint64_t frames=0;auto countWrite=[&](const float* samples,unsigned n){write(samples,n);frames+=n;};renderPolyphonic(sampleRate,channels,rate,read,countWrite);return frames;}
 soundtouch::SoundTouch engine;configure(engine,sampleRate,channels,rate,changesPitch);
 std::vector<float> input(blockFrames*channels),output(blockFrames*channels);uint64_t frames=0;
 auto drain=[&](){unsigned count;while((count=engine.receiveSamples(output.data(),blockFrames))!=0){
  for(size_t i=0;i<size_t(count)*channels;i++)if(!std::isfinite(output[i]))throw std::runtime_error("non-finite audio");
  write(output.data(),count);frames+=count;
 }};
 unsigned count;while((count=read(input.data(),blockFrames))!=0){if(count>blockFrames)throw std::runtime_error("invalid decoded block");engine.putSamples(input.data(),count);drain();}
 engine.flush();drain();return frames;
}
inline bool wavHeader(FILE* f,uint64_t frames,int rate,int channels){
 uint64_t bytes=frames*channels*sizeof(float);if(bytes>UINT32_MAX-36)return false;
 unsigned char h[44]={'R','I','F','F',0,0,0,0,'W','A','V','E','f','m','t',' ',16,0,0,0,3,0,0,0,0,0,0,0,0,0,0,0,0,0,32,0,'d','a','t','a',0,0,0,0};
 auto u32=[&](int at,uint32_t v){for(int i=0;i<4;i++)h[at+i]=static_cast<unsigned char>(v>>(8*i));};
 h[22]=static_cast<unsigned char>(channels);u32(4,uint32_t(bytes)+36);u32(24,rate);u32(28,rate*channels*4);h[32]=static_cast<unsigned char>(channels*4);u32(40,uint32_t(bytes));
 return fseek(f,0,SEEK_SET)==0&&fwrite(h,1,sizeof(h),f)==sizeof(h);
}
}
