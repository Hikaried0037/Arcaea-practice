#include "archive.h"
static al_u32 u16(const al_u8 *p){return p[0]|((al_u32)p[1]<<8);}
static al_u32 u32(const al_u8 *p){return u16(p)|u16(p+2)<<16;}
static int equal(const char*a,const char*b){while(*a&&*a==*b){a++;b++;}return *a==*b;}
static char lower(char c){return c>='A'&&c<='Z'?c+32:c;}
int al_zip_scan(const al_u8 *b,al_u64 n,ALZipEntry *out,al_u32 *count){
 *count=0;if(!b||n<22||n>268435456ULL)return 1;
 al_u64 e=n-22,limit=n>65557?n-65557:0;
 for(;;){if(u32(b+e)==0x06054b50&&e+22+u16(b+e+20)==n)break;if(e==limit)return 1;e--;}
 al_u32 entries=u16(b+e+10),pos=u32(b+e+16),cdsize=u32(b+e+12);
 if(u16(b+e+4)||u16(b+e+6)||u16(b+e+8)!=entries||entries>128||!entries||(al_u64)pos+cdsize!=e)return 2;
 al_u64 total=0;al_u32 cd=pos;
 for(al_u32 i=0;i<entries;i++){
  if((al_u64)pos+46>e||u32(b+pos)!=0x02014b50)return 3;
  al_u32 flags=u16(b+pos+8),method=u16(b+pos+10),cs=u32(b+pos+20),us=u32(b+pos+24),nl=u16(b+pos+28),el=u16(b+pos+30),cl=u16(b+pos+32),off=u32(b+pos+42);
  if(!nl||nl>255||(al_u64)pos+46+nl+el+cl>e||u16(b+pos+34)||cs==0xffffffffU||us>134217728U||((u32(b+pos+38)>>16)&0170000)==0120000)return 4;
  if(flags&~(0x800|8|6)||flags&1||(method!=0&&method!=8))return 5;
  if((al_u64)off+30>cd||u32(b+off)!=0x04034b50||u16(b+off+8)!=method||u16(b+off+6)!=flags||u16(b+off+26)!=nl)return 6;
  al_u32 start=off+30+u16(b+off+26)+u16(b+off+28);
  if(start<off||(al_u64)start+cs>cd||(!method&&cs!=us))return 6;
  const al_u8 *name=b+pos+46;char normalized[256];al_u32 base=0;
  for(al_u32 j=0;j<nl;j++){
   if(!name[j]||name[j]==':'||name[j]<32||name[j]!=b[off+30+j])return 7;
   normalized[j]=name[j]=='\\'?'/':(char)name[j];
   if(normalized[j]=='/'){if(j==0)return 7;base=j+1;}
  }
  normalized[nl]=0;
  for(al_u32 j=0;j<nl;j++)if((j==0||normalized[j-1]=='/')&&normalized[j]=='.'&&((j+1==nl)||normalized[j+1]=='/'||(normalized[j+1]=='.'&&(j+2==nl||normalized[j+2]=='/'))))return 7;
  total+=us;if(total>268435456ULL)return 8;
  // Directories, metadata forks and hidden files are never extracted.
  if(normalized[nl-1]!='/'&&normalized[base]!='.'&&!(nl>9&&normalized[0]=='_'&&normalized[1]=='_')){
   ALZipEntry *x=out+*count;al_u32 k=0;for(al_u32 j=base;j<nl;j++)x->name[k++]=lower(normalized[j]);x->name[k]=0;
   for(al_u32 j=0;j<*count;j++)if(equal(x->name,out[j].name))return 9;
   x->offset=start;x->compressed=cs;x->size=us;x->crc=u32(b+pos+16);x->method=method;(*count)++;
  }
  pos+=46+nl+el+cl;
 }
 return pos==e&&*count?0:3;
}
static int space(al_u8 c){return c==' '||c=='\t'||c=='\r';}
static int letter(al_u8 c){return (c>='a'&&c<='z')||(c>='A'&&c<='Z');}
int al_aff_validate(const al_u8*b,al_u64 n){
 if(!b||!n||n>16777216)return 1;
 int offset=0,separator=0,timing=0,event=0,depth=0;
 for(al_u64 start=0;start<n;){al_u64 end=start;while(end<n&&b[end]!='\n'&&b[end]!='\r'){if(!b[end])return 1;end++;}al_u64 next=end+1;
  for(al_u64 j=start;j+1<end;j++)if(b[j]=='/'&&b[j+1]=='/'){end=j;break;}
  while(start<end&&space(b[start]))start++;while(end>start&&space(b[end-1]))end--;
  if(start<end){
   if(!separator){
    if(end-start==1&&b[start]=='-')separator=1;
    else{const char*key="audiooffset";al_u64 j=start;int match=1;for(int k=0;k<11;k++)if(j>=end||lower((char)b[j++])!=key[k]){match=0;break;}
     if(match){while(j<end&&space(b[j]))j++;if(j<end&&b[j++]==':'){while(j<end&&space(b[j]))j++;int neg=0;if(j<end&&(b[j]=='-'||b[j]=='+'))neg=b[j++]=='-';int digits=0;al_u64 value=0;while(j<end&&b[j]>='0'&&b[j]<='9'){digits++;value=value*10+b[j++]-'0';if(value>2147483648ULL)return 1;}while(j<end&&space(b[j]))j++;if(digits&&j==end&&value<=(neg?2147483648ULL:2147483647ULL))offset=1;}}
    }
   }else{
    for(al_u64 j=start;j<end;j++){
     if(b[j]=='('){depth++;al_u64 k=j+1;while(k<end&&space(b[k]))k++;if(k<end&&(b[k]=='+'||b[k]=='-'))k++;int digit=0;while(k<end&&b[k]>='0'&&b[k]<='9'){digit=1;k++;}while(k<end&&space(b[k]))k++;if(digit&&k<end&&b[k]==',')event=1;}
     else if(b[j]==')'&&--depth<0)return 4;
     if(j+6<end&&(j==start||!letter(b[j-1]))&&b[j]=='t'&&b[j+1]=='i'&&b[j+2]=='m'&&b[j+3]=='i'&&b[j+4]=='n'&&b[j+5]=='g'){al_u64 k=j+6;while(k<end&&space(b[k]))k++;if(k<end&&b[k]=='(')timing=1;}
    }
   }
  }start=next;
 }
 return !offset?1:!separator?2:!timing?3:depth?4:!event?5:0;
}

/* SHA-256 over normalized UTF-8 chart bytes. No archive name/metadata dependency. */
static al_u32 rr(al_u32 x,unsigned n){return x>>n|x<<(32-n);}
static void sha_block(al_u32 h[8],const al_u8 *p){
 static const al_u32 k[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
 al_u32 w[64];for(int i=0;i<16;i++)w[i]=(al_u32)p[i*4]<<24|(al_u32)p[i*4+1]<<16|(al_u32)p[i*4+2]<<8|p[i*4+3];
 for(int i=16;i<64;i++){al_u32 a=w[i-15],b=w[i-2];w[i]=w[i-16]+(rr(a,7)^rr(a,18)^(a>>3))+w[i-7]+(rr(b,17)^rr(b,19)^(b>>10));}
 al_u32 a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],q=h[7];
 for(int i=0;i<64;i++){al_u32 t=q+(rr(e,6)^rr(e,11)^rr(e,25))+((e&f)^(~e&g))+k[i]+w[i];al_u32 u=(rr(a,2)^rr(a,13)^rr(a,22))+((a&b)^(a&c)^(b&c));q=g;g=f;f=e;e=d+t;d=c;c=b;b=a;a=t+u;}
 h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=q;
}
void al_sha256(const al_u8 *p,al_u64 n,char hex[65]){
 al_u32 h[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};al_u64 original=n;
 while(n>=64){sha_block(h,p);p+=64;n-=64;}
 al_u8 tail[128];for(int i=0;i<128;i++)tail[i]=0;for(al_u64 i=0;i<n;i++)tail[i]=p[i];tail[n]=128;unsigned used=n<56?64:128;al_u64 bits=original*8;for(int i=0;i<8;i++)tail[used-1-i]=(al_u8)(bits>>(8*i));sha_block(h,tail);if(used==128)sha_block(h,tail+64);
 const char *digits="0123456789abcdef";for(int i=0;i<32;i++){al_u8 v=(al_u8)(h[i/4]>>(24-8*(i%4)));hex[i*2]=digits[v>>4];hex[i*2+1]=digits[v&15];}hex[64]=0;
}
