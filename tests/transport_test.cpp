#include "../variants/full/native/transport.h"
#include <cassert>
#include <iostream>
int main(){
 for(float speed:{.25f,.3f,.5f,1.f,1.5f,2.f})for(int a:{0,1000,30000,180000}){
  int from=transport::leadStart(a,speed);transport::LeadIn clock;
  assert(!clock.active);clock.begin(from,a,1000000000LL);
  assert(clock.sample(1000000000LL,false)==from);
  assert(clock.sample(2500000000LL,false)==from+(a-from)/2);
  assert(clock.active&&clock.remaining()==1500);
  int paused=clock.sample(5500000000LL,true);assert(paused==from+(a-from)/2&&clock.remaining()==1500);
  assert(clock.sample(6999000000LL,false)<=a&&clock.active);
  assert(clock.sample(7000000000LL,false)==a&&!clock.active&&clock.remaining()==0);
 }
 std::cout<<"PASS: 24 lead-in scenarios at 0.25x–2x, A=0 supported, exactly 3000 ms excluding loading/pause\n";
}
