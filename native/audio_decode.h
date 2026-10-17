#pragma once
namespace quality {
// FMOD_MODE values: OPENONLY disables stream prebuffering before readData.
// 0x00020000 is UNIQUE, not OPENONLY; using it drops the prefetched prefix.
constexpr unsigned decodeTwoD=0x00000008u;
constexpr unsigned decodeStream=0x00000080u;
constexpr unsigned decodeOpenOnly=0x00002000u;
constexpr unsigned decodeAccurateTime=0x00004000u;
constexpr unsigned decodeMode=decodeTwoD|decodeStream|decodeOpenOnly|decodeAccurateTime;
}
