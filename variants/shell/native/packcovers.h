#include <fstream>
#include <cctype>
#include <vector>

// Pack::imagePath builds a filename from its id in both supported engines;
// the metadata "img" field alone does not override that native code path.
static std::mutex packCoverMutex;
static std::unordered_map<std::string,std::string> packCoverFiles;
static std::string (*packCoverOriginal)(void*);
static std::vector<void*> (*packSongsOriginal)(void*,const std::string*,int,bool);
// The stock click handler probes Past before delegating the selected difficulty.
// Imported packs may legitimately contain only a Beyond/Future chart. Restrict
// fallback to that one availability probe; normal difficulty queries stay exact.
static std::vector<void*> packSongsHook(void* catalog,const std::string* id,int difficulty,bool children){
 uintptr_t caller=reinterpret_cast<uintptr_t>(__builtin_return_address(0));
 auto songs=packSongsOriginal(catalog,id,difficulty,children);
 if(caller==base+packClickQueryReturn&&difficulty==0&&songs.empty()&&id&&id->rfind("custom_",0)==0){
  for(int alternative:{3,2,1,4}){
   songs=packSongsOriginal(catalog,id,alternative,children);
   if(!songs.empty()){
    __android_log_print(4,"ArcPractice","local pack availability id=%s difficulty=%d songs=%zu",id->c_str(),alternative,songs.size());break;
   }
  }
 }
 return songs;
}
static void loadPackCovers(){
 std::unordered_map<std::string,std::string> next;
 std::ifstream file(assetRoot+"/.practice-pack-covers.tsv");std::string line;size_t total=0;
 while(std::getline(file,line)&&((total+=line.size())<4*1024*1024)){
  size_t tab=line.find('\t');if(tab==std::string::npos||tab==0||line.size()>512)continue;
  std::string id=line.substr(0,tab),path=line.substr(tab+1);
  bool safe=id.size()<=128;for(unsigned char c:id)safe&=std::isalnum(c)||c=='_'||c=='-';
  if(!safe||path.rfind("songs/pack/",0)!=0||path.find("..")!=std::string::npos||path.find_first_of("\t\r\\")!=std::string::npos)continue;
  std::string absolute=assetRoot+"/"+path;if(access(absolute.c_str(),R_OK)==0)next[id]=absolute;
 }
 {std::lock_guard<std::mutex> lock(packCoverMutex);packCoverFiles.swap(next);}
}
static std::string packCoverHook(void* pack){
 const auto& id=at<std::string>(pack,8);
 {std::lock_guard<std::mutex> lock(packCoverMutex);auto found=packCoverFiles.find(id);
  if(found!=packCoverFiles.end()){
   static int diagnostics=0;if(diagnostics++<30)__android_log_print(4,"ArcPractice","native pack cover id=%s file=%s",id.c_str(),found->second.c_str());
   return found->second;
  }
 }
 return packCoverOriginal(pack);
}
