#pragma once
// Both verified providers use libc++ ARM64 vector<pair<string,int>> (32B/item).
namespace scheduledFx {
static void (*scheduleOriginal)(void*,void*);
static void (*seekOriginal)(void*,int,int);
static bool installed;
static void* sourceProvider;
static size_t sourceCount;
static int sourceTimes[100000];
static void schedule(void* provider,void* list){
 float rate=enabled&&(buildingScene||scene)?speed.load():1.f;
 auto first=at<unsigned char*>(list,0),last=at<unsigned char*>(list,8);
 sourceProvider=provider;sourceCount=0;
 if(first&&last>=first&&last-first<=3200000&&(last-first)%32==0){sourceCount=size_t(last-first)/32;for(size_t i=0;i<sourceCount;i++)sourceTimes[i]=at<int>(first+i*32,24);}
 if(first&&last>=first&&last-first<=3200000&&(last-first)%32==0&&rate!=1.f){
  for(auto p=first;p<last;p+=32)at<int>(p,24)=static_cast<int>(std::clamp<double>(std::llround(double(at<int>(p,24))/rate),INT32_MIN,INT32_MAX));
 }
 __android_log_print(4,"ArcPractice","scheduled SFX output rate=%.2f",rate);
 scheduleOriginal(provider,list);
}
static void seek(void* provider,int source,int index){
 auto first=at<uintptr_t*>(provider,0x38),last=at<uintptr_t*>(provider,0x40);
 if(!first||last<first||index<0||size_t(last-first)/2<=size_t(index))return;
 void* channel=reinterpret_cast<void*>(first[index*2+1]);
 float rate=audioCache::playbackRate(channel),cached=audioCache::channelRate(channel);
 struct OutputClock {double previous;OutputClock(double scale):previous(audioCache::providerClockScale){audioCache::providerClockScale=scale;}~OutputClock(){audioCache::providerClockScale=previous;}} units(double(cached)/rate);
 int output=quality::outputTime(std::max(0,source),rate);
 seekOriginal(provider,output,index);
 // Preparing is visual only. Do not let source events in the lead-in play
 // merely because the music group advances through those earlier notes.
 if(index==0&&enabled&&leadRequested&&sourceProvider==provider){
  auto effects=at<unsigned char*>(provider,0x20),end=at<unsigned char*>(provider,0x28);
  int firstPlayable=a.load()+offsetCalibration.combinedAt(rate);
  if(effects&&end>=effects&&size_t(end-effects)==sourceCount*40)
   for(size_t i=0;i<sourceCount;i++)if(sourceTimes[i]<firstPlayable)
    qualityStopOriginal(at<void*>(effects+i*40,32));
 }
 __android_log_print(4,"ArcPractice","provider seek source=%d output=%d rate=%.2f",source,output,rate);
}
static bool install(){
 void* provider=dlopen("libfmodProvider.so",RTLD_NOW);if(!provider)return false;
 void* scheduleTarget=dlsym(provider,"_ZN24AudioProviderFMODAndroid27loadAndScheduleSfxOnMainBGMENSt6__ndk16vectorINS0_4pairINS0_12basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEiEENS6_IS9_EEEE");
 void* seekTarget=dlsym(provider,"_ZN24AudioProviderFMODAndroid14setBGMPositionEii");
 const uint32_t scheduleWords[]={0xd10383ff,0xa9087bfd,0xa9096ffc,0xa90a67fa};
 const uint32_t seekWords[]={0xd102c3ff,0xfd0033e8,0xa9077bfd,0xa9085ff8};
 if(!scheduleTarget||!seekTarget||memcmp(scheduleTarget,scheduleWords,16)||memcmp(seekTarget,seekWords,16))return false;
 installed=hookAt(static_cast<uint8_t*>(scheduleTarget),reinterpret_cast<void*>(schedule),reinterpret_cast<void**>(&scheduleOriginal));
 installed=hookAt(static_cast<uint8_t*>(seekTarget),reinterpret_cast<void*>(seek),reinterpret_cast<void**>(&seekOriginal))&&installed;
 return installed;
}
}
