#include <unordered_set>
#include <time.h>
static int64_t monotonicNs(){timespec t{};clock_gettime(CLOCK_MONOTONIC,&t);return int64_t(t.tv_sec)*1000000000LL+t.tv_nsec;}
static std::vector<void*> sourceNotes,eventNotes;
static void* sourceModel;
static int restoredAt=-3000;
static uint8_t modelEffectBaseline[0x28];
static std::vector<std::pair<void*,uint8_t>> groupBaseline;
struct ReplayedAction{void* node;void* action;};
static std::vector<ReplayedAction> replayedActions;
static std::unordered_set<void*> frozenActions;
static bool capturingActions;
static void (*cameraEventOriginal)(void*,void*);
static void (*sceneEventOriginal)(void*,void*);
static void cameraEventHook(void* handler,void* event){
 bool before=capturingActions;if(scene&&handler==at<void*>(scene,0x300))capturingActions=true;
 cameraEventOriginal(handler,event);capturingActions=before;
}
static void sceneEventHook(void* handler,void* event){
 bool before=capturingActions;if(scene&&handler==at<void*>(scene,0x300))capturingActions=true;
 sceneEventOriginal(handler,event);capturingActions=before;
}
static void clearTransientVisuals(void* self){
 void* track=at<void*>(self,0x3b0);
 if(track){void* bursts=at<void*>(track,0x320);
  if(bursts&&reinterpret_cast<uintptr_t>(at<void*>(bursts,0))-base==0x1882d48){
   auto vt=at<uintptr_t*>(bursts,0);reinterpret_cast<void(*)(void*,bool)>(vt[0x280/8])(bursts,true);
  }
  // Force geometry updates even if the clock was repositioned within a frame.
  at<int>(track,0x3c4)=-1;
 }
 at<int>(self,0x4d0)=-1;
}
static void* (*runActionOriginal)(void*,void*);
static void (*actionStepOriginal)(void*,float);
static void releaseTimeline(){
 for(auto& p:replayedActions){fn<void(*)(void*)>(0xc5fac4)(p.action);fn<void(*)(void*)>(0xc5fac4)(p.node);}
 replayedActions.clear();frozenActions.clear();
 for(void* note:sourceNotes)fn<void(*)(void*)>(0xc5fac4)(note);
 sourceNotes.clear();eventNotes.clear();sourceModel=nullptr;restoredAt=-3000;
 groupBaseline.clear();
}
static void actionStepHook(void* action,float dt){
 if(!priming&&(previewing||waitingTransport)&&frozenActions.count(action))return;
 actionStepOriginal(action,dt);
}
static void* runActionHook(void* node,void* action){
 void* result=runActionOriginal(node,action);
 if(capturingActions&&result){
  fn<void(*)(void*)>(0x7b91e0)(node);fn<void(*)(void*)>(0x7b91e0)(result);
  replayedActions.push_back({node,result});frozenActions.insert(result);
  auto vt=at<uintptr_t*>(result,0);
  if(priming)reinterpret_cast<void(*)(void*,float)>(vt[0x40/8])(result,0.f);
 }
 return result;
}
static void advanceEffects(float seconds){
 if(seconds<=0)return;
 size_t count=replayedActions.size();
 for(size_t i=0;i<count;i++){
  void* action=replayedActions[i].action;
  if(!at<void*>(action,0x20))continue; // stopped/replaced actions have no target
  auto vt=at<uintptr_t*>(action,0);
  reinterpret_cast<void(*)(void*,float)>(vt[0x40/8])(action,seconds);
  if(reinterpret_cast<bool(*)(void*)>(vt[0x28/8])(action))reinterpret_cast<void(*)(void*)>(vt[0x38/8])(action);
 }
}
static bool cacheTimeline(void* model){
 if(sourceModel==model)return !sourceNotes.empty();
 releaseTimeline();std::unordered_set<void*> unique;
 auto groups=at<void**>(model,0x88),groupsEnd=at<void**>(model,0x90);
 if(!groups||groupsEnd<groups||groupsEnd-groups>4096)return false;
 for(auto g=groups;g<groupsEnd;++g){
  if(!*g)continue;
  std::vector<void*> stack;void* root=at<void*>(*g,8);if(root)stack.push_back(root);size_t visited=0;
  while(!stack.empty()&&++visited<100000){
   void* bucket=stack.back();stack.pop_back();
   if(void* left=at<void*>(bucket,0))stack.push_back(left);
   if(void* right=at<void*>(bucket,8))stack.push_back(right);
   auto notes=at<void**>(bucket,0x28),end=at<void**>(bucket,0x30);
   if(!notes||end<notes||end-notes>65536)continue;
   for(auto n=notes;n<end;++n)if(*n&&unique.insert(*n).second){
    fn<void(*)(void*)>(0x7b91e0)(*n);sourceNotes.push_back(*n);
    uintptr_t type=reinterpret_cast<uintptr_t>(at<void*>(*n,0))-base;
    if(type==0x18daf40||type==0x1927cc8)eventNotes.push_back(*n);
   }
  }
 }
 std::stable_sort(eventNotes.begin(),eventNotes.end(),[](void* x,void* y){return at<int>(x,0x18)<at<int>(y,0x18);});
 if(sourceNotes.empty())return false;
 sourceModel=model;
 memcpy(modelEffectBaseline,static_cast<char*>(model)+0x54,sizeof(modelEffectBaseline));
 void* chart=at<void*>(model,0x28);
 if(chart){auto groups=at<void**>(chart,0x50),end=at<void**>(chart,0x58);if(groups&&end>=groups&&end-groups<=4096)for(auto g=groups;g<end;g++)if(*g)groupBaseline.push_back({*g,at<uint8_t>(*g,0)});}
 __android_log_print(4,"ArcPractice","timeline indexed notes=%zu effects=%zu",sourceNotes.size(),eventNotes.size());
 return !sourceNotes.empty();
}
static void rewindActionTree(void* action,int depth=0){
 if(!action||depth>16)return;
 auto vt=at<uintptr_t*>(action,0);void* typeInfo=reinterpret_cast<void*>(vt[-1]);
 const char* name=at<const char*>(typeInfo,8);
 if(strstr(name,"Ease")||strstr(name,"RepeatForever")){rewindActionTree(at<void*>(action,0x40),depth+1);return;}
 if(strstr(name,"Sequence")||strstr(name,"Spawn")){rewindActionTree(at<void*>(action,0x48),depth+1);rewindActionTree(at<void*>(action,0x40),depth+1);return;}
 // Instant callbacks are not reversible transforms. Never invoke them while
 // seeking, and do not initialize sequence children which have not run yet.
 if(strstr(name,"CallFunc")||strstr(name,"DelayTime")||!at<void*>(action,0x18))return;
 // Never rewind an instantaneous Show/Hide/RemoveSelf or an unknown callback
 // by invoking it. Only continuous property animations have a safe t=0 state.
 if(!strstr(name,"Move")&&!strstr(name,"Rotate")&&!strstr(name,"Scale")&&!strstr(name,"Fade")&&!strstr(name,"Tint")&&!strstr(name,"Skew")&&!strstr(name,"Bezier")&&!strstr(name,"Jump"))return;
 at<void*>(action,0x20)=at<void*>(action,0x18);
 reinterpret_cast<void(*)(void*,float)>(vt[0x48/8])(action,0.f);
}
static void rewindTimeline(void* model){
 soundingHolds.clear();
 // Rewind effects without replacing the scene or decoding the music again.
 for(auto it=replayedActions.rbegin();it!=replayedActions.rend();++it){
  auto vt=at<uintptr_t*>(it->action,0);
  rewindActionTree(it->action);
  fn<void(*)(void*,void*)>(0x12fb468)(at<void*>(it->node,0x1b0),it->action);
  reinterpret_cast<void(*)(void*)>(vt[0x38/8])(it->action);
  fn<void(*)(void*)>(0xc5fac4)(it->action);fn<void(*)(void*)>(0xc5fac4)(it->node);
 }
 replayedActions.clear();frozenActions.clear();
 memcpy(static_cast<char*>(model)+0x54,modelEffectBaseline,sizeof(modelEffectBaseline));
 for(auto& g:groupBaseline)at<uint8_t>(g.first,0)=g.second;
 for(void* note:sourceNotes){
  at<uint8_t>(note,0xc)=0;at<uint8_t>(note,0xd)=0;at<int>(note,0x10)=-1;
  uintptr_t type=reinterpret_cast<uintptr_t>(at<void*>(note,0))-base;
  if(type==0x1918058||type==0x190aba0){
   at<uint8_t>(note,0x99)=0;at<uint8_t>(note,0x64)=0;at<uint8_t>(note,0x65)=0;at<uint8_t>(note,0x66)=0;
   if(type==0x1918058)at<uint8_t>(note,0xdc)=0;
   auto ticks=at<uint8_t*>(note,0x78),end=at<uint8_t*>(note,0x80);
   if(ticks&&end>=ticks&&end-ticks<1200000)for(auto p=ticks;p<end;p+=12)at<uint8_t>(p,8)=0;
   if(type==0x1918058){auto taps=at<void**>(note,0x120),end=at<void**>(note,0x128);if(taps&&end>=taps&&end-taps<65536)for(auto p=taps;p<end;p++)if(*p){at<uint8_t>(*p,0xc)=0;at<uint8_t>(*p,0xd)=0;}}
  }
 }
 restoredAt=-3000;
}
static void previewEvents(void* self,void* model,int now){
 if(!cacheTimeline(model))return;
 void* handler=at<void*>(self,0x300);if(!handler)return;
 capturingActions=true;
 for(void* event:eventNotes){int when=at<int>(event,0x18);if(when>now)break;if(at<uint8_t>(event,0xd)||at<uint8_t>(event,0xc))continue;
  uintptr_t type=reinterpret_cast<uintptr_t>(at<void*>(event,0))-base;
  fn<void(*)(void*,void*)>(type==0x18daf40?0x109a42c:0xc60578)(handler,event);
  at<uint8_t>(event,0xd)=1;at<int>(event,0x10)=when;
 }
 capturingActions=false;restoredAt=now;
}
static void timelineTime(void* clock,int time){at<int>(clock,0x20)=time;at<int>(clock,0x28)=0;at<int>(reinterpret_cast<void*>(base),0x19c6590)=time;}
static void prepareNote(void* note,int target){
 uintptr_t type=reinterpret_cast<uintptr_t>(at<void*>(note,0))-base;
 if(type==0x18daf40||type==0x1927cc8)return;
 if(at<int>(note,0x1c)<target){at<uint8_t>(note,0xc)=1;return;}
 if(type==0x1918058){
  auto taps=at<void**>(note,0x120),end=at<void**>(note,0x128);
  if(taps&&end>=taps&&end-taps<65536)for(auto p=taps;p<end;++p)if(*p&&at<int>(*p,0x18)<target)at<uint8_t>(*p,0xc)=1;
 }
 if(type==0x1918058||type==0x190aba0){
  auto ticks=at<uint8_t*>(note,0x78),end=at<uint8_t*>(note,0x80);
  if(ticks&&end>=ticks&&end-ticks<1200000)for(auto p=ticks;p<end;p+=12)if(at<int>(p,0)<target)at<uint8_t>(p,8)|=1;
 }
}
static bool restoreTimeline(void* self,void* model,int target){
 void* clock=at<void*>(model,0x30);if(!clock||!at<uint8_t>(clock,0x2d))return false;
 int64_t began=monotonicNs();if(!cacheTimeline(model))return false;
 clearTransientVisuals(self);
 if(target<restoredAt)rewindTimeline(model);
 clockOriginal(clock);uint8_t saved[0x40];memcpy(saved,clock,sizeof(saved));
 priming=true;at<uint8_t>(clock,0x2c)=0;capturingActions=true;
 int cursor=restoredAt;
 for(void* event:eventNotes){
  int when=at<int>(event,0x18);if(when>target)break;
  if(at<uint8_t>(event,0xd)||at<uint8_t>(event,0xc))continue;
  timelineTime(clock,when);advanceEffects(std::max(0,when-cursor)/1000.f);cursor=std::max(cursor,when);
  void* handler=at<void*>(self,0x300);
  if(handler){uintptr_t type=reinterpret_cast<uintptr_t>(at<void*>(event,0))-base;
   fn<void(*)(void*,void*)>(type==0x18daf40?0x109a42c:0xc60578)(handler,event);
  }
  at<uint8_t>(event,0xd)=1;at<int>(event,0x10)=when;
 }
 timelineTime(clock,target);advanceEffects(std::max(0,target-cursor)/1000.f);capturingActions=false;
 for(void* note:sourceNotes)prepareNote(note,target);
 // Materialize nearby notes directly at the final time. Never judge/prune the
 // whole historical chart at 60 Hz merely to recover a handful of scene events.
 fn<void(*)(void*,void*)>(0xb94168)(model,self);
 if(void* visual=at<void*>(self,0x3c0))fn<void(*)(void*,int,void*)>(0x127cd8c)(visual,target,model);
 priming=false;memcpy(clock,saved,sizeof(saved));clockOriginal(clock);
 at<int>(clock,0x28)=at<int>(clock,0x20)-target;
 lastClock=nullptr;fraction=0;timelineCursor=target;restoredAt=target;
 pendingSeek=transport::noSeek;musicSyncing=false;
 __android_log_print(4,"ArcPractice","seek ready target=%d actual=%d prepare_ms=%lld",target,timeOf(model),(long long)((monotonicNs()-began)/1000000));
 return true;
}
