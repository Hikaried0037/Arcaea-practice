#include <jni.h>
#include <android/log.h>
#include <dlfcn.h>
#include <link.h>
#include <sys/mman.h>
#include <unistd.h>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <cmath>
#include <algorithm>

// These offsets belong ONLY to Infinity 7.0.1f's ARM64 library.
static uintptr_t base;
static void* scene;
static std::atomic<int> enabled{0}, autoplay{0}, loop{0}, a{0}, b{30000}, command{0};
static std::atomic<float> speed{1};
static std::atomic<int> ready{0}, position{-1}, duration{0}, rounds{0};
static int restartAt=-1;
static bool transitioning;
static uint8_t originalNoFail;
static bool scenePracticed;
static bool priming;
static int pendingSeek=-1;
static void* lastClock;
static int lastRaw;
static double fraction;
static bool musicSyncing,wasPaused;
static int syncTarget;
static float lastSpeed=1.f;
template<class T> static T& at(void* p,size_t n){return *reinterpret_cast<T*>(static_cast<char*>(p)+n);}
template<class T> static T fn(uintptr_t n){return reinterpret_cast<T>(base+n);}
static bool (*initOriginal)(void*);
static void (*destroyOriginal)(void*);
static void (*clockOriginal)(void*);
static void (*notesOriginal)(void*);
static void (*finishOriginal)(void*,uint32_t);
static int (*pitch)(void*,float);
static int (*getPitch)(void*,float*);
static int (*getMusicPosition)(void*,uint32_t*,uint32_t);
static int timeOf(void* model){return fn<int(*)(void*)>(0x1634424)(model);}
static void* audioProvider(){
 auto slot=reinterpret_cast<void**>(base+0x1b595c0);
 void* core=*reinterpret_cast<void**>(*slot);
 if(!core)return nullptr;
 void* manager=at<void*>(core,0x10);
 return manager?at<void*>(manager,0x2c0):nullptr;
}
static bool musicPosition(uint32_t& result){
 void* provider=audioProvider();if(!provider||!getMusicPosition)return false;
 auto begin=at<uintptr_t*>(provider,0x38),end=at<uintptr_t*>(provider,0x40);
 if(!begin||end<begin||end-begin<2||end-begin>128||!begin[1])return false;
 return getMusicPosition(reinterpret_cast<void*>(begin[1]),&result,1)==0;
}
static void musicPitch(float ratio,bool diagnostic=false){
 void* provider=audioProvider();
 if(!provider)return;
 auto begin=at<uintptr_t*>(provider,0x38),end=at<uintptr_t*>(provider,0x40);
 if(!begin||end<begin||end-begin>128)return;
 for(auto p=begin;p<end;p+=2)if(p[1]){
  void* channel=reinterpret_cast<void*>(p[1]);
  int result=pitch(channel,ratio);
  if(diagnostic){
   float actual=-1;uint32_t music=0;
   int rp=getPitch?getPitch(channel,&actual):-1;
   int rt=getMusicPosition?getMusicPosition(channel,&music,1):-1; // FMOD_TIMEUNIT_MS
   __android_log_print(4,"ArcPractice","music channel=%p set=%d pitch=%.2f get=%d audio_ms=%u position_result=%d chart_ms=%d",channel,result,actual,rp,music,rt,position.load());
  }
 }
}
static void perfect(void* model,void* note,int when){
 if(priming)return;
 fn<void(*)(void*,void*,int,int,int,int)>(0x9d5500)(at<void*>(model,0x38),note,0,0,when,-1);
 void* delegate=at<void*>(model,0x40);
 if(delegate){auto vt=at<uintptr_t*>(delegate,0);reinterpret_cast<void(*)(void*,void*,int,int)>(vt[1])(delegate,note,0,0);}
}
static void autoTap(void* model,void* note,int now){
 int start=at<int>(note,0x18);
 if(now<start||at<uint8_t>(note,0xc)||at<uint8_t>(note,0xd))return;
 auto vt=at<uintptr_t*>(note,0);
 if(priming)reinterpret_cast<bool(*)(void*,bool,int)>(vt[7])(note,true,start);
 else reinterpret_cast<bool(*)(void*,int,int)>(vt[4])(note,0,start);
 perfect(model,note,start);
}
static void autoNotes(void* model,int now){
 auto begin=at<void**>(model,0xa0),end=at<void**>(model,0xa8);
 if(!begin||end<begin||end-begin>65536)return;
 for(auto it=begin;it<end;++it){
  void* note=*it;if(!note)continue;
  auto vt=at<uintptr_t*>(note,0);auto type=reinterpret_cast<uintptr_t>(vt)-base;
  if(type==0x1a62438){
   auto taps=at<void**>(note,0x120),tapsEnd=at<void**>(note,0x128);
   if(taps&&tapsEnd>=taps&&tapsEnd-taps<65536)
    for(auto tap=taps;tap<tapsEnd;++tap)if(*tap)autoTap(model,*tap,now);
  }
  int start=at<int>(note,0x18);
  if(now<start||at<uint8_t>(note,0xc))continue;
  if(type==0x1adb188||type==0x1af6cc0){
   autoTap(model,note,now);
  }else if(type==0x1ac7630||type==0x1a62438){
   if(type==0x1a62438&&at<int>(note,0xa4)!=0)continue;
   auto ticks=at<uint8_t*>(note,0x78),stop=at<uint8_t*>(note,0x80);
   if(!ticks||stop<ticks||stop-ticks>1200000)continue;
   at<uint8_t>(note,0x64)=1;at<uint8_t>(note,0x65)=1;
   if(type==0x1a62438)at<uint8_t>(note,0xa8)=1;
   for(auto t=ticks;t<stop;t+=12){
    int when=at<int>(t,0);if(when>now)break;
    if(!(at<uint8_t>(t,8)&1)){
     at<uint8_t>(t,8)|=1;
     int count=at<int>(t,4);
     for(int n=0;n<count&&n<64;++n)perfect(model,note,when);
    }
   }
  }
 }
}
static void notesHook(void* model){
 notesOriginal(model);
 if(enabled&&scene&&at<void*>(scene,0x3e0)==model){
  int now=timeOf(model);
  if(autoplay||now<a.load())autoNotes(model,now);
 }
}
static bool initHook(void* self){
 bool practicing=enabled.load();
 bool restarting=restartAt>=0;
 if(practicing&&(restartAt>=0||a.load()>3000))at<int>(self,0x4b4)=1;
 bool result=initOriginal(self);
 if(result){scene=self;transitioning=false;position=-1;lastClock=nullptr;fraction=0;musicSyncing=false;wasPaused=false;lastSpeed=speed.load();
  if(!restarting){originalNoFail=at<uint8_t>(self,0x34d);scenePracticed=practicing;}
  pendingSeek=restarting?restartAt:(practicing?std::max(0,a.load()-3000):-1);
  if(practicing){at<uint8_t>(self,0x34d)=1;void* m=at<void*>(self,0x3e0);if(m){void* chart=at<void*>(m,0x28);if(chart)duration=at<int>(chart,0xbc);}}
  __android_log_print(4,"ArcPractice","scene=%p initialized practice=%d start=%d",self,practicing,restartAt);
 }
 restartAt=-1;return result;
}
static void destroyHook(void* self){__android_log_print(4,"ArcPractice","destroy scene=%p tracked=%p",self,scene);if(scene==self){scene=nullptr;position=-1;lastClock=nullptr;}destroyOriginal(self);}
static void retry(void* self){
 if(transitioning)return;
 transitioning=true;restartAt=std::max(0,a.load()-3000);rounds++;
 __android_log_print(4,"ArcPractice","retry scene=%p target=%d",self,restartAt);
 fn<void(*)(void*,bool)>(0x13020b8)(self,false);
}
static void restoreTimeline(void* self,void* model,int target){
 void* clock=at<void*>(model,0x30);
 if(!clock||!at<uint8_t>(clock,0x2d))return;
 clockOriginal(clock);
 uint8_t saved[0x40];memcpy(saved,clock,sizeof(saved));
 priming=true;at<uint8_t>(clock,0x2d)=1;at<int>(clock,0x28)=0;
 for(int t=0;t<=target;t+=16){
  at<int>(clock,0x20)=t;
  fn<void(*)(void*,void*)>(0x198bed0)(model,self);
 }
 at<int>(clock,0x20)=target;fn<void(*)(void*,void*)>(0x198bed0)(model,self);
 priming=false;memcpy(clock,saved,sizeof(saved));lastClock=nullptr;fraction=0;
 fn<void(*)(void*,int,int)>(0xb6fb70)(model,target-timeOf(model),1);
 syncTarget=target;musicSyncing=true;
 pendingSeek=-1;
 __android_log_print(4,"ArcPractice","timeline restored target=%d actual=%d",target,timeOf(model));
}
extern "C" JNIEXPORT void JNICALL Java_moe_practice_PracticeOverlay_frame(JNIEnv*,jclass){
 if(ready!=1||!scene||transitioning)return;
 void* self=scene;
 if(scene==self){
  void* model=at<void*>(self,0x3e0);
  if(model){
   if(pendingSeek>=0&&at<uint8_t>(self,0x4c1))restoreTimeline(self,model,std::min(pendingSeek,std::max(0,duration.load()-1000)));
   position=timeOf(model);int cmd=command.exchange(0);
   static int diagnostic=0;
   bool report=++diagnostic%300==0;
   if(report)__android_log_print(4,"ArcPractice","frame scene=%p time=%d active=%d",self,position.load(),at<uint8_t>(self,0x4c1));
   at<uint8_t>(self,0x34d)=enabled?1:originalNoFail;
   if(enabled)scenePracticed=true;
   if(enabled&&(cmd==1||(loop&&position>=b.load()))&&at<uint8_t>(self,0x4c1)){
    retry(self);return;
   }
   musicPitch(enabled?speed.load():1.f,report);
  }
 }
}
static void finishHook(void* self,uint32_t cleared){
 if(scenePracticed&&scene==self){
  if(enabled&&loop)command=1;
  else fn<void(*)(void*,bool,bool)>(0x1890094)(self,true,false);
  return;
 }
 finishOriginal(self,cleared);
}
static void clockHook(void* clock){
 if(priming)return;
 clockOriginal(clock);
 if(!enabled||!scene)return;
 void* model=at<void*>(scene,0x3e0);
 if(!model||at<void*>(model,0x30)!=clock)return;
 int raw=at<int>(clock,0x20);
 if(at<uint8_t>(clock,0x2c))wasPaused=true;
 if(lastClock!=clock||!at<uint8_t>(clock,0x2e)||at<uint8_t>(clock,0x2c)){lastClock=clock;lastRaw=raw;fraction=0;return;}
 float ratio=speed.load();
 if(wasPaused||lastSpeed!=ratio){syncTarget=timeOf(model);musicSyncing=true;wasPaused=false;lastSpeed=ratio;}
 int delta=raw-lastRaw;lastRaw=raw;
 if(delta>=0&&delta<2000){fraction+=delta*(ratio-1.0);int extra=static_cast<int>(fraction);fraction-=extra;at<int>(clock,0x28)-=extra;}
 // Stream seeks complete asynchronously. Keep the chart on the music clock
 // during the first three chart seconds after seeking, resuming or changing rate.
 if(musicSyncing&&pendingSeek<0){
  uint32_t audio=0;int audioOffset=at<int>(clock,0x38);
  int64_t musicTime=static_cast<int64_t>(audioOffset);
  bool available=musicPosition(audio);musicTime+=audio;
  if(available&&musicTime>=syncTarget-1000&&musicTime<=static_cast<int64_t>(syncTarget)+6000){
   at<int>(clock,0x28)=raw-static_cast<int>(musicTime);fraction=0;
   if(musicTime>=syncTarget+3000){musicSyncing=false;__android_log_print(4,"ArcPractice","music synchronized chart=%lld audio=%u speed=%.2f",static_cast<long long>(musicTime),audio,ratio);}
  }else at<int>(clock,0x28)=raw-syncTarget;
 }
}
// Only use on verified, position-independent 16-byte prologues.
static bool hook(uintptr_t offset,void* replacement,void** original){
 auto target=reinterpret_cast<uint8_t*>(base+offset);
 void* trampoline=mmap(nullptr,4096,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
 if(trampoline==MAP_FAILED)return false;
 uint32_t jump[2]={0x58000051,0xd61f0220}; // ldr x17, #8; br x17
 memcpy(trampoline,target,16);memcpy(static_cast<char*>(trampoline)+16,jump,8);
 uintptr_t back=reinterpret_cast<uintptr_t>(target+16);memcpy(static_cast<char*>(trampoline)+24,&back,8);
 __builtin___clear_cache(static_cast<char*>(trampoline),static_cast<char*>(trampoline)+32);
 mprotect(trampoline,4096,PROT_READ|PROT_EXEC);
 long page=sysconf(_SC_PAGESIZE);uintptr_t pageStart=reinterpret_cast<uintptr_t>(target)&~(page-1);
 if(mprotect(reinterpret_cast<void*>(pageStart),page,PROT_READ|PROT_WRITE|PROT_EXEC))return false;
 *original=trampoline;memcpy(target,jump,8);memcpy(target+8,&replacement,8);
 __builtin___clear_cache(reinterpret_cast<char*>(target),reinterpret_cast<char*>(target+16));
 mprotect(reinterpret_cast<void*>(pageStart),page,PROT_READ|PROT_EXEC);return true;
}
static int locate(dl_phdr_info* info,size_t,void*){if(strstr(info->dlpi_name,"libcocos2dcpp.so")){base=info->dlpi_addr;return 1;}return 0;}
extern "C" JNIEXPORT jint JNICALL Java_moe_practice_PracticeOverlay_boot(JNIEnv*,jclass){
 if(ready)return ready;dl_iterate_phdr(locate,nullptr);if(!base)return -1;
 // Refuse another build before modifying executable memory.
 struct Prologue{uintptr_t offset;uint32_t words[4];};
 const Prologue expected[]={
  {0x13df664,{0xa9ba7bfd,0xa9016ffc,0xa90267fa,0xa9035ff8}},
  {0xa09fc8,{0xa9bd7bfd,0xf9000bf5,0xa9024ff4,0x910003fd}},
  {0xd6fa64,{0xa9bd7bfd,0xf9000bf5,0xa9024ff4,0x910003fd}},
  {0xf87fd4,{0xd10343ff,0x6d0623e9,0xa9077bfd,0xa9086ffc}},
  {0x8bb024,{0xd10183ff,0xa9027bfd,0xa9035ff8,0xa90457f6}}
 };
 for(const auto& p:expected)if(memcmp(reinterpret_cast<void*>(base+p.offset),p.words,16))return -2;
 void* fmod=dlopen("libfmod.so",RTLD_NOW);pitch=reinterpret_cast<int(*)(void*,float)>(dlsym(fmod,"_ZN4FMOD14ChannelControl8setPitchEf"));
 getPitch=reinterpret_cast<int(*)(void*,float*)>(dlsym(fmod,"_ZN4FMOD14ChannelControl8getPitchEPf"));
 getMusicPosition=reinterpret_cast<int(*)(void*,uint32_t*,uint32_t)>(dlsym(fmod,"_ZN4FMOD7Channel11getPositionEPjj"));
 if(!pitch)return -4;
 bool ok=hook(0x13df664,reinterpret_cast<void*>(initHook),reinterpret_cast<void**>(&initOriginal));
 ok&=hook(0xa09fc8,reinterpret_cast<void*>(destroyHook),reinterpret_cast<void**>(&destroyOriginal));
 ok&=hook(0xd6fa64,reinterpret_cast<void*>(clockHook),reinterpret_cast<void**>(&clockOriginal));
 ok&=hook(0xf87fd4,reinterpret_cast<void*>(notesHook),reinterpret_cast<void**>(&notesOriginal));
 ok&=hook(0x8bb024,reinterpret_cast<void*>(finishHook),reinterpret_cast<void**>(&finishOriginal));
 ready=ok?1:-3;__android_log_print(4,"ArcPractice","hooks ready=%d pitch=%p",ready.load(),pitch);return ready;
}
extern "C" JNIEXPORT void JNICALL Java_moe_practice_PracticeOverlay_config(JNIEnv*,jclass,jboolean on,jboolean autoPlay,jboolean looping,jint start,jint end,jfloat ratio){
 if(start<0||end-start<1000||end>3600000||!std::isfinite(ratio)||ratio<.25f||ratio>2.f)return;
 a=start;b=end;speed=ratio;autoplay=autoPlay;loop=looping;enabled=on;
 __android_log_print(4,"ArcPractice","config enabled=%d auto=%d loop=%d A=%d B=%d speed=%.2f",on,autoPlay,looping,start,end,ratio);
}
extern "C" JNIEXPORT void JNICALL Java_moe_practice_PracticeOverlay_replay(JNIEnv*,jclass){command=1;}
extern "C" JNIEXPORT jintArray JNICALL Java_moe_practice_PracticeOverlay_status(JNIEnv* env,jclass){
 jint values[]={ready.load(),position.load(),duration.load(),rounds.load()};auto out=env->NewIntArray(4);env->SetIntArrayRegion(out,0,4,values);return out;
}
