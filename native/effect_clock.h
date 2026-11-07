#pragma once
#include <cstdint>
namespace practiceEffects {
// The native model computes enwidencamera/enwidenlanes from chart time on
// every render. Replaying their events alone does not freeze that evaluator.
// Shift only their temporary epoch, never the note/music clock or durations.
struct EpochScope {
 int& camera; int& lanes; int savedCamera,savedLanes;
 EpochScope(int& c,int& l,int now,int effects):camera(c),lanes(l),savedCamera(c),savedLanes(l){
  camera=int(int64_t(c)+now-effects);lanes=int(int64_t(l)+now-effects);
 }
 ~EpochScope(){camera=savedCamera;lanes=savedLanes;}
};
}
