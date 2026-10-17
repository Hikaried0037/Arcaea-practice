#pragma once
#include "audio_quality.h"
#include "audio_decode.h"
#include <dirent.h>
#include <cerrno>
#include <memory>
#include <set>
// Only the original song handles escape to the game. A converted stream is
// substituted at playSound, and position/seek units are mapped to source time.
namespace audioCache {
struct Source {void* system;std::string path;unsigned mode;};
struct Playback {void* source;void* actual;float requested,rate;bool changesPitch;};
struct Converted {void* sound;float rate;std::string path;};
static std::mutex mutex;
static std::unordered_map<void*,Source> sources;
static std::unordered_map<void*,Playback> playing;
static std::unordered_map<void*,std::unordered_map<std::string,Converted>> converted;
static std::unordered_map<void*,float> soundRates;
static int (*getCurrentSound)(void*,void**),(*getFormat)(void*,int*,int*,int*,int*),(*getDefaults)(void*,float*,int*),(*readData)(void*,void*,unsigned,unsigned*);
static int (*seekData)(void*,unsigned);
static bool available;
static std::atomic<int> failure{0};
static float channelRate(void* channel){std::lock_guard<std::mutex> lock(mutex);auto it=playing.find(channel);return it==playing.end()?1.f:it->second.rate;}
static bool reload(void* channel,float rate,bool changesPitch){std::lock_guard<std::mutex> lock(mutex);auto it=playing.find(channel);return it!=playing.end()&&(std::abs(it->second.requested-rate)>.0001f||(rate!=1.f&&it->second.changesPitch!=changesPitch));}
static bool songPath(const std::string& path){return path.find("/songs/")!=std::string::npos||path.rfind("songs/",0)==0||path.rfind("assets/songs/",0)==0;}
static std::string cacheKey(const Source& source,float rate,bool changesPitch){
 struct stat info{};std::string fingerprint=source.path+"|hq-v4|"+std::to_string(int(std::lround(rate*100)))+"|"+(changesPitch?"rate":"tempo");
 if(stat(source.path.c_str(),&info)==0)fingerprint+="|"+std::to_string(info.st_size)+"|"+std::to_string(info.st_mtime)+"|"+std::to_string(info.st_mtim.tv_nsec);
 char key[32];snprintf(key,sizeof(key),"%016llx",(unsigned long long)quality::identity(fingerprint.c_str()));return key;
}
static void prune(const std::string& directory,const std::string& keep){
 DIR* d=opendir(directory.c_str());if(!d)return;std::vector<std::pair<time_t,std::string>> files;uint64_t total=0;dirent* item;
 while((item=readdir(d))){std::string n=item->d_name;if(n.size()!=20||n.substr(16)!=".wav"||n.find_first_not_of("0123456789abcdef",0)<16)continue;
  std::string p=directory+"/"+n;struct stat st{};if(stat(p.c_str(),&st)==0&&S_ISREG(st.st_mode)){total+=st.st_size;files.push_back({st.st_mtime,p});}}
 closedir(d);std::sort(files.begin(),files.end());
 for(auto& item:files){if(total<=512ULL*1024*1024)break;if(item.second==keep)continue;struct stat st{};if(stat(item.second.c_str(),&st)==0&&unlink(item.second.c_str())==0)total-=st.st_size;}
}
static std::string prepare(const Source& source,const std::string& key,float rate,bool changesPitch){
 const std::string directory=assetRoot+"/.practice-audio-cache-v1";if(mkdir(directory.c_str(),0700)!=0&&errno!=EEXIST)throw std::runtime_error("audio cache directory");
 std::string path=directory+"/"+key+".wav",part=path+".part";
 FILE* existing=fopen(path.c_str(),"rb");if(existing){unsigned char h[44];size_t n=fread(h,1,sizeof(h),existing);fclose(existing);struct stat st{};
  uint32_t bytes=n==44?uint32_t(h[40])|(uint32_t(h[41])<<8)|(uint32_t(h[42])<<16)|(uint32_t(h[43])<<24):0;
  if(n==44&&!memcmp(h,"RIFF",4)&&!memcmp(h+8,"WAVEfmt ",8)&&h[20]==3&&h[34]==32&&stat(path.c_str(),&st)==0&&st.st_size==44LL+bytes)return path;
 }
 void* decoder=nullptr;
 // An independent OPENONLY stream decodes source samples without resampling.
 int result=soundOpenOriginal(source.system,source.path.c_str(),quality::decodeMode,nullptr,&decoder);
 if(result||!decoder)throw std::runtime_error("source decoder unavailable");
 struct SoundGuard {void* sound;~SoundGuard(){qualityReleaseOriginal(sound);}} guard{decoder};
 int type=0,format=0,channels=0,bits=0;float frequency=0;int priority=0;
 if(getFormat(decoder,&type,&format,&channels,&bits)||getDefaults(decoder,&frequency,&priority))throw std::runtime_error("source format unavailable");
 if(channels<1||channels>8||bits<8||bits>32||(format<1||format>5))throw std::runtime_error("unsupported source format");
 if(seekData(decoder,0))throw std::runtime_error("decoder seek to source origin failed");
 unsigned expectedFrames=0;qualityLengthOriginal(decoder,&expectedFrames,2);uint64_t decodedFrames=0;
 int sampleRate=int(std::lround(frequency)),sampleBytes=bits/8;std::vector<unsigned char> raw(quality::blockFrames*channels*sampleBytes);
 FILE* output=fopen(part.c_str(),"wb+");if(!output)throw std::runtime_error("audio cache write");
 try {
  if(!quality::wavHeader(output,0,sampleRate,channels))throw std::runtime_error("audio header write");
  auto reader=[&](float* samples,unsigned frames)->unsigned{
   unsigned received=0;int r=readData(decoder,raw.data(),frames*channels*sampleBytes,&received);
   if(r!=0&&received==0&&r!=16)throw std::runtime_error("audio decode failed"); // FMOD_ERR_FILE_EOF = 16
   if(received%(channels*sampleBytes))throw std::runtime_error("partial PCM frame");
   unsigned count=received/(channels*sampleBytes);decodedFrames+=count;
   for(size_t i=0;i<size_t(count)*channels;i++){
    const unsigned char* p=raw.data()+i*sampleBytes;
    if(format==5){float v;memcpy(&v,p,4);samples[i]=v;}
    else if(bits==8)samples[i]=(int(*p)-128)/128.f;
    else {uint32_t v=0;for(int j=0;j<sampleBytes;j++)v|=uint32_t(p[j])<<(8*j);int64_t signedValue=v;if(v&(uint32_t(1)<<(bits-1)))signedValue-=int64_t(1)<<bits;samples[i]=float(double(signedValue)/double(uint64_t(1)<<(bits-1)));}
   }
   return count;
  };
  auto writer=[&](const float* samples,unsigned frames){if(fwrite(samples,sizeof(float)*channels,frames,output)!=frames)throw std::runtime_error("audio cache full");};
  uint64_t frames=quality::render(sampleRate,channels,rate,changesPitch,reader,writer);
  // Allow a compressed codec's small end-padding discrepancy, but reject
  // missing large prefixes instead of caching audio with a shifted time origin.
  if(expectedFrames&&decodedFrames+4096<expectedFrames)throw std::runtime_error("incomplete source PCM decode");
  __android_log_print(4,"ArcPractice","quality source origin=0 decoded_frames=%llu expected_frames=%u sample_rate=%d",(unsigned long long)decodedFrames,expectedFrames,sampleRate);
  if(!frames||!quality::wavHeader(output,frames,sampleRate,channels))throw std::runtime_error("audio cache header");
  if(fclose(output)!=0){output=nullptr;throw std::runtime_error("audio cache flush");}output=nullptr;
  if(rename(part.c_str(),path.c_str())!=0)throw std::runtime_error("audio cache commit");
  prune(directory,path);__android_log_print(4,"ArcPractice","quality audio prepared rate=%.2f pitch=%d frames=%llu sample_rate=%d",rate,changesPitch,(unsigned long long)frames,sampleRate);return path;
 }catch(...){if(output)fclose(output);unlink(part.c_str());throw;}
}
// Stream handles need not stay open just because their WAV is cached on disk.
// Drop stopped/stolen channel records and release converted streams that are no
// longer audible. Active voices (including fades) keep their own stream alive.
static void retire(void* source,void* keep){
 std::vector<std::pair<void*,Playback>> snapshot;
 {std::lock_guard<std::mutex> lock(mutex);for(auto& p:playing)snapshot.push_back(p);}
 std::set<void*> live{keep};std::vector<std::pair<void*,Playback>> stale;
 for(auto& p:snapshot){void* current=nullptr;if(getCurrentSound(p.first,&current)==0&&current==p.second.actual)live.insert(current);else stale.push_back(p);}
 std::vector<void*> release;
 {std::lock_guard<std::mutex> lock(mutex);
  for(auto& p:stale){auto it=playing.find(p.first);if(it!=playing.end()&&it->second.actual==p.second.actual)playing.erase(it);}
  auto owner=converted.find(source);if(owner!=converted.end())for(auto it=owner->second.begin();it!=owner->second.end();){
   if(!live.count(it->second.sound)){release.push_back(it->second.sound);soundRates.erase(it->second.sound);it=owner->second.erase(it);}else++it;
  }
 }
 for(void* sound:release)qualityReleaseOriginal(sound);
}
static bool init(void* fmod){
 getCurrentSound=reinterpret_cast<decltype(getCurrentSound)>(dlsym(fmod,"_ZN4FMOD7Channel15getCurrentSoundEPPNS_5SoundE"));
 getFormat=reinterpret_cast<decltype(getFormat)>(dlsym(fmod,"_ZN4FMOD5Sound9getFormatEP15FMOD_SOUND_TYPEP17FMOD_SOUND_FORMATPiS5_"));
 getDefaults=reinterpret_cast<decltype(getDefaults)>(dlsym(fmod,"_ZN4FMOD5Sound11getDefaultsEPfPi"));
 readData=reinterpret_cast<decltype(readData)>(dlsym(fmod,"_ZN4FMOD5Sound8readDataEPvjPj"));
 seekData=reinterpret_cast<decltype(seekData)>(dlsym(fmod,"_ZN4FMOD5Sound8seekDataEj"));
 available=seekData&&getCurrentSound&&getFormat&&getDefaults&&readData&&qualityPlayOriginal&&qualityPositionOriginal&&qualitySeekOriginal&&qualityLengthOriginal&&qualityReleaseOriginal&&qualityStopOriginal;
 return available;
}
}
static void qualityRegisterSound(void* system,const char* path,unsigned mode,void* sound){
 if(!sound||!path||(mode&0x10000c00u)||!audioCache::songPath(path))return;
 std::lock_guard<std::mutex> lock(audioCache::mutex);audioCache::sources[sound]={system,path,mode};
}
static int qualityPlay(void* system,void* original,void* group,bool paused,void** channel){
 float rate=enabled?speed.load():1.f;bool changesPitch=changePitch.load()!=0;
 void* actual=original;float convertedRate=1.f;bool eligible=enabled&&(buildingScene||scene);audioCache::Source source{};bool known=false;
 {std::lock_guard<std::mutex> lock(audioCache::mutex);auto it=audioCache::sources.find(original);if(it!=audioCache::sources.end()){source=it->second;known=true;}}
 if(known&&audioCache::available&&eligible&&rate!=1.f){
  try {
   std::string key=audioCache::cacheKey(source,rate,changesPitch),path;void* prepared=nullptr;
   {std::lock_guard<std::mutex> lock(audioCache::mutex);auto p=audioCache::converted.find(original);if(p!=audioCache::converted.end()){auto c=p->second.find(key);if(c!=p->second.end())prepared=c->second.sound;}}
   if(!prepared){path=audioCache::prepare(source,key,rate,changesPitch);int r=streamOpenOriginal(system,path.c_str(),0x80u|0x8u|0x1u,nullptr,&prepared);
    if(r||!prepared)throw std::runtime_error("converted stream unavailable");
    std::lock_guard<std::mutex> lock(audioCache::mutex);audioCache::converted[original][key]={prepared,rate,path};audioCache::soundRates[prepared]=rate;
   }
   actual=prepared;convertedRate=rate;audioError=0;audioCache::failure=0;
  }catch(const std::exception& e){audioError=-20;audioCache::failure=-20;__android_log_print(6,"ArcPractice","quality audio fallback: %s",e.what());}
 }
 int result=qualityPlayOriginal(system,actual,group,paused,channel);
 if(!result&&channel&&*channel){std::lock_guard<std::mutex> lock(audioCache::mutex);audioCache::playing.erase(*channel);if(known)audioCache::playing[*channel]={original,actual,eligible?rate:1.f,convertedRate,changesPitch};}
 if(!result&&actual!=original)audioCache::retire(original,actual);
 return result;
}
static int qualityPosition(void* channel,uint32_t* position,uint32_t unit){int result=qualityPositionOriginal(channel,position,unit);if(!result&&position&&(unit==1||unit==2))*position=quality::sourceTime(*position,audioCache::channelRate(channel));return result;}
static int qualitySeek(void* channel,uint32_t position,uint32_t unit){if(unit==1||unit==2)position=quality::outputTime(position,audioCache::channelRate(channel));return qualitySeekOriginal(channel,position,unit);}
static int qualityLength(void* sound,uint32_t* length,uint32_t unit){
 int result=qualityLengthOriginal(sound,length,unit);if(!result&&length&&(unit==1||unit==2)){std::lock_guard<std::mutex> lock(audioCache::mutex);auto it=audioCache::soundRates.find(sound);if(it!=audioCache::soundRates.end())*length=quality::sourceTime(*length,it->second);}return result;
}
static int qualityRelease(void* sound){
 std::vector<void*> release;
 {std::lock_guard<std::mutex> lock(audioCache::mutex);audioCache::sources.erase(sound);auto it=audioCache::converted.find(sound);
  if(it!=audioCache::converted.end()){for(auto& c:it->second){release.push_back(c.second.sound);audioCache::soundRates.erase(c.second.sound);}audioCache::converted.erase(it);}
  audioCache::soundRates.erase(sound);
  for(auto p=audioCache::playing.begin();p!=audioCache::playing.end();)if(p->second.source==sound||p->second.actual==sound)p=audioCache::playing.erase(p);else++p;
 }
 for(void* child:release)qualityReleaseOriginal(child);return qualityReleaseOriginal(sound);
}
static int qualityStop(void* channel){int result=qualityStopOriginal(channel);if(!result){std::lock_guard<std::mutex> lock(audioCache::mutex);audioCache::playing.erase(channel);}return result;}
