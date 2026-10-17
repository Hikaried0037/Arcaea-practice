#include <android/asset_manager.h>
#include <elf.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <string>
#include <mutex>
#include <unordered_map>
#include <vector>
static std::string assetRoot,chartPath;
static bool globalTheme;
struct LocalAsset{std::vector<char> bytes;off64_t pos=0;std::string path;};
static std::mutex assetMutex;
static std::unordered_map<AAsset*,LocalAsset*> localAssets;
static AAsset* (*assetOpenOriginal)(AAssetManager*,const char*,int);
static int (*assetReadOriginal)(AAsset*,void*,size_t);
static void (*assetCloseOriginal)(AAsset*);
static off_t (*assetSeekOriginal)(AAsset*,off_t,int);
static off64_t (*assetSeek64Original)(AAsset*,off64_t,int);
static off_t (*assetLengthOriginal)(AAsset*);
static off64_t (*assetLength64Original)(AAsset*);
static off_t (*assetRemainingOriginal)(AAsset*);
static off64_t (*assetRemaining64Original)(AAsset*);
static const void* (*assetBufferOriginal)(AAsset*);
static int (*assetFdOriginal)(AAsset*,off_t*,off_t*);
static int (*assetFd64Original)(AAsset*,off64_t*,off64_t*);
static int (*assetAllocatedOriginal)(AAsset*);
static int (*streamOpenOriginal)(void*,const char*,unsigned,void*,void**);
static int (*soundOpenOriginal)(void*,const char*,unsigned,void*,void**);
static std::string localAudioPath(const char* name,unsigned mode){
 if(!name||(mode&0x10000c00u))return "";std::string n=name;
 const std::string prefix="file:///android_asset/";if(n.rfind(prefix,0)==0)n=n.substr(prefix.size());
 if(n.rfind("assets/",0)==0)n=n.substr(7);
 if(n.rfind("songs/",0)!=0||n.find("..")!=std::string::npos)return "";
 std::string p=assetRoot+"/"+n;return access(p.c_str(),R_OK)==0?p:"";
}
static int streamOpen(void* system,const char* name,unsigned mode,void* info,void** sound){std::string p=localAudioPath(name,mode);int result=streamOpenOriginal(system,p.empty()?name:p.c_str(),mode,info,sound);if(!result&&sound)qualityRegisterSound(system,p.empty()?name:p.c_str(),mode,*sound);return result;}
static int soundOpen(void* system,const char* name,unsigned mode,void* info,void** sound){std::string p=localAudioPath(name,mode);int result=soundOpenOriginal(system,p.empty()?name:p.c_str(),mode,info,sound);if(!result&&sound)qualityRegisterSound(system,p.empty()?name:p.c_str(),mode,*sound);return result;}
static AAsset* assetOpen(AAssetManager* m,const char* name,int mode){
 std::string n=name?name:"";if(n.rfind("assets/",0)==0)n=n.substr(7);
 std::lock_guard<std::mutex> lock(assetMutex);
 if(n.size()>4&&n.substr(n.size()-4)==".aff")chartPath=n;
 if(globalTheme){
  if(n.rfind("img/bg/1080/",0)==0&&n.size()>4&&n.substr(n.size()-4)==".jpg")n="img/bg/1080/finale_conflict.jpg";
  const char* tracks[]={"track.png","track_arcana.png","track_black.png","track_colorless.png","track_dark.png","track_dark_nijuusei.png","track_dark_vs.png","track_darklephon.png","track_finale.png","track_pentiment.png","track_rei.png","track_tempestissimo.png"};
  for(const char* t:tracks)if(n==std::string("img/")+t){n="img/track_dark_vs.png";break;}
  // 6K outer lanes and their judgement extensions are separate textures.
  // Match the forced dark track without changing the song's original side.
  if(n=="img/track_extralane_light.png")n="img/track_extralane_dark.png";
  if(n=="img/track_critical_extra_light.png")n="img/track_critical_extra_dark.png";
 }
 if(n.find("..")!=std::string::npos||n.empty()||n[0]=='/')return assetOpenOriginal(m,name,mode);
 std::string path=assetRoot+"/"+n;FILE* f=fopen(path.c_str(),"rb");
 if(!f)return assetOpenOriginal(m,n.c_str(),mode);
 fseek(f,0,SEEK_END);long size=ftell(f);rewind(f);
 if(size<0||size>512*1024*1024){fclose(f);return nullptr;}
 auto p=new LocalAsset();p->path=path;p->bytes.resize(size);
 if(fread(p->bytes.data(),1,size,f)!=static_cast<size_t>(size)){delete p;fclose(f);return nullptr;}fclose(f);
 auto handle=reinterpret_cast<AAsset*>(p);localAssets[handle]=p;return handle;
}
static int assetRead(AAsset* a,void* b,size_t n){std::lock_guard<std::mutex> l(assetMutex);auto it=localAssets.find(a);if(it==localAssets.end())return assetReadOriginal(a,b,n);auto p=it->second;n=std::min(n,p->bytes.size()-static_cast<size_t>(p->pos));memcpy(b,p->bytes.data()+p->pos,n);p->pos+=n;return n;}
static void assetClose(AAsset* a){std::lock_guard<std::mutex> l(assetMutex);auto it=localAssets.find(a);if(it==localAssets.end()){assetCloseOriginal(a);return;}delete it->second;localAssets.erase(it);}
static off64_t seekLocal(LocalAsset* p,off64_t n,int w){off64_t target=(w==SEEK_SET?0:w==SEEK_CUR?p->pos:w==SEEK_END?p->bytes.size():-1)+n;if(target<0||target>static_cast<off64_t>(p->bytes.size()))return -1;return p->pos=target;}
static off_t assetSeek(AAsset* a,off_t n,int w){std::lock_guard<std::mutex> l(assetMutex);auto it=localAssets.find(a);return it==localAssets.end()?assetSeekOriginal(a,n,w):seekLocal(it->second,n,w);}
static off64_t assetSeek64(AAsset* a,off64_t n,int w){std::lock_guard<std::mutex> l(assetMutex);auto it=localAssets.find(a);return it==localAssets.end()?assetSeek64Original(a,n,w):seekLocal(it->second,n,w);}
#define ASSET_SIZE(NAME,TYPE,EXPR) static TYPE NAME(AAsset* a){std::lock_guard<std::mutex> l(assetMutex);auto it=localAssets.find(a);if(it==localAssets.end())return NAME##Original(a);auto p=it->second;return (EXPR);}
ASSET_SIZE(assetLength,off_t,p->bytes.size())
ASSET_SIZE(assetLength64,off64_t,p->bytes.size())
ASSET_SIZE(assetRemaining,off_t,p->bytes.size()-p->pos)
ASSET_SIZE(assetRemaining64,off64_t,p->bytes.size()-p->pos)
ASSET_SIZE(assetBuffer,const void*,p->bytes.data())
ASSET_SIZE(assetAllocated,int,1)
static int assetFd(AAsset* a,off_t* s,off_t* n){std::lock_guard<std::mutex> l(assetMutex);auto it=localAssets.find(a);if(it==localAssets.end())return assetFdOriginal(a,s,n);*s=0;*n=it->second->bytes.size();return open(it->second->path.c_str(),O_RDONLY|O_CLOEXEC);}
static int assetFd64(AAsset* a,off64_t* s,off64_t* n){std::lock_guard<std::mutex> l(assetMutex);auto it=localAssets.find(a);if(it==localAssets.end())return assetFd64Original(a,s,n);*s=0;*n=it->second->bytes.size();return open(it->second->path.c_str(),O_RDONLY|O_CLOEXEC);}
struct AssetHook{const char* name;void* replacement;void** original;};
#define AH(F,N) {N,reinterpret_cast<void*>(F),reinterpret_cast<void**>(&F##Original)}
static AssetHook assetHooks[]={AH(assetOpen,"AAssetManager_open"),AH(assetRead,"AAsset_read"),AH(assetClose,"AAsset_close"),AH(assetSeek,"AAsset_seek"),AH(assetSeek64,"AAsset_seek64"),AH(assetLength,"AAsset_getLength"),AH(assetLength64,"AAsset_getLength64"),AH(assetRemaining,"AAsset_getRemainingLength"),AH(assetRemaining64,"AAsset_getRemainingLength64"),AH(assetBuffer,"AAsset_getBuffer"),AH(assetFd,"AAsset_openFileDescriptor"),AH(assetFd64,"AAsset_openFileDescriptor64"),AH(assetAllocated,"AAsset_isAllocated"),AH(qualityPlay,"_ZN4FMOD6System9playSoundEPNS_5SoundEPNS_12ChannelGroupEbPPNS_7ChannelE"),AH(qualityPosition,"_ZN4FMOD7Channel11getPositionEPjj"),AH(qualitySeek,"_ZN4FMOD7Channel11setPositionEjj"),AH(qualityLength,"_ZN4FMOD5Sound9getLengthEPjj"),AH(qualityRelease,"_ZN4FMOD5Sound7releaseEv"),AH(qualityStop,"_ZN4FMOD14ChannelControl4stopEv"),AH(streamOpen,"_ZN4FMOD6System12createStreamEPKcjP22FMOD_CREATESOUNDEXINFOPPNS_5SoundE"),AH(soundOpen,"_ZN4FMOD6System11createSoundEPKcjP22FMOD_CREATESOUNDEXINFOPPNS_5SoundE")};
static int hookAssetLibrary(dl_phdr_info* info,size_t,void*){
 if(!strstr(info->dlpi_name,"libcocos2dcpp.so")&&!strstr(info->dlpi_name,"libfmod")&&!strstr(info->dlpi_name,"libarcinf.so"))return 0;
 ElfW(Dyn)* dyn=nullptr;for(int i=0;i<info->dlpi_phnum;i++)if(info->dlpi_phdr[i].p_type==PT_DYNAMIC)dyn=reinterpret_cast<ElfW(Dyn)*>(info->dlpi_addr+info->dlpi_phdr[i].p_vaddr);
 if(!dyn)return 0;ElfW(Sym)* syms=nullptr;const char* names=nullptr;ElfW(Rela)* rel=nullptr;size_t bytes=0;
 for(auto d=dyn;d->d_tag!=DT_NULL;d++){uintptr_t v=info->dlpi_addr+d->d_un.d_ptr;switch(d->d_tag){case DT_SYMTAB:syms=reinterpret_cast<ElfW(Sym)*>(v);break;case DT_STRTAB:names=reinterpret_cast<const char*>(v);break;case DT_JMPREL:rel=reinterpret_cast<ElfW(Rela)*>(v);break;case DT_PLTRELSZ:bytes=d->d_un.d_val;break;}}
 if(!syms||!names||!rel)return 0;
 for(size_t i=0;i<bytes/sizeof(*rel);i++){const char* name=names+syms[ELF64_R_SYM(rel[i].r_info)].st_name;for(auto& h:assetHooks)if(!strcmp(h.name,name)){
  auto slot=reinterpret_cast<void**>(info->dlpi_addr+rel[i].r_offset);long page=sysconf(_SC_PAGESIZE);auto pageStart=reinterpret_cast<uintptr_t>(slot)&~(page-1);
  if(mprotect(reinterpret_cast<void*>(pageStart),page,PROT_READ|PROT_WRITE)==0){*slot=h.replacement;mprotect(reinterpret_cast<void*>(pageStart),page,PROT_READ);}
 }}return 0;
}
extern "C" JNIEXPORT void JNICALL Java_moe_practice_PracticeOverlay_initAssets(JNIEnv* env,jclass,jstring path){const char* s=env->GetStringUTFChars(path,nullptr);assetRoot=s;env->ReleaseStringUTFChars(path,s);FILE* mode=fopen((assetRoot+"/theme-mode").c_str(),"rb");globalTheme=mode&&fgetc(mode)==1;if(mode)fclose(mode);void* lib=dlopen("libandroid.so",RTLD_NOW);void* fmod=dlopen("libfmod.so",RTLD_NOW);for(auto& h:assetHooks)*h.original=dlsym(h.name[0]=='_'?fmod:lib,h.name);dl_iterate_phdr(hookAssetLibrary,nullptr);}
extern "C" JNIEXPORT jstring JNICALL Java_moe_practice_PracticeOverlay_chartAsset(JNIEnv* env,jclass){std::lock_guard<std::mutex> l(assetMutex);return env->NewStringUTF(chartPath.c_str());}
