#pragma once
static int (*qualityPlayOriginal)(void*,void*,void*,bool,void**);
static int (*qualityPositionOriginal)(void*,uint32_t*,uint32_t);
static int (*qualitySeekOriginal)(void*,uint32_t,uint32_t);
static int (*qualityLengthOriginal)(void*,uint32_t*,uint32_t);
static int (*qualityReleaseOriginal)(void*);
static int (*qualityStopOriginal)(void*);
static void qualityRegisterSound(void*,const char*,unsigned,void*);
static int qualityPlay(void*,void*,void*,bool,void**);
static int qualityPosition(void*,uint32_t*,uint32_t);
static int qualitySeek(void*,uint32_t,uint32_t);
static int qualityLength(void*,uint32_t*,uint32_t);
static int qualityRelease(void*);
static int qualityStop(void*);
