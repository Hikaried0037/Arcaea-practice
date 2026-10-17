#include "../native/audio_quality.h"
#include <string>
#include <chrono>
int main(int argc,char** argv){
 if(argc!=7)return 2;FILE* in=fopen(argv[1],"rb"),*out=fopen(argv[2],"wb");if(!in||!out)return 3;
 int hz=std::stoi(argv[3]),ch=std::stoi(argv[4]);float speed=std::stof(argv[5]);bool pitch=std::stoi(argv[6])!=0;
 auto began=std::chrono::steady_clock::now();uint64_t frames=0;
 try{frames=quality::render(hz,ch,speed,pitch,[&](float* p,unsigned n){return unsigned(fread(p,sizeof(float)*ch,n,in));},[&](const float* p,unsigned n){if(fwrite(p,sizeof(float)*ch,n,out)!=n)throw std::runtime_error("write failed");});}
 catch(const std::exception& e){fprintf(stderr,"%s\n",e.what());return 4;}
 fclose(in);fclose(out);double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count();
 printf("frames=%llu seconds=%.5f\n",(unsigned long long)frames,seconds);
 // Reversibility of timeline conversion, including saturated long durations.
 for(float r:{.25f,.37f,1.f,1.33f,2.f})for(unsigned t:{0u,1u,30000u,3600000u})if(std::abs(int64_t(quality::sourceTime(quality::outputTime(t,r),r))-t)>1)return 5;
 return 0;
}
