#include "../native/music_origin.h"
extern "C" __attribute__((visibility("default"))) void initializeOrigin(void* clock,void(*refresh)(void*)){
 transport::initializeMusicOrigin(clock,refresh,[]{});
}
