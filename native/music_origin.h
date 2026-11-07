#pragma once
#include <cstdint>
namespace transport {
// Music must have passed the native start threshold before seeking. In
// particular a negative AFF offset starts music after chart zero, not at zero.
template<class Refresh,class Pause>
void initializeMusicOrigin(void* state,Refresh refresh,Pause pause){
 auto clock=static_cast<uint8_t*>(state);refresh(state);
 if(clock[0x2e])return;
 auto integer=[&](int offset)->int&{return *reinterpret_cast<int*>(clock+offset);};
 uint8_t paused=clock[0x2c];clock[0x2c]=0;
 integer(0x28)=integer(0x20)+integer(0x30)-1;
 refresh(state);pause();clock[0x2c]=paused;
}
}
