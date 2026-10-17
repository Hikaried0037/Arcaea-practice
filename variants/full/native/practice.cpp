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
#include <unordered_set>
#include "../../../native/audio_routes.h"
#include "assets.h"
#include "transport.h"
#include "../../../native/playback_sync.h"
static std::atomic<int> changePitch{1},audioError{0};
static int (*getSystem)(void*,void**),(*createDSP)(void*,int,void**),(*addDSP)(void*,int,void*),(*removeDSP)(void*,void*),(*releaseDSP)(void*),(*setFloat)(void*,int,float),(*setInt)(void*,int,int),(*setBypass)(void*,bool);
struct PitchPair{void* first;void* second;};
static std::unordered_map<void*,PitchPair> pitchEffects;
static void clearEffects(){for(auto& e:pitchEffects){removeDSP(e.first,e.second.first);removeDSP(e.first,e.second.second);releaseDSP(e.second.first);releaseDSP(e.second.second);}pitchEffects.clear();}
static int correctPitch(void* channel,float ratio){
 bool active=!changePitch.load()&&ratio!=1.f;auto it=pitchEffects.find(channel);
 if(active&&it==pitchEffects.end()){
  void* system=nullptr;PitchPair pair{};int result=getSystem(channel,&system);
  if(!result)result=createDSP(system,13,&pair.first);
  if(!result)result=createDSP(system,13,&pair.second);
  if(!result){setInt(pair.first,1,2048);setInt(pair.second,1,2048);result=addDSP(channel,0,pair.first);}
  if(!result)result=addDSP(channel,0,pair.second);
  if(result){if(pair.first){removeDSP(channel,pair.first);releaseDSP(pair.first);}if(pair.second){removeDSP(channel,pair.second);releaseDSP(pair.second);}audioError=result;return result;}
  pitchEffects[channel]=pair;it=pitchEffects.find(channel);
 }
 if(it!=pitchEffects.end()){
  float inverse=1.f/ratio,first=std::min(2.f,std::max(.5f,inverse));
  int r=setFloat(it->second.first,0,first);r|=setFloat(it->second.second,0,inverse/first);
  r|=setBypass(it->second.first,!active);r|=setBypass(it->second.second,!active||inverse==first);audioError=r;return r;
 }
 return 0;
}

// These offsets belong ONLY to Infinity 7.0.1f's ARM64 library.
static uintptr_t base;
static void* scene;
static std::atomic<int> enabled{0}, autoplay{0}, loop{0}, a{0}, b{30000}, command{0};
static std::atomic<float> speed{1};
static std::atomic<bool> fixedFlow{false};
static std::unordered_set<void*> soundingHolds;
static bool buildingScene;
static float sceneFlowRatio=1.f;
struct ArcSegmentState {void* node;float start[3];};
struct ArcGeometryState {void* owner;int lastTime;std::vector<ArcSegmentState> segments;};
static std::unordered_map<void*,ArcGeometryState> arcGeometry;
static std::atomic<int> ready{0}, position{-1}, duration{0}, rounds{0};
static int restartAt=transport::noSeek;
static std::atomic<bool> transitioning{false};
static uint8_t originalNoFail;
static bool scenePracticed;
static bool priming;
static std::atomic<int> pendingSeek{transport::noSeek};
static bool waitingTransport,leadRequested,audioStartPending;
static int warmFrames,audioStable;
static int64_t prepareSince;
static transport::LeadIn leadIn;
static std::atomic<int> countdownRemaining{0};
static int (*setMusicPosition)(void*,uint32_t,uint32_t);
static std::atomic<int> previewing{0},seekRequest{-1};
static std::atomic<int> simulatorActive{0};
static int64_t lastPreviewSeek;
static std::atomic<int> previewRestart{0};
static int timelineCursor=-3000;
static bool previewWasActive;
static int (*pauseChannel)(void*,bool);
static void (*holdVisualOriginal)(void*,int);
static void (*arcVisualOriginal)(void*,int);
static void* lastClock;
static int lastRaw;
static double fraction;
static bool musicSyncing,wasPaused;
static transport::SmoothAudioSync smoothAudioSync;
struct AppliedPitch {void* sound;float value;bool changesPitch;};
static std::unordered_map<void*,AppliedPitch> appliedPitches;
static int64_t lastPitchRefresh;
static float refreshedRatio=-1.f;
static bool refreshedPitchMode;
static int64_t monotonicNs();
static int syncTarget;
static float lastSpeed=1.f;
static transport::OffsetCalibration offsetCalibration;
static void* calibratedClock;
#include "../../../native/audio_cache.h"
template<class T> static T& at(void* p,size_t n){return *reinterpret_cast<T*>(static_cast<char*>(p)+n);}
template<class T> static T fn(uintptr_t n){return reinterpret_cast<T>(base+n);}

static constexpr uintptr_t packClickQueryReturn=0x164ad2c;
#include "packcovers.h"

// Refresh catalogs only while constructing a new selection scene. Never mutate
// pointers owned by an active gameplay or a visible song selection scene.
static std::atomic<bool> catalogDirty{false};
static bool (*selectionInitOriginal)(void*);
static bool selectionInitHook(void* self){
 if(catalogDirty.exchange(false)){
  loadPackCovers();
  void* core=*reinterpret_cast<void**>(*reinterpret_cast<void**>(base+0x1b595c0));
  if(core){void* catalog=at<void*>(core,0x20);if(catalog){
   fn<void(*)(void*)>(0x189af00)(catalog);fn<void(*)(void*)>(0xcce050)(catalog);
   __android_log_print(4,"ArcPractice","live catalog reloaded before selection init");
  }else catalogDirty=true;}else catalogDirty=true;
 }
 return selectionInitOriginal(self);
}
extern "C" JNIEXPORT void JNICALL Java_moe_practice_PracticeOverlay_catalogChanged(JNIEnv*,jclass){catalogDirty=true;}

using ChartFactory=void*(*)(void*,void*,void*,int,int,void*,int,int,float);
static ChartFactory chartOriginal;
static void* chartHook(void* p0,void* p1,void* p2,int p3,int p4,void* p5,int p6,int p7,float highspeed){
 // Native distance calculation preserves note size, billboard and hit effects.
 float adjusted=buildingScene?highspeed/sceneFlowRatio:highspeed;
 if(buildingScene)__android_log_print(4,"ArcPractice","native flow base=%.3f effective=%.3f rate=%.2f",highspeed,adjusted,sceneFlowRatio);
 return chartOriginal(p0,p1,p2,p3,p4,p5,p6,p7,adjusted);
}
static bool (*initOriginal)(void*);
static void (*destroyOriginal)(void*);
static void (*clockOriginal)(void*);
static void (*notesOriginal)(void*);
static void (*finishOriginal)(void*,uint32_t);
static void (*judgementOriginal)(void*,void*);
static int (*pitch)(void*,float);
static int (*getPitch)(void*,float*);
static int (*getMusicPosition)(void*,uint32_t*,uint32_t);
static int (*soundOriginal)(void*,int,int,int,int);
static int soundDiagnostics,audioDiagnosticFrames;
static void (*burstOriginal)(void*,void*,int,void*);
static void (*sustainBurstOriginal)(void*,void*,void*);
static bool suppressBurst(){return priming||simulatorActive||waitingTransport||pendingSeek!=transport::noSeek;}
static void burstHook(void* renderer,void* note,int result,void* point){if(!suppressBurst())burstOriginal(renderer,note,result,point);}
static void sustainBurstHook(void* renderer,void* note,void* point){if(!suppressBurst())sustainBurstOriginal(renderer,note,point);}
static int soundHook(void* manager,int effect,int when,int mode,int flags){
 if(effect<=2&&(priming||simulatorActive||waitingTransport||pendingSeek!=transport::noSeek))return -1;
 int result=soundOriginal(manager,effect,when,mode,flags);
 if(effect<=2&&enabled&&autoplay&&soundDiagnostics++<20)
  __android_log_print(4,"ArcPractice","note sound effect=%d at=%d voice=%d",effect,when,result);
 return result;
}
static int timeOf(void* model){return fn<int(*)(void*)>(0x1634424)(model);}
static bool configuredDeviceOffset(int& value){
 auto slot=reinterpret_cast<void**>(base+0x1b595c0);
 if(!*slot)return false;
 void* core=*reinterpret_cast<void**>(*slot);if(!core)return false;
 void* settings=at<void*>(core,0x70);if(!settings)return false;
 // Same route selection as the verified native GameplayModel constructor.
 int route=at<int>(settings,0);value=at<int>(settings,route==0?4:8);return true;
}
static void updateOffset(void* model,bool fixedTimeline=false){
 void* clock=at<void*>(model,0x30);if(!clock||clock!=calibratedClock)return;
 float rate=enabled?speed.load():1.f;
 int original=0;if(configuredDeviceOffset(original))offsetCalibration.configured(original);
 bool fixed=fixedTimeline||previewing||waitingTransport||leadIn.active||pendingSeek!=transport::noSeek;
 int delta=offsetCalibration.apply(rate,at<int>(clock,0x30),at<int>(clock,0x38),
              at<int>(clock,0x28),at<int>(clock,0x24),at<uint8_t>(clock,0x2e)!=0,
              at<uint8_t>(clock,0x2c)!=0,fixed);
 if(delta){fraction=0;__android_log_print(4,"ArcPractice","offset calibration device=%d aff=%d effective=%d rate=%.2f",offsetCalibration.device,offsetCalibration.chart,at<int>(clock,0x30),rate);}
}
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
 bool ok=getMusicPosition(reinterpret_cast<void*>(begin[1]),&result,1)==0;
 if(ok)result=quality::sourceTime(result,audioCache::channelRate(reinterpret_cast<void*>(begin[1])));return ok;
}
static void musicPitch(float ratio,bool diagnostic=false){
 int64_t now=monotonicNs();bool mode=changePitch.load()!=0;
 bool changed=ratio!=refreshedRatio||mode!=refreshedPitchMode;
 if(!diagnostic&&!changed&&lastPitchRefresh&&now-lastPitchRefresh<250000000LL)return;
 lastPitchRefresh=now;refreshedRatio=ratio;refreshedPitchMode=mode;
 void* provider=audioProvider();
 if(!provider)return;
 auto begin=at<uintptr_t*>(provider,0x38),end=at<uintptr_t*>(provider,0x40);
 if(!begin||end<begin||end-begin>128)return;
 for(auto p=begin;p<end;p+=2)if(p[1]){
  void* channel=reinterpret_cast<void*>(p[1]);
  // The provider retains old preview voices. Do not create effects or report
  // failures for voices which FMOD has already stopped/reused.
  void* currentSound=nullptr;
  if(audioCache::getCurrentSound(channel,&currentSound)!=0||!currentSound){appliedPitches.erase(channel);continue;}
  float storedRate=audioCache::channelRate(channel);
  float wanted=storedRate!=1.f?ratio/storedRate:ratio;
  auto previous=appliedPitches.find(channel);int result=0;
  bool dirty=previous==appliedPitches.end()||previous->second.sound!=currentSound||previous->second.value!=wanted||previous->second.changesPitch!=mode;
  if(!dirty&&getPitch){float actual=0;dirty=getPitch(channel,&actual)!=0||std::abs(actual-wanted)>.0001f;}
  if(dirty){
   result=pitch(channel,wanted);int correction=correctPitch(channel,storedRate!=1.f?1.f:ratio);if(!result)result=correction;
   if(!result)appliedPitches[channel]={currentSound,wanted,mode};
  }
  if(diagnostic){
   float actual=-1;uint32_t music=0;
   int rp=getPitch?getPitch(channel,&actual):-1;
   int rt=getMusicPosition?getMusicPosition(channel,&music,1):-1; // FMOD_TIMEUNIT_MS
   __android_log_print(4,"ArcPractice","music channel=%p set=%d pitch=%.2f get=%d audio_ms=%u position_result=%d chart_ms=%d stored_rate=%.2f",channel,result,actual,rp,music,rt,position.load(),storedRate);
  }
 }
}
static void perfect(void* model,void* note,int when){
 if(priming||simulatorActive)return;
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
   if(!priming&&!waitingTransport&&pendingSeek==transport::noSeek&&now<at<int>(note,0x1c)){
    if(type==0x1ac7630&&soundingHolds.insert(note).second){
     // The native Hold press plays tap.wav and initializes held state.
     fn<void(*)(void*)>(0xe9606c)(note);
     if(soundDiagnostics++<20)__android_log_print(4,"ArcPractice","autoplay hold sound at=%d",now);
    }else if(type==0x1a62438&&at<int>(note,0x68)==-1){
     void* core=*reinterpret_cast<void**>(*reinterpret_cast<void**>(base+0x1b595c0));
     if(core){at<int>(note,0x68)=fn<int(*)(void*,int,int,int,int)>(0xf05fe8)(at<void*>(core,0x10),0,start,0,0);
      if(soundDiagnostics++<20)__android_log_print(4,"ArcPractice","autoplay arc sound at=%d id=%d",now,at<int>(note,0x68));}
    }
   }
   at<uint8_t>(note,0x64)=1;at<uint8_t>(note,0x65)=1;
   // Arc +0xa8 is a FLOAT coordinate, never a judgement flag.
   bool newTick=false;
   for(auto t=ticks;t<stop;t+=12){
    int when=at<int>(t,0);if(when>now)break;
    if(!(at<uint8_t>(t,8)&1)){
     at<uint8_t>(t,8)|=1;
     at<uint8_t>(note,0x66)=1;
     int count=at<int>(t,4);
     newTick|=count>0;
     if(!priming)for(int n=0;n<count&&n<64;++n)fn<void(*)(void*,void*,int,int,int,int)>(0x9d5500)(at<void*>(model,0x38),note,0,0,when,-1);
    }
   }
   // Match native long-note judgement: score all ticks, notify effects once.
   if(newTick&&!priming){void* delegate=at<void*>(model,0x40);if(delegate){auto dv=at<uintptr_t*>(delegate,0);reinterpret_cast<void(*)(void*,void*,int,int)>(dv[1])(delegate,note,0,0);}}
  }
 }
}
static void notesHook(void* model){
 notesOriginal(model);
 if(enabled&&scene&&at<void*>(scene,0x3e0)==model){
  int now=timeOf(model);
  if(!simulatorActive&&(autoplay||now<a.load()))autoNotes(model,now);
 }
}
#include "timeline.h"
static void judgementHook(void* model,void* self){
 if(priming||simulatorActive){if(simulatorActive&&!priming)previewEvents(self,model,timeOf(model));return;}
 judgementOriginal(model,self);
}
static bool initHook(void* self){
 bool practicing=enabled.load();
 bool restarting=restartAt!=transport::noSeek;
 if(practicing)at<int>(self,0x4b4)=1;
 sceneFlowRatio=enabled&&fixedFlow?speed.load():1.f;
 buildingScene=true;bool result=initOriginal(self);buildingScene=false;
 if(result){scene=self;soundingHolds.clear();arcGeometry.clear();soundDiagnostics=0;audioDiagnosticFrames=0;appliedPitches.clear();lastPitchRefresh=0;refreshedRatio=-1.f;smoothAudioSync.reset();transitioning=false;position=-1;lastClock=nullptr;fraction=0;musicSyncing=false;wasPaused=false;lastSpeed=speed.load();
  calibratedClock=nullptr;
  if(void* model=at<void*>(self,0x3e0)){
   void* clock=at<void*>(model,0x30);void* chart=at<void*>(model,0x28);
   if(clock&&chart){
    calibratedClock=clock;int original=0;
    if(configuredDeviceOffset(original))offsetCalibration.captureConfigured(at<int>(clock,0x30),at<int>(chart,0xc4),original);
    else offsetCalibration.capture(at<int>(clock,0x30),at<int>(chart,0xc4));
    updateOffset(model,true);
    __android_log_print(4,"ArcPractice","offset baseline settings=%d aff=%d effective=%d rate=%.2f",offsetCalibration.device,offsetCalibration.chart,at<int>(clock,0x30),enabled?speed.load():1.f);
   }
  }
  if(!restarting){originalNoFail=at<uint8_t>(self,0x34d);scenePracticed=practicing;}
  timelineCursor=-3000;leadIn.active=false;countdownRemaining=0;waitingTransport=false;previewWasActive=false;leadRequested=practicing&&!simulatorActive;
  pendingSeek=previewing?std::max(0,seekRequest.load()):restarting?restartAt:(practicing?transport::leadStart(a.load(),speed.load()):transport::noSeek);
  {void* m=at<void*>(self,0x3e0);if(m){void* chart=at<void*>(m,0x28);if(chart)duration=at<int>(chart,0xbc);cacheTimeline(m);}}if(practicing)at<uint8_t>(self,0x34d)=1;
  __android_log_print(4,"ArcPractice","scene=%p initialized practice=%d start=%d",self,practicing,restartAt);
 }
 restartAt=transport::noSeek;return result;
}
static void destroyHook(void* self){if(scene==self)clearEffects();if(scene==self){soundingHolds.clear();arcGeometry.clear();releaseTimeline();clearEffects();leadIn.active=false;countdownRemaining=0;}__android_log_print(4,"ArcPractice","destroy scene=%p tracked=%p",self,scene);if(scene==self){scene=nullptr;calibratedClock=nullptr;position=-1;lastClock=nullptr;}destroyOriginal(self);}
static void retry(void* self,bool countRound=true){
 if(transitioning)return;
 transitioning=true;restartAt=!countRound&&simulatorActive?std::max(0,timeOf(at<void*>(self,0x3e0))):transport::leadStart(a.load(),speed.load());if(countRound)rounds++;
 __android_log_print(4,"ArcPractice","retry scene=%p target=%d",self,restartAt);
 fn<void(*)(void*,bool)>(0x13020b8)(self,false);
}
static void pauseMusic(bool paused){
 void* provider=audioProvider();if(!provider||!pauseChannel)return;
 auto first=at<uintptr_t*>(provider,0x38),last=at<uintptr_t*>(provider,0x40);
 if(!first||last<first||last-first>128)return;
 for(auto p=first;p<last;p+=2)if(p[1])pauseChannel(reinterpret_cast<void*>(p[1]),paused);
}
static bool consumeVisual(int now){return scene&&enabled&&(priming||simulatorActive||previewing||autoplay||now<a.load());}
static void visible(void* node,bool on){auto vt=at<uintptr_t*>(node,0);reinterpret_cast<void(*)(void*,bool)>(vt[0x150/8])(node,on);}
static void (*arcMarkersOriginal)(void*,void*);
static void arcMarkersHook(void* track,void* notes){
 // Arc head markers live in a separate, persistent layer (+0x348), outside
 // both the Arc mesh and NoteBurstRenderer. The native forward-only updater
 // leaves inactive markers visible until their fade action removes them;
 // scrubbing backwards pauses that fade and can leave old heads on screen.
 // Hide the previous frame's markers first. The original updater explicitly
 // enables and positions every marker belonging to the current active notes.
 if(scene&&enabled&&(priming||simulatorActive||previewing||waitingTransport)){
  void* layer=at<void*>(track,0x348);
  if(layer&&reinterpret_cast<uintptr_t>(at<void*>(layer,0))-base==0x1a7e318){
   void* children=at<void*>(layer,0x140);
   auto first=children?at<void**>(children,0):nullptr,last=children?at<void**>(children,8):nullptr;
   if(first&&last>=first&&last-first<65536)for(auto p=first;p<last;++p)if(*p)visible(*p,false);
   // A marker previously faded out may have been detached while its Arc
   // renderer still has the forward-only "already attached" flag set.
   // Re-arm attachment and cancel that old fade for live notes on rewind.
   auto begin=notes?at<void**>(notes,0):nullptr,end=notes?at<void**>(notes,8):nullptr;
   int now=at<int>(track,0x2e8);
   if(begin&&end>=begin&&end-begin<65536)for(auto p=begin;p<end;++p){
    void* note=*p;if(!note||reinterpret_cast<uintptr_t>(at<void*>(note,0))-base!=0x1a62438||at<uint8_t>(note,0xc)||at<int>(note,0x1c)<now)continue;
    void* render=at<void*>(note,0x40);if(!render)continue;
    void* marker=at<void*>(render,0x2d0);if(!marker)continue;
    fn<void(*)(void*)>(0x1a030f0)(marker); // Node::stopAllActions
    if(at<void*>(marker,0x148)!=layer)at<uint8_t>(render,0x2c8)=0;
   }
  }
 }
 arcMarkersOriginal(track,notes);
}
static void tapVisualHook(void* node,int now){
 void* note=at<void*>(node,0x2a8);bool seeking=priming||simulatorActive;
 if(note&&seeking)visible(node,now<=at<int>(note,0x1c)&&!at<uint8_t>(note,0xc));
 fn<void(*)(void*,int)>(0x13d244c)(node,now);
 if(note&&seeking&&now>at<int>(note,0x1c))visible(node,false);
}
static void holdVisualHook(void* node,int now){
 void* note=at<void*>(node,0x2a8);
 if(note&&(priming||simulatorActive))visible(node,now<=at<int>(note,0x1c)&&!at<uint8_t>(note,0xc));
 if(!note||!consumeVisual(now)||now<at<int>(note,0x18)){holdVisualOriginal(node,now);return;}
 int head=at<int>(note,0x30),tail=at<int>(note,0x34);
 at<int>(note,0x30)=0;
 if(now>=at<int>(note,0x1c))at<int>(note,0x34)=0;
 holdVisualOriginal(node,now);
 at<int>(note,0x30)=head;at<int>(note,0x34)=tail;
}
static void arcVisualHook(void* node,int now){
 void* note=at<void*>(node,0x2a8);
 if(note){
  void* body=at<void*>(node,0x2b8);void* children=body?at<void*>(body,0x140):nullptr;
  auto first=children?at<void**>(children,0):nullptr,last=children?at<void**>(children,8):nullptr;
  if(first&&last>=first&&last-first<100000){
   auto it=arcGeometry.find(note);bool fresh=it==arcGeometry.end()||it->second.owner!=node||it->second.segments.size()!=size_t(last-first);
   if(!fresh)for(size_t i=0;i<it->second.segments.size();++i)if(it->second.segments[i].node!=first[i]){fresh=true;break;}
   // Clipping writes +0x2f4; +0x300 is the unchanged end point.
   if(fresh){ArcGeometryState state{node,now,{}};for(auto p=first;p<last;++p){ArcSegmentState part{*p,{}};memcpy(part.start,static_cast<char*>(*p)+0x2f4,12);state.segments.push_back(part);}it=arcGeometry.insert_or_assign(note,std::move(state)).first;}
   else if(now<it->second.lastTime){for(auto& part:it->second.segments){fn<void(*)(void*,float*)>(0x9d5a08)(part.node,part.start);visible(part.node,true);}visible(node,true);}
   it->second.lastTime=now;
  }
  if(priming||simulatorActive)visible(node,now<=at<int>(note,0x1c)&&!at<uint8_t>(note,0xc));
 }
 arcVisualOriginal(node,now);
 if(!note||!consumeVisual(now)||at<int>(note,0xa4)!=0||now<at<int>(note,0x18))return;
 // The original engine clips individual mesh sections and interpolates the
 // current arc head (+0xd4/+0xd8); moving the whole arc would distort its curve.
 fn<void(*)(void*)>(0x13a000c)(node);
 if(now>=at<int>(note,0x1c)){
  auto vt=at<uintptr_t*>(node,0);
  reinterpret_cast<void(*)(void*,bool)>(vt[0x150/8])(node,false);
 }
}
static bool seekMusic(void* model,int target){
 void* provider=audioProvider();void* clock=at<void*>(model,0x30);if(!provider||!setMusicPosition)return false;
 auto first=at<uintptr_t*>(provider,0x38),last=at<uintptr_t*>(provider,0x40);
 if(!first||last-first<2||last-first>128||!first[1])return false;
 int audio=std::max(0,target-at<int>(clock,0x38));
 audio=quality::outputTime(audio,audioCache::channelRate(reinterpret_cast<void*>(first[1])));
 int result=setMusicPosition(reinterpret_cast<void*>(first[1]),audio,1);audioError=result;
 __android_log_print(4,"ArcPractice","audio seek chart=%d audio=%d result=%d",target,audio,result);
 return result==0;
}
extern "C" JNIEXPORT void JNICALL Java_moe_practice_PracticeOverlay_frame(JNIEnv*,jclass){
 if(ready!=1||!scene||transitioning)return;
 void* self=scene;void* model=at<void*>(self,0x3e0);if(!model)return;
 updateOffset(model);
 bool active=at<uint8_t>(self,0x4c1)!=0;
 if(active&&pendingSeek==transport::noSeek&&!previewing&&!waitingTransport){
  void* provider=audioProvider();
  if(provider){auto first=at<uintptr_t*>(provider,0x38),last=at<uintptr_t*>(provider,0x40);
   if(first&&last-first>=2&&last-first<=128&&first[1]&&audioCache::reload(reinterpret_cast<void*>(first[1]),enabled?speed.load():1.f,changePitch.load()!=0)){retry(self,false);return;}
  }
 }
 float wantedFlow=enabled&&fixedFlow?speed.load():1.f;
 // Regenerate native geometry once for committed flow changes. Scrubbing does
 // not change this value and never restarts the scene.
 if(active&&std::abs(wantedFlow-sceneFlowRatio)>.0001f){retry(self,false);return;}
 if(enabled&&!previewing&&active&&command.exchange(0)==1){retry(self);return;}
 int requested=seekRequest.load();
 if(previewing&&active&&previewRestart.exchange(0)){if(cacheTimeline(model))rewindTimeline(model);pendingSeek=requested;}
 if(previewing&&requested>=0&&active&&requested!=timelineCursor&&monotonicNs()-lastPreviewSeek>=33000000LL)pendingSeek=requested;
 if(pendingSeek!=transport::noSeek&&active){
  pauseMusic(true);
  int target=std::max(-6000,std::min(pendingSeek.load(),std::max(0,duration.load()-1)));
  if(restoreTimeline(self,model,target)){
   pauseMusic(true);if(!previewing)seekMusic(model,target);else lastPreviewSeek=monotonicNs();previewWasActive=true;
   waitingTransport=!previewing;warmFrames=3;audioStable=0;prepareSince=monotonicNs();
  }
 }
 if(previewing){pauseMusic(true);previewWasActive=true;waitingTransport=false;leadIn.active=false;countdownRemaining=0;}
 else if(pendingSeek==transport::noSeek&&previewWasActive){
  if(!waitingTransport){waitingTransport=true;warmFrames=3;audioStable=0;prepareSince=monotonicNs();seekMusic(model,timelineCursor);}
  pauseMusic(true);if(warmFrames>0)--warmFrames;
  void* clock=at<void*>(model,0x30);uint32_t audio=0;int offset=at<int>(clock,0x38);
  bool beforeMusic=timelineCursor<offset;
  bool settled=beforeMusic||(musicPosition(audio)&&std::abs(int64_t(audio)+offset-timelineCursor)<80);
  audioStable=settled?audioStable+1:0;
  if(warmFrames==0&&(audioStable>=3||monotonicNs()-prepareSince>3000000000LL)){
   if(leadRequested){leadIn.begin(timelineCursor,a.load(),monotonicNs());countdownRemaining=3000;}
   audioStartPending=beforeMusic;pauseMusic(beforeMusic);waitingTransport=false;previewWasActive=false;leadRequested=false;
   lastClock=nullptr;fraction=0;syncTarget=timelineCursor;smoothAudioSync.reset();musicSyncing=!leadIn.active;
   __android_log_print(4,"ArcPractice","transport ready target=%d lead_ms=%d",timelineCursor,countdownRemaining.load());
  }
 }
 position=timeOf(model);
 if(audioStartPending&&!previewing&&!waitingTransport){
  void* clock=at<void*>(model,0x30);
  if(position>=at<int>(clock,0x38)){seekMusic(model,position.load());pauseMusic(false);audioStartPending=false;}
 }
 at<uint8_t>(self,0x34d)=enabled?1:originalNoFail;
 if(enabled)scenePracticed=true;
 if(enabled&&!previewing&&!waitingTransport&&!leadIn.active&&pendingSeek==transport::noSeek&&loop&&position>=b.load()&&active){retry(self);return;}
 bool diagnostic=false;
 if(enabled&&!previewing&&!waitingTransport&&!leadIn.active&&pendingSeek==transport::noSeek&&position>=a.load()&&audioDiagnosticFrames<180)diagnostic=(audioDiagnosticFrames++%60)==0;
 musicPitch(enabled?speed.load():1.f,diagnostic);
}
static void finishHook(void* self,uint32_t cleared){
 if(priming||simulatorActive||previewing||waitingTransport||leadIn.active||pendingSeek!=transport::noSeek)return;
 if(scenePracticed&&scene==self){
  if(enabled&&loop)command=1;
  else fn<void(*)(void*,bool,bool)>(0x1890094)(self,true,false);
  return;
 }
 finishOriginal(self,cleared);
}
static void clockHook(void* clock){
 if(priming)return;
 void* model=scene?at<void*>(scene,0x3e0):nullptr;
 bool current=model&&at<void*>(model,0x30)==clock;
 if(current)updateOffset(model);
 clockOriginal(clock);
 if(!enabled||!current)return;
 int raw=at<int>(clock,0x20);
 if((previewing||waitingTransport||pendingSeek!=transport::noSeek)&&at<uint8_t>(clock,0x2d)){at<int>(clock,0x28)=raw-timelineCursor;lastClock=nullptr;fraction=0;return;}
 if(leadIn.active){
  int target=leadIn.sample(monotonicNs(),at<uint8_t>(clock,0x2c)!=0);
  at<int>(clock,0x28)=raw-target;countdownRemaining=leadIn.remaining();
  lastClock=clock;lastRaw=raw;fraction=0;
  if(!leadIn.active){syncTarget=a.load();smoothAudioSync.reset();musicSyncing=true;__android_log_print(4,"ArcPractice","lead complete chart=%d elapsed_ms=%lld",target,(long long)(leadIn.elapsedNs/1000000));}
  return;
 }
 if(at<uint8_t>(clock,0x2c))wasPaused=true;
 if(lastClock!=clock||!at<uint8_t>(clock,0x2e)||at<uint8_t>(clock,0x2c)){lastClock=clock;lastRaw=raw;fraction=0;return;}
 float ratio=speed.load();
 if(wasPaused||lastSpeed!=ratio){syncTarget=timeOf(model);smoothAudioSync.reset();musicSyncing=true;wasPaused=false;lastSpeed=ratio;}
 int delta=raw-lastRaw;lastRaw=raw;
 if(delta>=0&&delta<2000){fraction+=delta*(ratio-1.0);int extra=static_cast<int>(fraction);fraction-=extra;at<int>(clock,0x28)-=extra;}
 // Keep render time continuous across buffered audio reports. Querying and
 // snapping every frame made the first seconds visibly step at high refresh.
 if(musicSyncing&&pendingSeek==transport::noSeek){
  if(smoothAudioSync.due(raw)){
   uint32_t audio=0;bool available=musicPosition(audio);
   int64_t musicTime=int64_t(at<int>(clock,0x38))+audio;
   smoothAudioSync.observe(raw,musicTime,timeOf(model),ratio,available);
  }
  at<int>(clock,0x28)-=smoothAudioSync.advance(raw,ratio);
  if(smoothAudioSync.expired(raw)){
   musicSyncing=false;
   __android_log_print(4,"ArcPractice","smooth music sync complete chart=%d samples=%u",timeOf(model),smoothAudioSync.samples);
  }
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
  {0xd0f184,{0xd10403ff,0xa90a7bfd,0xa90b6ffc,0xa90c67fa}},
  {0xc23328,{0xd10283ff,0xa9067bfd,0xf9003bf7,0xa90857f6}},
  {0x15fa714,{0x6db82beb,0x6d0123e9,0xa9027bfd,0xa9036ffc}},
  {0x13df664,{0xa9ba7bfd,0xa9016ffc,0xa90267fa,0xa9035ff8}},
  {0xa09fc8,{0xa9bd7bfd,0xf9000bf5,0xa9024ff4,0x910003fd}},
  {0xd6fa64,{0xa9bd7bfd,0xf9000bf5,0xa9024ff4,0x910003fd}},
  {0xf87fd4,{0xd10343ff,0x6d0623e9,0xa9077bfd,0xa9086ffc}},
  {0x8bb024,{0xd10183ff,0xa9027bfd,0xa9035ff8,0xa90457f6}},
  {0x1638898,{0xd101c3ff,0x6d0223e9,0xa9037bfd,0xf90023f7}},
  {0x838248,{0xd10303ff,0xfd001bec,0x6d042beb,0x6d0523e9}},
  {0x17aac28,{0xa9be7bfd,0xf9000bf3,0x910003fd,0x39470008}},
  {0x13312c0,{0x3940e008,0x340000a8,0x3900e01f,0xb900341f}}
  ,{0xf21224,{0xfc190fe8,0xa9017bfd,0xa9026ffc,0xa90367fa}}
  ,{0xf05fe8,{0xa9ba7bfd,0xf9000bfb,0xa90267fa,0xa9035ff8}}
  ,{0xd09544,{0xd10283ff,0xfd001be8,0xa9047bfd,0xa9056ffc}}
  ,{0xfe9af4,{0xd10143ff,0xa9017bfd,0xa9025ff8,0xa90357f6}}
  ,{0x83b008,{0xfc1b0fe8,0xa9017bfd,0xa9025ff8,0xa90357f6}}
  ,{0xc1e030,{0xd10283ff,0xa9077bfd,0xa90857f6,0xa9094ff4}}
  ,{0xd5b0b4,{0xd103c3ff,0x6d0923e9,0xa90a7bfd,0xf9005bf9}}
  ,{0x8061fc,{0xd10343ff,0x6d033bef,0x6d0433ed,0x6d052beb}}
 };
 for(const auto& p:expected)if(memcmp(reinterpret_cast<void*>(base+p.offset),p.words,16))return -2;
 void* fmod=dlopen("libfmod.so",RTLD_NOW);pitch=reinterpret_cast<int(*)(void*,float)>(dlsym(fmod,"_ZN4FMOD14ChannelControl8setPitchEf"));
 getPitch=reinterpret_cast<int(*)(void*,float*)>(dlsym(fmod,"_ZN4FMOD14ChannelControl8getPitchEPf"));
 getMusicPosition=reinterpret_cast<int(*)(void*,uint32_t*,uint32_t)>(dlsym(fmod,"_ZN4FMOD7Channel11getPositionEPjj"));
 pauseChannel=reinterpret_cast<int(*)(void*,bool)>(dlsym(fmod,"_ZN4FMOD14ChannelControl9setPausedEb"));
 setMusicPosition=reinterpret_cast<int(*)(void*,uint32_t,uint32_t)>(dlsym(fmod,"_ZN4FMOD7Channel11setPositionEjj"));
 if(!pitch||!pauseChannel||!setMusicPosition)return -4;
 getSystem=reinterpret_cast<decltype(getSystem)>(dlsym(fmod,"_ZN4FMOD14ChannelControl15getSystemObjectEPPNS_6SystemE"));
 createDSP=reinterpret_cast<decltype(createDSP)>(dlsym(fmod,"_ZN4FMOD6System15createDSPByTypeE13FMOD_DSP_TYPEPPNS_3DSPE"));
 addDSP=reinterpret_cast<decltype(addDSP)>(dlsym(fmod,"_ZN4FMOD14ChannelControl6addDSPEiPNS_3DSPE"));
 removeDSP=reinterpret_cast<decltype(removeDSP)>(dlsym(fmod,"_ZN4FMOD14ChannelControl9removeDSPEPNS_3DSPE"));
 releaseDSP=reinterpret_cast<decltype(releaseDSP)>(dlsym(fmod,"_ZN4FMOD3DSP7releaseEv"));
 setFloat=reinterpret_cast<decltype(setFloat)>(dlsym(fmod,"_ZN4FMOD3DSP17setParameterFloatEif"));
 setInt=reinterpret_cast<decltype(setInt)>(dlsym(fmod,"_ZN4FMOD3DSP15setParameterIntEii"));
 setBypass=reinterpret_cast<decltype(setBypass)>(dlsym(fmod,"_ZN4FMOD3DSP9setBypassEb"));
 if(!getSystem||!createDSP||!addDSP||!removeDSP||!releaseDSP||!setFloat||!setInt||!setBypass)return -5;
 if(!audioCache::init(fmod))return -6;
 loadPackCovers();
 bool ok=hook(0xc23328,reinterpret_cast<void*>(packCoverHook),reinterpret_cast<void**>(&packCoverOriginal));
 ok&=hook(0xd0f184,reinterpret_cast<void*>(packSongsHook),reinterpret_cast<void**>(&packSongsOriginal));
 ok&=hook(0x15fa714,reinterpret_cast<void*>(selectionInitHook),reinterpret_cast<void**>(&selectionInitOriginal));
 ok&=hook(0x13df664,reinterpret_cast<void*>(initHook),reinterpret_cast<void**>(&initOriginal));
 ok&=hook(0xa09fc8,reinterpret_cast<void*>(destroyHook),reinterpret_cast<void**>(&destroyOriginal));
 ok&=hook(0xd6fa64,reinterpret_cast<void*>(clockHook),reinterpret_cast<void**>(&clockOriginal));
 ok&=hook(0xf87fd4,reinterpret_cast<void*>(notesHook),reinterpret_cast<void**>(&notesOriginal));
 ok&=hook(0xf21224,reinterpret_cast<void*>(judgementHook),reinterpret_cast<void**>(&judgementOriginal));
 ok&=hook(0xf05fe8,reinterpret_cast<void*>(soundHook),reinterpret_cast<void**>(&soundOriginal));
 ok&=hook(0xd09544,reinterpret_cast<void*>(chartHook),reinterpret_cast<void**>(&chartOriginal));
 ok&=hook(0xfe9af4,reinterpret_cast<void*>(burstHook),reinterpret_cast<void**>(&burstOriginal));
 ok&=hook(0x83b008,reinterpret_cast<void*>(sustainBurstHook),reinterpret_cast<void**>(&sustainBurstOriginal));
 ok&=hook(0xc1e030,reinterpret_cast<void*>(cameraEventHook),reinterpret_cast<void**>(&cameraEventOriginal));
 ok&=hook(0xd5b0b4,reinterpret_cast<void*>(sceneEventHook),reinterpret_cast<void**>(&sceneEventOriginal));
 ok&=hook(0x8bb024,reinterpret_cast<void*>(finishHook),reinterpret_cast<void**>(&finishOriginal));
 ok&=hook(0x1638898,reinterpret_cast<void*>(holdVisualHook),reinterpret_cast<void**>(&holdVisualOriginal));
 ok&=hook(0x838248,reinterpret_cast<void*>(arcVisualHook),reinterpret_cast<void**>(&arcVisualOriginal));
 ok&=hook(0x17aac28,reinterpret_cast<void*>(runActionHook),reinterpret_cast<void**>(&runActionOriginal));
 ok&=hook(0x8061fc,reinterpret_cast<void*>(arcMarkersHook),reinterpret_cast<void**>(&arcMarkersOriginal));
 // This update thunk contains a branch: patch its Tap/ArcTap slots only.
 for(uintptr_t table:{0x1a589b0,0x1a6b568}){
  auto slot=reinterpret_cast<uintptr_t*>(base+table+0x518);
  if(*slot!=base+0x13d244c){ok=false;continue;}
  long page=sysconf(_SC_PAGESIZE);uintptr_t start=reinterpret_cast<uintptr_t>(slot)&~(page-1);
  if(mprotect(reinterpret_cast<void*>(start),page,PROT_READ|PROT_WRITE)==0){*slot=reinterpret_cast<uintptr_t>(tapVisualHook);mprotect(reinterpret_cast<void*>(start),page,PROT_READ);}else ok=false;
 }
 // All ActionInterval step slots point at the same implementation. Patch those
 // read-only slots rather than relocating the branch in its first 16 bytes.
 actionStepOriginal=fn<void(*)(void*,float)>(0x13312c0);
 for(uintptr_t address=0x1a46440;address<0x1b59000;address+=8){
  auto slot=reinterpret_cast<uintptr_t*>(base+address);
  if(*slot==base+0x13312c0){
   long page=sysconf(_SC_PAGESIZE);uintptr_t start=(base+address)&~(page-1);
   if(mprotect(reinterpret_cast<void*>(start),page,PROT_READ|PROT_WRITE)==0){*slot=reinterpret_cast<uintptr_t>(actionStepHook);mprotect(reinterpret_cast<void*>(start),page,PROT_READ);}else ok=false;
  }
 }
 ready=ok?1:-3;__android_log_print(4,"ArcPractice","hooks ready=%d pitch=%p",ready.load(),pitch);return ready;
}
extern "C" JNIEXPORT void JNICALL Java_moe_practice_PracticeOverlay_config(JNIEnv*,jclass,jboolean on,jboolean autoPlay,jboolean looping,jint start,jint end,jfloat ratio){
 if(start<0||end-start<1000||end>3600000||!std::isfinite(ratio)||ratio<.25f||ratio>2.f)return;
 a=start;b=end;speed=ratio;autoplay=autoPlay;loop=looping;enabled=on;
 __android_log_print(4,"ArcPractice","config enabled=%d auto=%d loop=%d A=%d B=%d speed=%.2f",on,autoPlay,looping,start,end,ratio);
}
extern "C" JNIEXPORT void JNICALL Java_moe_practice_PracticeOverlay_replay(JNIEnv*,jclass){command=1;}
extern "C" JNIEXPORT void JNICALL Java_moe_practice_PracticeOverlay_previewMode(JNIEnv*,jclass,jboolean on,jint target){
 if(on){seekRequest=std::max(0,std::min(target,std::max(0,duration.load()-1)));if(!previewing)previewRestart=1;previewing=1;}
 else{previewing=0;seekRequest=-1;}
}
extern "C" JNIEXPORT void JNICALL Java_moe_practice_PracticeOverlay_simulatorMode(JNIEnv*,jclass,jboolean on){simulatorActive=on;}
extern "C" JNIEXPORT void JNICALL Java_moe_practice_PracticeOverlay_pitchMode(JNIEnv*,jclass,jboolean on){changePitch=on;}
extern "C" JNIEXPORT void JNICALL Java_moe_practice_PracticeOverlay_flowMode(JNIEnv*,jclass,jboolean on){fixedFlow=on;}
extern "C" JNIEXPORT jintArray JNICALL Java_moe_practice_PracticeOverlay_status(JNIEnv* env,jclass){
 jint values[]={ready.load(),position.load(),duration.load(),rounds.load(),audioCache::failure.load()?audioCache::failure.load():audioError.load(),previewing.load(),transitioning||waitingTransport||pendingSeek!=transport::noSeek,countdownRemaining.load()};auto out=env->NewIntArray(8);env->SetIntArrayRegion(out,0,8,values);return out;
}
