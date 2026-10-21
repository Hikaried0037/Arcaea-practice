/* SDK-independent Objective-C runtime bridge, ARM64 iOS.
 * UIKit/Foundation/WebKit are system frameworks loaded by the dylib dependencies.
 * Catalog behavior lives in catalog.js; no legacy importArchive code is called. */
#include "archive.h"
typedef void *ID;typedef unsigned long U;typedef long I;typedef double D;
typedef struct{D x,y;} Point;typedef struct{D w,h;} Size;typedef struct{Point p;Size s;} Rect;
extern ID objc_getClass(const char*);extern ID sel_registerName(const char*);extern void objc_msgSend(void);
extern ID objc_allocateClassPair(ID,const char*,U);extern int class_addMethod(ID,ID,void*,const char*);extern void objc_registerClassPair(ID);
extern ID objc_getProtocol(const char*);extern int class_addProtocol(ID,ID);
extern ID objc_autoreleasePoolPush(void);extern void objc_autoreleasePoolPop(ID);
extern void *malloc(U);extern void free(void*);extern void *memcpy(void*,const void*,U);extern void *memset(void*,int,U);
extern U strlen(const char*);extern int strcmp(const char*,const char*);extern int snprintf(char*,U,const char*,...);
extern int memcmp(const void*,const void*,U);
extern void dispatch_async_f(void*,void*,void(*)(void*));extern char _dispatch_main_q;extern void *dispatch_get_global_queue(long,U);
extern void UIGraphicsBeginImageContextWithOptions(Size,int,D);extern void UIGraphicsEndImageContext(void);extern ID UIGraphicsGetImageFromCurrentImageContext(void);extern ID UIImagePNGRepresentation(ID);extern ID UIImageJPEGRepresentation(ID,D);
extern U CGImageGetWidth(void*);extern U CGImageGetHeight(void*);
typedef struct{unsigned char*next_in;unsigned int avail_in;U total_in;unsigned char*next_out;unsigned int avail_out;U total_out;char*msg;void*state;void*(*zalloc)(void*,unsigned int,unsigned int);void(*zfree)(void*,void*);void*opaque;int data_type;U adler,reserved;} ZStream;
extern const char*zlibVersion(void);extern int inflateInit2_(ZStream*,int,const char*,int);extern int inflate(ZStream*,int);extern int inflateEnd(ZStream*);extern U crc32(U,const unsigned char*,unsigned int);
static ID S(const char*s){return ((ID(*)(ID,ID,const char*))objc_msgSend)(objc_getClass("NSString"),sel_registerName("stringWithUTF8String:"),s);}
static ID C(const char*s){return objc_getClass(s);}static ID sel(const char*s){return sel_registerName(s);}
static ID m0(ID o,const char*s){return ((ID(*)(ID,ID))objc_msgSend)(o,sel(s));}
static ID m1(ID o,const char*s,ID a){return ((ID(*)(ID,ID,ID))objc_msgSend)(o,sel(s),a);}
static ID m2(ID o,const char*s,ID a,ID b){return ((ID(*)(ID,ID,ID,ID))objc_msgSend)(o,sel(s),a,b);}
static ID m3(ID o,const char*s,ID a,ID b,ID c){return ((ID(*)(ID,ID,ID,ID,ID))objc_msgSend)(o,sel(s),a,b,c);}
static ID m4(ID o,const char*s,ID a,ID b,ID c,ID d){return ((ID(*)(ID,ID,ID,ID,ID,ID))objc_msgSend)(o,sel(s),a,b,c,d);}
static ID keep(ID o){return m0(o,"retain");}static void drop(ID o){m0(o,"release");}
static const char*utf(ID o){return o&&(U)m1(o,"isKindOfClass:",C("NSString"))?(const char*)m0(o,"UTF8String"):0;}static U num(ID o){return (U)m0(o,"unsignedLongLongValue");}
static int kind(ID o,const char*name){return o&&(U)m1(o,"isKindOfClass:",C(name));}
static ID dict(void){return m0(C("NSMutableDictionary"),"dictionary");}static ID array(void){return m0(C("NSMutableArray"),"array");}
static ID get(ID o,const char*k){return kind(o,"NSDictionary")?m1(o,"objectForKey:",S(k)):0;}
static void put(ID o,const char*k,ID v){if(v)m2(o,"setObject:forKey:",v,S(k));}
static void add(ID a,ID o){if(o)m1(a,"addObject:",o);}static U count(ID a){return (U)m0(a,"count");}static ID at(ID a,U i){return m1(a,"objectAtIndex:",(ID)i);}
static ID number(U n){return m1(C("NSNumber"),"numberWithUnsignedLongLong:",(ID)n);}
static ID path(ID a,ID b){return m1(a,"stringByAppendingPathComponent:",b);}static ID subpath(ID a,const char*b){return path(a,S(b));}
static ID data(ID p){return m3(C("NSData"),"dataWithContentsOfFile:options:error:",p,0,0);}static U length(ID d){return (U)m0(d,"length");}
static ID bytes(const void*p,U n){return m2(C("NSData"),"dataWithBytes:length:",(ID)p,(ID)n);}
static ID textData(ID s){return m1(s,"dataUsingEncoding:",(ID)4);}
static ID text(ID d){return m0(m2(m0(C("NSString"),"alloc"),"initWithData:encoding:",d,(ID)4),"autorelease");}
static ID json(ID d){if(!d)return 0;ID error=0;return m3(C("NSJSONSerialization"),"JSONObjectWithData:options:error:",d,(ID)1,&error);}
static ID encode(ID o){ID error=0;return m3(C("NSJSONSerialization"),"dataWithJSONObject:options:error:",o,(ID)3,&error);}
static ID fm(void){return m0(C("NSFileManager"),"defaultManager");}
static int mkdirs(ID p){return (U)m4(fm(),"createDirectoryAtPath:withIntermediateDirectories:attributes:error:",p,(ID)1,0,0);}
static int writeData(ID p,ID d){return d&&mkdirs(m0(p,"stringByDeletingLastPathComponent"))&&(U)m3(d,"writeToFile:options:error:",p,(ID)1,0);}
static int exists(ID p){return (U)m1(fm(),"fileExistsAtPath:",p);}
static int safe(const char*s){if(!s||!*s||strlen(s)>80)return 0;for(;*s;s++)if(!((*s>='a'&&*s<='z')||(*s>='A'&&*s<='Z')||(*s>='0'&&*s<='9')||*s=='_'||*s=='-'))return 0;return 1;}
static ID uuid(const char*prefix){ID u=m0(m0(C("NSUUID"),"UUID"),"UUIDString");u=m2(u,"stringByReplacingOccurrencesOfString:withString:",S("-"),S(""));u=m0(u,"lowercaseString");return m1(S(prefix),"stringByAppendingString:",u);}
static ID root,bundle,bridge,window,previousWindow,controller,web,operation,pendingID,pendingDir,pickPack,oldMaster,currentMaster,activePicker,pendingHashes,pendingBackgrounds;
static int busy,pickMode,dirty,pendingBackgroundOnly;static const char *failure;
extern int arc_library_reload_request;
static void fail(const char*s){if(!failure)failure=s;}
static ID resource(const char*relative){ID d=data(subpath(subpath(root,"library"),relative));return d?d:data(subpath(bundle,relative));}
static ID image(ID d){if(!d||length(d)>32*1024*1024)return 0;ID im=m1(C("UIImage"),"imageWithData:",d);void*cg=m0(im,"CGImage");if(!cg)return 0;U w=CGImageGetWidth(cg),h=CGImageGetHeight(cg);if(!w||!h||w>8192||h>8192||w*h>16777216)return 0;return im;}
static ID render(ID im,D width,D height,int png,int fill){
 if(!im)return 0;void*cg=m0(im,"CGImage");D sw=CGImageGetWidth(cg),sh=CGImageGetHeight(cg);D w=width,h=height;
 if(fill){D scale=width/sw>height/sh?width/sw:height/sh;w=sw*scale;h=sh*scale;}
 UIGraphicsBeginImageContextWithOptions((Size){width,height},1,1);
 ((void(*)(ID,ID,Rect))objc_msgSend)(im,sel("drawInRect:"),(Rect){{(width-w)/2,(height-h)/2},{w,h}});
 ID output=png?UIImagePNGRepresentation(UIGraphicsGetImageFromCurrentImageContext()):UIImageJPEGRepresentation(UIGraphicsGetImageFromCurrentImageContext(),.95);keep(output);UIGraphicsEndImageContext();return m0(output,"autorelease");
}
static ID activeDir(void){ID a=json(data(subpath(root,"active.json")));ID g=get(a,"catalog");if(!kind(g,"NSString")||!safe(utf(g))||!(U)m1(g,"hasPrefix:",S("generation_")))return 0;return path(subpath(root,"catalog"),g);}
// Full-release marker opts in once; imported records and their IDs remain intact.
__attribute__((noinline)) static ID restoreBundledCatalog(ID model){
 if(!exists(subpath(bundle,"ArcLibrary/restore-bundled-catalog"))||exists(subpath(root,"full-catalog-restored-r22")))return model;
 ID bundledSongs=get(json(data(subpath(bundle,"songs/songlist"))),"songs"),bundledPacks=get(json(data(subpath(bundle,"songs/packlist"))),"packs");
 ID songs=get(get(model,"songs"),"songs"),packs=get(get(model,"packs"),"packs");if(!kind(bundledSongs,"NSArray")||!kind(bundledPacks,"NSArray"))return model;
 if(!exists(subpath(root,"ArcLibrary-pre-full-restore.json"))&&!writeData(subpath(root,"ArcLibrary-pre-full-restore.json"),encode(model)))return model;
 for(int k=0;k<2;k++){ID source=k?bundledPacks:bundledSongs,target=k?packs:songs,seen=m0(C("NSMutableSet"),"set");for(U j=0;j<count(target);j++)m1(seen,"addObject:",get(at(target,j),"id"));for(U j=0;j<count(source);j++){ID entry=at(source,j),id=get(entry,"id");if(!(U)m1(seen,"containsObject:",id)){add(target,entry);m1(seen,"addObject:",id);}}}
 // Index is presentation order; IDs continue to identify imported charts/scores.
 for(U j=0;j<count(songs);j++)put(at(songs,j),"idx",number(j));put(model,"practice_restore_bundled",number(1));return model;
}
static ID loadMaster(void){
 ID active=activeDir(),saved=active?json(data(subpath(active,"ArcLibrary.json"))):0;if(kind(get(saved,"songs"),"NSDictionary")&&kind(get(saved,"packs"),"NSDictionary"))return restoreBundledCatalog(saved);
 ID songs=active?json(data(subpath(active,"songs/songlist"))):0,packs=active?json(data(subpath(active,"songs/packlist"))):0;
 if(!kind(get(songs,"songs"),"NSArray"))songs=json(data(subpath(bundle,"songs/songlist")));
 if(!kind(get(packs,"packs"),"NSArray"))packs=json(data(subpath(bundle,"songs/packlist")));
 if(!kind(get(songs,"songs"),"NSArray")||!kind(get(packs,"packs"),"NSArray")){fail("曲库原始列表无法读取，未改动已有数据");return 0;}
 ID d=dict();put(d,"songs",songs);put(d,"packs",packs);return restoreBundledCatalog(d);
}
static ID backgrounds(void){ID list=array();for(int k=0;k<2;k++){ID p=subpath(k?bundle:subpath(root,"library"),"img/bg/1080");ID files=m2(fm(),"contentsOfDirectoryAtPath:error:",p,0);for(U i=0;i<count(files);i++){ID n=at(files,i);ID e=m0(n,"lowercaseString");if((U)m1(e,"hasSuffix:",S(".jpg"))||(U)m1(e,"hasSuffix:",S(".png")))add(list,m0(n,"stringByDeletingPathExtension"));}}return list;}
static ID coverFor(ID pack){const char*id=utf(get(pack,"id"));if(!safe(id))return 0;char p[220];ID name=get(pack,"img");ID result=0;
 if(kind(name,"NSString")){const char*s=utf(name);if(s&&strlen(s)<160&&!m1(name,"containsString:",S("/"))&&!m1(name,"containsString:",S(".."))){snprintf(p,sizeof(p),"songs/pack/%s",s);result=resource(p);if(!result){snprintf(p,sizeof(p),"songs/pack/1080_%s",s);result=resource(p);}}}
 if(!result){snprintf(p,sizeof(p),"songs/pack/1080_select_%s.png",id);result=resource(p);}if(!result)result=resource("songs/pack/1080_select_base.png");
 ID png=render(image(result),112,199,1,1);if(!png)return 0;return m1(S("data:image/png;base64,"),"stringByAppendingString:",m1(png,"base64EncodedStringWithOptions:",0));
}
static ID decodeText(ID d);
static ID normalizeChart(ID d){ID t=decodeText(d);if(!t)return 0;t=m2(t,"stringByReplacingOccurrencesOfString:withString:",S("\r\n"),S("\n"));return textData(m2(t,"stringByReplacingOccurrencesOfString:withString:",S("\r"),S("\n")));}
static ID chartHash(ID raw){ID normalized=normalizeChart(raw);if(!normalized||length(normalized)>8*1024*1024)return 0;char hex[65];al_sha256(m0(normalized,"bytes"),length(normalized),hex);return S(hex);}
__attribute__((noinline)) static ID songHashes(ID song){ID result=array();const char*key=utf(get(song,"id"));if(!safe(key))return result;for(int c=0;c<5;c++){ID pool=objc_autoreleasePoolPush();char f[140];snprintf(f,sizeof(f),"songs/%s",key);ID dir=subpath(subpath(root,"library"),f);char name[8];snprintf(name,sizeof(name),"%d.aff",c);ID raw=data(subpath(dir,name));if(!raw)raw=data(subpath(subpath(bundle,f),name));if(raw){ID hash=chartHash(raw);if(hash&&!(U)m1(result,"containsObject:",hash))add(result,hash);}objc_autoreleasePoolPop(pool);}return result;}
__attribute__((noinline)) static int duplicateCharts(ID hashes,ID model){ID songs=get(get(model,"songs"),"songs");for(U i=0;i<count(songs);i++){ID old=songHashes(at(songs,i));for(U j=0;j<count(hashes);j++)if((U)m1(old,"containsObject:",at(hashes,j)))return 1;}return 0;}
static U migrateBackgrounds(void);
static ID snapshot(void){U repaired=migrateBackgrounds();ID result=dict(),model=loadMaster();if(!model)return 0;drop(currentMaster);currentMaster=keep(encode(model));put(result,"type",S("catalog"));if(repaired)put(result,"backgroundsRepaired",number(repaired));put(result,"data",model);ID songs=get(get(model,"songs"),"songs");for(U i=0;i<count(songs);i++)if((U)m1(get(at(songs,i),"id"),"hasPrefix:",S("local_")))put(at(songs,i),"practice_chart_hashes",songHashes(at(songs,i)));put(result,"data",model);ID covers=dict(),packs=get(get(model,"packs"),"packs");for(U i=0;i<count(packs);i++){ID p=at(packs,i);const char*key=utf(get(p,"id"));if(safe(key))put(covers,key,coverFor(p));}put(result,"covers",covers);return result;}
static void notify(ID o){if(web){ID raw=text(encode(o));if(!raw)return;ID js=m1(S("window.receive("),"stringByAppendingString:",raw);js=m1(js,"stringByAppendingString:",S(");"));m2(web,"evaluateJavaScript:completionHandler:",js,0);}}
static void sendOnMain(void*ctx){ID o=ctx;busy=0;drop(operation);operation=0;notify(o);drop(o);}
static void send(ID object){dispatch_async_f(&_dispatch_main_q,keep(object),sendOnMain);}
static ID errorResult(const char*s){ID o=dict();put(o,"type",S("error"));put(o,"message",S(s?s:"操作失败，原曲库保持不变"));return o;}
static int catalogValid(ID model){ID songs=get(get(model,"songs"),"songs"),packs=get(get(model,"packs"),"packs");if(!kind(songs,"NSArray")||!kind(packs,"NSArray")||count(songs)>20000||count(packs)>2000)return 0;
 for(int k=0;k<2;k++){ID list=k?packs:songs;ID seen=m0(C("NSMutableSet"),"set");for(U i=0;i<count(list);i++){ID x=at(list,i),id=get(x,"id");if(!kind(id,"NSString")||!safe(utf(id))||(U)m1(seen,"containsObject:",id))return 0;m1(seen,"addObject:",id);if(!k){ID set=get(x,"set"),diffs=get(x,"difficulties");if(!safe(utf(set))||!kind(diffs,"NSArray")||!count(diffs)||count(diffs)>5)return 0;int found=0;for(U j=0;j<count(packs);j++)if((U)m1(set,"isEqual:",get(at(packs,j),"id")))found=1;if(!found)return 0;}}}return 1;}
static int ensureCovers(ID packs){
 for(U i=0;i<count(packs);i++){ID p=at(packs,i),name=get(p,"img"),id=get(p,"id");const char*key=utf(id);if(!safe(key))return 0;ID png=0;
  if(kind(name,"NSString")){const char*s=utf(name);if(!s||strlen(s)>160||(U)m1(name,"containsString:",S("/"))||(U)m1(name,"containsString:",S("..")))return 0;char f[240];snprintf(f,sizeof(f),"songs/pack/%s",s);png=resource(f);}
  if(!png&&(U)m1(id,"hasPrefix:",S("custom_")))png=resource("songs/pack/1080_select_base.png");
  if(png){const char*prefix[]={"songs/pack/select_","songs/pack/1080_select_","songs/pack/1080/select_"};for(int j=0;j<3;j++){char f[240];snprintf(f,sizeof(f),"%s%s.png",prefix[j],key);if(!writeData(subpath(subpath(root,"library"),f),png))return 0;}}
 }return 1;
}
static int commitBackgrounds(void);
__attribute__((noinline)) static int commit(ID op){
 ID masterText=get(op,"masterText"),songText=get(op,"songText"),packText=get(op,"packText");if(!kind(masterText,"NSString")||!kind(songText,"NSString")||!kind(packText,"NSString")||length(textData(masterText))>24*1024*1024){fail("曲库事务格式无效");return 0;}
 ID master=json(textData(masterText)),songs=json(textData(songText)),packs=json(textData(packText));if(!catalogValid(master)||!kind(get(songs,"songs"),"NSArray")||!kind(get(packs,"packs"),"NSArray")){fail("曲库结构校验失败");return 0;}
 // The runtime copy must have the same songs and pack IDs; only section mapping differs.
 if(!(U)m1(get(master,"songs"),"isEqual:",songs)||count(get(get(master,"packs"),"packs"))!=count(get(packs,"packs"))+num(get(op,"virtualPackCount"))){fail("运行列表与管理列表不一致");return 0;}
 if(!ensureCovers(get(packs,"packs"))){fail("曲包封面检查或写入失败");return 0;}
 ID stageToken=get(op,"stage");if(stageToken){if(!pendingID||!pendingHashes||!(U)m1(stageToken,"isEqual:",pendingID)){fail("导入预检已过期，请重新选择压缩包");return 0;}if(duplicateCharts(pendingHashes,loadMaster())){fail("相同谱面已存在于曲库，不能重复导入");return 0;}}
 ID gen=uuid("generation_"),dir=path(subpath(root,"catalog"),gen);
 if(!writeData(subpath(dir,"songs/songlist"),textData(songText))||!writeData(subpath(dir,"songs/packlist"),textData(packText))||!writeData(subpath(dir,"ArcLibrary.json"),textData(masterText))){fail("无法写入曲库新版本");return 0;}
 ID unlock=resource("songs/unlocks");if(!unlock)unlock=textData(S("{}"));if(!writeData(subpath(dir,"songs/unlocks"),unlock)){fail("解锁列表写入失败");return 0;}
 ID token=get(op,"stage");if(token&&!commitBackgrounds())return 0;if(token){if(!pendingID||!(U)m1(token,"isEqual:",pendingID)){fail("导入预检已过期，请重新选择压缩包");return 0;}ID dest=path(subpath(root,"library/songs"),pendingID);if(exists(dest)||!mkdirs(m0(dest,"stringByDeletingLastPathComponent"))||!(U)m3(fm(),"moveItemAtPath:toPath:error:",pendingDir,dest,0)){fail("歌曲资源提交失败");return 0;}}
 // A single atomic active.json swap commits complete generation files. Never edit
 // the currently active songlist/packlist in place, and keep resources for undo.
 ID prev=loadMaster();if(prev&&!writeData(subpath(root,"ArcLibrary-undo.json"),encode(prev))){fail("无法保存撤销记录，未切换曲库");return 0;}
 ID a=dict();put(a,"catalog",gen);put(a,"songs",get(songs,"songs"));put(a,"libraryVersion",number(1));if(!writeData(subpath(root,"active.json"),encode(a))){fail("曲库指针提交失败");return 0;}
 if(num(get(op,"bundledRestore")))writeData(subpath(root,"full-catalog-restored-r22"),textData(S("restored")));
 if(token){drop(pendingBackgrounds);pendingBackgrounds=0;drop(pendingHashes);pendingHashes=0;drop(pendingID);pendingID=0;drop(pendingDir);pendingDir=0;}dirty=1;return 1;
}
static ID unzip(ID archive){
 U n=length(archive);const al_u8*b=m0(archive,"bytes");ALZipEntry entries[128];al_u32 countEntries=0;int e=al_zip_scan(b,n,entries,&countEntries);if(e){fail(e==7?"ZIP 含不安全路径":e==9?"压缩包有重复文件名，一次只能导入一首歌曲":"ZIP 结构、格式或大小不符合要求");return 0;}
 ID files=dict();for(al_u32 i=0;i<countEntries;i++){
  ALZipEntry*x=entries+i;void*p=malloc(x->size?x->size:1);if(!p){fail("内存不足");return 0;}int ok=1;
  if(!x->method)memcpy(p,b+x->offset,x->size);else{ZStream z;memset(&z,0,sizeof(z));z.next_in=(void*)(b+x->offset);z.avail_in=x->compressed;z.next_out=p;z.avail_out=x->size?x->size:1;int initialized=inflateInit2_(&z,-15,zlibVersion(),sizeof(z))==0;ok=initialized&&inflate(&z,4)==1&&z.total_out==x->size&&z.total_in==x->compressed;if(initialized)inflateEnd(&z);}
  if(ok)ok=crc32(0,p,x->size)==x->crc;if(!ok){free(p);fail("ZIP 解压或 CRC 校验失败");return 0;}ID key=S(x->name);if(!key){free(p);fail("ZIP 文件名不是有效 UTF-8 编码");return 0;}m2(files,"setObject:forKey:",bytes(p,x->size),key);free(p);
 }return files;
}
static ID pickFile(ID files,const char**names,U total,const char*extension,int imageFile){for(U i=0;i<total;i++){ID d=get(files,names[i]);if(d)return d;}ID keys=m0(files,"allKeys"),result=0;for(U i=0;i<count(keys);i++){ID name=at(keys,i);const char*s=utf(name);U n=strlen(s);int match=n>4&&(!strcmp(s+n-4,extension)||(imageFile&&!strcmp(s+n-4,".png"))||(imageFile&&n>5&&!strcmp(s+n-5,".jpeg")));if(match){if(result){fail(imageFile?"多个曲绘无法确定，请将主曲绘命名为 base.jpg/png":"多个音乐无法确定，请命名为 base.ogg");return 0;}result=m1(files,"objectForKey:",name);}}return result;}
static ID decodeText(ID d){ID t=text(d);if(!t)t=m0(m2(m0(C("NSString"),"alloc"),"initWithData:encoding:",d,(ID)10),"autorelease");if(!t)t=m0(m2(m0(C("NSString"),"alloc"),"initWithData:encoding:",d,(ID)0x90000100),"autorelease");if(t&&(U)m1(t,"hasPrefix:",S("\xef\xbb\xbf")))t=m1(t,"substringFromIndex:",(ID)1);return t;}
static int builtinBackground(ID id){const char*exts[]={".jpg",".png",".jpeg"};for(int j=0;j<3;j++)if(exists(path(subpath(bundle,"img/bg/1080"),m1(id,"stringByAppendingString:",S(exts[j])))))return 1;return 0;}
static ID backgroundBackup(ID id){return path(subpath(root,"background-backup-r20"),m1(id,"stringByAppendingString:",S(".jpg")));}
static ID restoredMarker(ID id){return path(subpath(root,"background-restored-r21"),id);}
static int repairableBackground(ID id){return !builtinBackground(id)&&exists(backgroundBackup(id))&&!exists(restoredMarker(id));}
static ID backgroundJPEG(ID raw){ID im=image(raw);if(!im)return 0;void*cg=m0(im,"CGImage");const unsigned char*b=m0(raw,"bytes");if(CGImageGetWidth(cg)==1920&&CGImageGetHeight(cg)==1440&&length(raw)>2&&b[0]==255&&b[1]==216)return raw;return render(im,1920,1440,0,1);}
__attribute__((noinline)) static U migrateBackgrounds(void){
 U repaired=0;ID base=subpath(root,"library/img/bg/1080"),files=m2(fm(),"contentsOfDirectoryAtPath:error:",base,0);
 for(U i=0;i<count(files);i++){ID pool=objc_autoreleasePoolPush();ID filename=at(files,i),id=m0(filename,"stringByDeletingPathExtension");if(safe(utf(id))&&!builtinBackground(id)){
  ID target=path(base,filename),raw=data(target),im=image(raw);void*cg=m0(im,"CGImage");if(cg&&CGImageGetWidth(cg)==1920&&CGImageGetHeight(cg)==1080){
   ID backup=backgroundBackup(id),jpg=backgroundJPEG(raw);if(jpg&&(exists(backup)||writeData(backup,raw))&&writeData(path(subpath(root,"library/img/bg"),filename),jpg)&&writeData(target,jpg)){repaired++;dirty=1;}
  }
 }objc_autoreleasePoolPop(pool);}return repaired;
}
// Only metadata-referenced backgrounds are accepted; no arbitrary ZIP files are installed.
static ID metadataSong(ID model){
 if(kind(model,"NSArray")){if(count(model)!=1)return 0;model=at(model,0);}
 ID songs=get(model,"songs");if(songs){if(!kind(songs,"NSArray")||count(songs)!=1)return 0;model=at(songs,0);}
 return kind(model,"NSDictionary")?model:0;
}
static int backgroundRef(ID refs,ID value){if(!value)return 1;if(kind(value,"NSString")&&!*utf(value))return 1;if(!kind(value,"NSString")||!safe(utf(value))){fail("背景 ID 无效");return 0;}if(!(U)m1(refs,"containsObject:",value))add(refs,value);return 1;}
__attribute__((noinline)) static ID prepareBackgrounds(ID files,ID model,ID classes){
 ID song=metadataSong(model),refs=array(),installed=backgrounds(),staged=array();if(!song){fail("谱面信息必须包含一首歌曲");return 0;}
 if(!backgroundRef(refs,get(song,"bg"))||!backgroundRef(refs,get(song,"bg_inverse")))return 0;
 ID diffs=get(song,"difficulties");if(kind(diffs,"NSArray"))for(U i=0;i<count(diffs);i++){ID d=at(diffs,i);if(!(U)m1(classes,"containsObject:",get(d,"ratingClass")))continue;if(!backgroundRef(refs,get(d,"bg"))||!backgroundRef(refs,get(d,"bg_inverse")))return 0;}
 if(count(refs)>12){fail("一次导入引用的背景过多");return 0;}
 for(U i=0;i<count(refs);i++){ID id=at(refs,i);if((U)m1(installed,"containsObject:",id)&&!repairableBackground(id))continue;ID stem=m0(id,"lowercaseString"),raw=0;
  const char*exts[]={".jpg",".png",".jpeg"};for(int j=0;j<3&&!raw;j++)raw=m1(files,"objectForKey:",m1(stem,"stringByAppendingString:",S(exts[j])));
  if(!raw){ID large=m1(S("1080_"),"stringByAppendingString:",stem);for(int j=0;j<3&&!raw;j++)raw=m1(files,"objectForKey:",m1(large,"stringByAppendingString:",S(exts[j])));}
  if(!raw){if((U)m1(installed,"containsObject:",id))continue;fail("背景不存在，ZIP 需附带与 bg 同名的 JPG/PNG 图片");return 0;}
  ID im=image(raw);if(!im){fail("ZIP 背景图片无效或尺寸过大");return 0;}ID jpg=backgroundJPEG(raw);if(!jpg){fail("背景图片转换失败");return 0;}
  ID filename=m1(id,"stringByAppendingString:",S(".jpg"));if(!writeData(path(subpath(pendingDir,"_backgrounds"),filename),jpg)){fail("背景图片暂存失败");return 0;}add(staged,id);add(installed,id);
 }
 drop(pendingBackgrounds);pendingBackgrounds=keep(staged);return installed;
}
__attribute__((noinline)) static int commitBackgrounds(void){
 ID installed=backgrounds();for(U i=0;i<count(pendingBackgrounds);i++){ID id=at(pendingBackgrounds,i);int restoring=repairableBackground(id);if((U)m1(installed,"containsObject:",id)&&!restoring)continue;ID filename=m1(id,"stringByAppendingString:",S(".jpg"));ID jpg=data(path(subpath(pendingDir,"_backgrounds"),filename));if(!jpg){fail("暂存背景丢失，请重新选择压缩包");return 0;}
  ID target=path(subpath(root,"library/img/bg/1080"),filename);if(exists(target)&&!restoring)continue;
  // Write canonical 1080 alias last so incomplete writes remain retryable.
  if(!writeData(path(subpath(root,"library/img/bg"),filename),jpg)||!writeData(target,jpg)){fail("背景资源提交失败");return 0;}
  if(restoring&&!writeData(restoredMarker(id),textData(S("restored")))){fail("背景修复标记写入失败，请重试");return 0;}
 }return 1;
}
static ID prepare(ID raw){
 drop(pendingBackgrounds);pendingBackgrounds=0;pendingBackgroundOnly=0;
 ID files=unzip(raw);if(!files)return 0;ID keys=m0(files,"allKeys"),classes=array(),hashes=array();U affs=0;for(U i=0;i<count(keys);i++)if((U)m1(at(keys,i),"hasSuffix:",S(".aff")))affs++;
 if(!affs||affs>5){fail("ZIP 必须包含 1–5 个有效 AFF");return 0;}
 m2(fm(),"removeItemAtPath:error:",subpath(root,"staging"),0);drop(pendingHashes);pendingHashes=0;drop(pendingID);pendingID=keep(uuid("local_"));drop(pendingDir);pendingDir=keep(path(subpath(root,"staging"),pendingID));if(!mkdirs(pendingDir)){fail("无法创建暂存目录");return 0;}
 for(U i=0;i<count(keys);i++){ID name=at(keys,i);const char*s=utf(name);if(!(U)m1(name,"hasSuffix:",S(".aff")))continue;int c=strlen(s)==5&&s[0]>='0'&&s[0]<='4'?s[0]-'0':affs==1?2:-1;if(c<0){fail("多难度 AFF 必须命名 0.aff 至 4.aff");return 0;}ID chart=decodeText(m1(files,"objectForKey:",name));if(!chart||length(textData(chart))>8*1024*1024){fail("AFF 编码无效或尺寸过大");return 0;}
  chart=m2(chart,"stringByReplacingOccurrencesOfString:withString:",S("\r\n"),S("\n"));chart=m2(chart,"stringByReplacingOccurrencesOfString:withString:",S("\r"),S("\n"));ID normalized=textData(chart);int affError=al_aff_validate(m0(normalized,"bytes"),length(normalized));
  if(affError){fail(affError==4?"AFF 括号不匹配":"AFF 缺少有效 AudioOffset、独立分隔行或 timing 事件");return 0;}char filename[10];snprintf(filename,sizeof(filename),"%d.aff",c);if(!writeData(subpath(pendingDir,filename),textData(chart))){fail("AFF 写入暂存目录失败");return 0;}add(classes,number(c));add(hashes,chartHash(normalized));
 }
 int duplicate=duplicateCharts(hashes,loadMaster());pendingHashes=keep(hashes);
 const char*images[]={"base.jpg","base.png","1080_base.jpg","1080_base.png","jacket.jpg","jacket.png","cover.jpg","cover.png"};const char*audio[]={"base.ogg","audio.ogg","music.ogg"};
 ID jacket=pickFile(files,images,8,".jpg",1),music=pickFile(files,audio,3,".ogg",0);if(failure)return 0;ID im=image(jacket);if(!im){fail("必须包含有效 JPG/PNG 曲绘（最大 8192 像素、1600 万像素）");return 0;}if(length(music)<4||memcmp(m0(music,"bytes"),"OggS",4)){fail("必须包含有效 OGG 音乐，不能只改扩展名");return 0;}
 ID jpg=render(im,1080,1080,0,1),thumb=render(im,256,256,0,1);if(!jpg||!thumb){fail("曲绘转换失败");return 0;}if(!writeData(subpath(pendingDir,"base.ogg"),music)||!writeData(subpath(pendingDir,"base.jpg"),jpg)||!writeData(subpath(pendingDir,"1080_base.jpg"),jpg)||!writeData(subpath(pendingDir,"base_256.jpg"),thumb)||!writeData(subpath(pendingDir,"1080_base_256.jpg"),thumb)){fail("音乐或曲绘暂存失败");return 0;}
 const char*metas[]={"songlist.json","songlist.txt","songlist","song.json","song.txt"};ID meta=0;for(U i=0;i<5;i++)if(get(files,metas[i])){if(meta){fail("只允许一份谱面信息文件");return 0;}meta=decodeText(get(files,metas[i]));}if(!meta){for(U i=0;i<count(keys);i++)if((U)m1(at(keys,i),"hasSuffix:",S(".arcproj"))){if(meta){fail("只允许一份谱面信息文件");return 0;}meta=decodeText(m1(files,"objectForKey:",at(keys,i)));}}
 if(!meta)meta=S("{}");ID parsed=json(textData(meta));if(!parsed){fail("谱面信息不是有效 JSON");return 0;}
 ID available=prepareBackgrounds(files,parsed,classes);if(!available)return 0;
 if(duplicate&&!count(pendingBackgrounds)){fail("相同谱面已存在于曲库，不能重复导入");return 0;}pendingBackgroundOnly=duplicate;
 ID o=dict();put(o,"type",S(pendingBackgroundOnly?"backgroundRepair":"prepared"));put(o,"metadataRaw",meta);put(o,"chartClasses",classes);put(o,"chartHashes",hashes);put(o,"id",pendingID);put(o,"backgrounds",available);put(o,"newBackgrounds",pendingBackgrounds);return o;
}
__attribute__((noinline)) static ID prepareCover(ID raw){if(!safe(utf(pickPack))){fail("目标曲包 ID 无效");return 0;}ID im=image(raw);if(!im){fail("封面图片无效或太大");return 0;}ID png=render(im,403,717,1,1);if(!png){fail("封面生成失败");return 0;}ID filename=m1(uuid("practice_"),"stringByAppendingString:",S(".png"));ID base=subpath(root,"library/songs/pack");ID scaled=m1(S("1080_"),"stringByAppendingString:",filename);if(!writeData(path(base,filename),png)||!writeData(path(base,scaled),png)){fail("封面写入失败");return 0;}ID o=dict();put(o,"type",S("cover"));put(o,"pack",pickPack);put(o,"filename",filename);return o;}
__attribute__((noinline)) static int repairBackgrounds(ID op){
 ID stage=get(op,"stage");if(!pendingBackgroundOnly||!pendingID||!stage||!(U)m1(stage,"isEqual:",pendingID)){fail("背景修复预检已过期，请重新选择压缩包");return 0;}
 if(!commitBackgrounds())return 0;m2(fm(),"removeItemAtPath:error:",pendingDir,0);drop(pendingBackgrounds);pendingBackgrounds=0;drop(pendingHashes);pendingHashes=0;drop(pendingID);pendingID=0;drop(pendingDir);pendingDir=0;pendingBackgroundOnly=0;dirty=1;return 1;
}
static void work(void*ctx){ID pool=objc_autoreleasePoolPush();ID op=ctx;failure=0;ID action=get(op,"action"),result=0;
 if((U)m1(action,"isEqual:",S("refresh")))result=snapshot();
 else if((U)m1(action,"isEqual:",S("commit"))){if(commit(op))result=snapshot();}
 else if((U)m1(action,"isEqual:",S("repairBackgrounds"))){if(repairBackgrounds(op))result=snapshot();}
 else if((U)m1(action,"isEqual:",S("undo"))){ID m=json(data(subpath(root,"ArcLibrary-undo.json")));if(m){result=dict();put(result,"type",S("undo"));put(result,"data",m);}else fail("暂无可以撤销的曲库修改");}
 else if((U)m1(action,"isEqual:",S("file"))){ID url=get(op,"url");if(num(get(op,"mode"))==2){drop(pickPack);pickPack=keep(get(op,"pack"));}int scoped=(U)m0(url,"startAccessingSecurityScopedResource");ID raw=m3(C("NSData"),"dataWithContentsOfURL:options:error:",url,(ID)1,0);if(raw&&length(raw)<=268435456ULL)result=num(get(op,"mode"))==2?prepareCover(raw):prepare(raw);else fail("无法读取文件或文件超过 256 MB");if(scoped)m0(url,"stopAccessingSecurityScopedResource");}
 if(!result)result=errorResult(failure);send(result);objc_autoreleasePoolPop(pool);
}
static void start(ID op){if(busy||activePicker)return;busy=1;drop(operation);operation=keep(op);dispatch_async_f(dispatch_get_global_queue(0,0),operation,work);}
// One retained picker at a time. File callbacks may arrive after cancellation;
// only the current picker can start work. No modal or file IO on inactive apps.
static int foreground(void){return (U)m0(m0(C("UIApplication"),"sharedApplication"),"applicationState")==0;}
static int available(ID o,const char*name){return o&&(U)m1(o,"respondsToSelector:",sel(name));}
__attribute__((noinline)) static void closeLibrary(void){if(busy||activePicker)return;
 if(web){ID cc=m0(m0(web,"configuration"),"userContentController");m1(cc,"removeScriptMessageHandlerForName:",S("library"));}
 m1(window,"setHidden:",(ID)1);m0(previousWindow,"makeKeyWindow");drop(window);window=0;controller=0;web=0;drop(previousWindow);previousWindow=0;
}
__attribute__((noinline)) static void pick(int mode,ID pack){
 if(busy||activePicker)return;
 if(!foreground()||!controller||!m0(m0(controller,"view"),"window")||m0(controller,"presentedViewController")){notify(errorResult("当前无法打开文件选择器，请返回前台后重试"));return;}
 if(mode!=1&&mode!=2){notify(errorResult("文件选择类型无效"));return;}
 if(mode==2&&!safe(utf(pack))){notify(errorResult("目标曲包无效，请刷新曲库后重试"));return;}
 // UIKit's selector ends in completion:, unlike WebKit's completionHandler:.
 if(!available(controller,"presentViewController:animated:completion:")){notify(errorResult("系统文件选择接口不可用"));return;}
 ID cls=C("UIDocumentPickerViewController");if(!cls){notify(errorResult("系统文件选择器不可用"));return;}
 ID types=array();add(types,S(mode==2?"public.image":"public.data"));
 ID picker=m2(m0(cls,"alloc"),"initWithDocumentTypes:inMode:",types,0);
 if(!picker){notify(errorResult("无法创建系统文件选择器"));return;}
 pickMode=mode;drop(pickPack);pickPack=keep(pack);activePicker=picker;
 m1(picker,"setDelegate:",bridge);m1(picker,"setModalPresentationStyle:",(ID)0);m1(picker,"setAllowsMultipleSelection:",0);
 m3(controller,"presentViewController:animated:completion:",picker,(ID)1,0);
}
__attribute__((noinline)) static void pickerCancel(ID self,ID cmd,ID picker){(void)self;(void)cmd;
 if(!activePicker||picker!=activePicker)return;drop(activePicker);activePicker=0;ID o=dict();put(o,"type",S("cancel"));notify(o);
}
__attribute__((noinline)) static void picked(ID self,ID cmd,ID picker,ID urls){(void)self;(void)cmd;
 if(!activePicker||picker!=activePicker)return;
 if(!kind(urls,"NSArray")||!count(urls)){pickerCancel(self,cmd,picker);return;}
 ID url=at(urls,0);if(!kind(url,"NSURL")||!(U)m0(url,"isFileURL")){drop(activePicker);activePicker=0;notify(errorResult("文件选择器未返回有效本地文件，请重新选择"));return;}
 ID op=dict();put(op,"action",S("file"));put(op,"url",url);put(op,"mode",number(pickMode));if(pickPack)put(op,"pack",pickPack);
 drop(activePicker);activePicker=0;start(op);
}
__attribute__((noinline)) static void received(ID self,ID cmd,ID content,ID message){(void)self;(void)cmd;(void)content;if(!web)return;ID op=m0(message,"body");if(!kind(op,"NSDictionary"))return;ID action=get(op,"action");if(!kind(action,"NSString"))return;
 if((U)m1(action,"isEqual:",S("close")))closeLibrary();else if((U)m1(action,"isEqual:",S("pickZip")))pick(1,0);else if((U)m1(action,"isEqual:",S("pickCover")))pick(2,get(op,"pack"));else if((U)m1(action,"isEqual:",S("reload"))){if(busy||activePicker||!foreground())return;dirty=0;closeLibrary();/* engine-thread bridge polls this atomic request */__atomic_store_n(&arc_library_reload_request,1,__ATOMIC_RELEASE);}else if((U)m1(action,"isEqual:",S("refresh"))||(U)m1(action,"isEqual:",S("commit"))||(U)m1(action,"isEqual:",S("undo"))||(U)m1(action,"isEqual:",S("repairBackgrounds")))start(op);
}
// Exported state is consumed by the existing engine-loop integration only.
int arc_library_reload_request;
int arc_library_take_reload(void){return __atomic_exchange_n(&arc_library_reload_request,0,__ATOMIC_ACQ_REL);}
void arc_library_open(ID self,ID cmd,ID sender){(void)self;(void)cmd;(void)sender;if(window){m0(window,"makeKeyAndVisible");return;}
 ID pool=objc_autoreleasePoolPush();if(!root){bundle=keep(m0(m0(C("NSBundle"),"mainBundle"),"bundlePath"));ID urls=m2(fm(),"URLsForDirectory:inDomains:",(ID)5,(ID)1);if(!count(urls)){objc_autoreleasePoolPop(pool);return;}root=keep(subpath(m0(at(urls,0),"path"),"ArcPracImports"));mkdirs(root);}
 if(!bridge){ID cls=objc_allocateClassPair(C("NSObject"),"ArcLibraryBridgeV1",0);if(!cls)cls=C("ArcLibraryBridgeV1");else{class_addMethod(cls,sel("userContentController:didReceiveScriptMessage:"),(void*)received,"v@:@@");class_addMethod(cls,sel("documentPicker:didPickDocumentsAtURLs:"),(void*)picked,"v@:@@");class_addMethod(cls,sel("documentPickerWasCancelled:"),(void*)pickerCancel,"v@:@");ID protocol=objc_getProtocol("WKScriptMessageHandler");if(protocol)class_addProtocol(cls,protocol);protocol=objc_getProtocol("UIDocumentPickerDelegate");if(protocol)class_addProtocol(cls,protocol);objc_registerClassPair(cls);}bridge=m0(m0(cls,"alloc"),"init");}
 ID app=m0(C("UIApplication"),"sharedApplication");ID source=m0(sender,"window");if(!source)source=m0(app,"keyWindow");if(!source){ID scenes=m0(m0(app,"connectedScenes"),"allObjects");for(U i=0;i<count(scenes)&&!source;i++){ID sc=at(scenes,i);if((U)m0(sc,"activationState"))continue;ID windows=m0(sc,"windows");for(U j=0;j<count(windows);j++)if((U)m0(at(windows,j),"isKeyWindow"))source=at(windows,j);}}previousWindow=keep(source);ID scene=m0(previousWindow,"windowScene");ID w=m0(C("UIWindow"),"alloc");if(scene)window=m1(w,"initWithWindowScene:",scene);else{Rect rect=((Rect(*)(ID,ID))objc_msgSend)(m0(C("UIScreen"),"mainScreen"),sel("bounds"));window=((ID(*)(ID,ID,Rect))objc_msgSend)(w,sel("initWithFrame:"),rect);}
 ((void(*)(ID,ID,D))objc_msgSend)(window,sel("setWindowLevel:"),1001.0);controller=m0(m0(C("UIViewController"),"alloc"),"init");m1(window,"setRootViewController:",controller);drop(controller);
 ID config=m0(m0(C("WKWebViewConfiguration"),"alloc"),"init");ID cc=m0(config,"userContentController");m2(cc,"addScriptMessageHandler:name:",bridge,S("library"));Rect frame=((Rect(*)(ID,ID))objc_msgSend)(m0(controller,"view"),sel("bounds"));web=((ID(*)(ID,ID,Rect,ID))objc_msgSend)(m0(C("WKWebView"),"alloc"),sel("initWithFrame:configuration:"),frame,config);drop(config);m1(web,"setAutoresizingMask:",(ID)18);m1(web,"setOpaque:",0);m1(m0(controller,"view"),"addSubview:",web);drop(web);
 ID html=subpath(bundle,"ArcLibrary/index.html"),access=subpath(bundle,"ArcLibrary");m2(web,"loadFileURL:allowingReadAccessToURL:",m1(C("NSURL"),"fileURLWithPath:",html),m1(C("NSURL"),"fileURLWithPath:",access));m0(window,"makeKeyAndVisible");objc_autoreleasePoolPop(pool);
}
