'use strict';
/* Port of the user's Android LibraryCatalog / ChartArchive behavior.
 * Pure data operations: no filesystem, native pointers, networking or UI. */
const ArcCatalog = (() => {
 const copy=x=>JSON.parse(JSON.stringify(x));
 const safe=s=>typeof s==='string'&&/^[a-zA-Z0-9_-]{1,80}$/.test(s);
 const builtins=new Set(['arcaea','mainstory','mainstory2','sidestory','collab','collaboration','variety','shortstory','extend','customize']);
 const title=x=>{const n=x.name_localized||x.title_localized||{};return n['zh-Hans']||n['zh-Hant']||n.en||n.ja||x.id||'';};
 const requireName=s=>{if(typeof s!=='string'||!s.trim()||s.length>120)throw Error('名称不能为空，且不能超过 120 字');return s.trim();};
 const finite=(x,fallback)=>{const n=Number(x);return Number.isFinite(n)?n:fallback;};
 const localized=(x,fallback)=>{const out={};if(x&&typeof x==='object'&&!Array.isArray(x))for(const [k,v] of Object.entries(x))if(typeof v==='string')out[k]=v;if(!Object.keys(out).length)out.en=typeof fallback==='string'?fallback:'Imported chart';return out;};
 class Catalog {
  constructor(data){
   this.data=copy(data);this.migrated=!!this.data.practice_restore_bundled;this.restoredBundled=this.migrated;delete this.data.practice_restore_bundled;
   if(!this.data.songs||!Array.isArray(this.data.songs.songs)||!this.data.packs||!Array.isArray(this.data.packs.packs))throw Error('曲库结构无效，已保留原文件');
   for(const s of this.songs)if(s.set==='arcprac_another'){s.set='base';if(s.difficulties?.some(d=>d.ratingClass===3))s.byd_local_unlock=true;this.migrated=true;}
   const old=this.packs.length;this.data.packs.packs=this.packs.filter(p=>p.id!=='arcprac_another');this.migrated ||=old!==this.packs.length;
   if(!this.pack('base')){this.packs.unshift(Catalog.newPack('base','Arcaea','arcaea'));this.migrated=true;}
   if(this.songs.some(s=>s.set==='single')&&!this.pack('single')){const p=Catalog.newPack('single','Memory Archive','arcaea');p.practice_virtual=true;this.packs.push(p);}
   // Keep the earliest active local record. Archive metadata, never delete assets.
   const fingerprints=new Set(),kept=[];this.duplicatesRemoved=0;
   for(const song of this.songs){const hashes=song.practice_chart_hashes;const valid=Array.isArray(hashes)&&hashes.length&&hashes.every(h=>typeof h==='string'&&/^[a-f0-9]{64}$/.test(h));const key=valid?[...new Set(hashes)].sort().join(':'):null;
    if(song.id?.startsWith('local_')&&key&&fingerprints.has(key)){const archive=(this.data.songs.practice_duplicate_archive ||= []);if(!archive.some(x=>x.id===song.id))archive.push(copy(song));this.duplicatesRemoved++;this.migrated=true;continue;}
    if(song.id?.startsWith('local_')&&key)fingerprints.add(key);kept.push(song);
   }
   this.data.songs.songs=kept;
   this.validate();
  }
  get songs(){return this.data.songs.songs;}
  get packs(){return this.data.packs.packs;}
  pack(id){return this.packs.find(p=>p.id===id);}
  sections(){const defs=this.data.packs.practice_sections||[];const m=new Map(defs.map(d=>[d.id,title(d)]));for(const p of this.packs)if(!m.has(p.section||'arcaea'))m.set(p.section||'arcaea',({arcaea:'Arcaea',mainstory:'主线故事',mainstory2:'主线故事 II',sidestory:'支线故事',collab:'联动曲包',collaboration:'联动曲包',variety:'曲风精选',shortstory:'短篇故事',extend:'World Extend',customize:'自定义'})[p.section]||p.section||'Arcaea');return [...m].map(([id,name])=>({id,name}));}
  validate(){
   for(const [list,label] of [[this.songs,'歌曲'],[this.packs,'曲包']]){const seen=new Set();for(const x of list){if(!safe(x.id)||seen.has(x.id))throw Error(label+' ID 无效或重复');seen.add(x.id);}}
   for(const s of this.songs){if(!this.pack(s.set||'base'))throw Error('歌曲所属曲包不存在：'+title(s));if(!Array.isArray(s.difficulties))throw Error('歌曲难度列表无效');}
   return this;
  }
  static newPack(id,name,section){if(!safe(id)||!safe(section))throw Error('曲包或分类 ID 无效');return {id,section,plus_character:-1,cost:0,is_extend_pack:false,custom_banner:false,cutout_pack_image:true,name_localized:{en:requireName(name)},description_localized:{en:''}};}
  addPack(id,name,section){if(this.pack(id))throw Error('曲包 ID 已存在');this.packs.push(Catalog.newPack(id,name,section));return id;}
  addSection(id,name){if(!safe(id)||this.sections().some(s=>s.id===id))throw Error('分类 ID 无效或重复');(this.data.packs.practice_sections ||= []).push({id,name_localized:{en:requireName(name)}});return id;}
  descendants(id){const ids=new Set([id]);let changed;do{changed=false;for(const p of this.packs)if(ids.has(p.pack_parent)&&!ids.has(p.id)){ids.add(p.id);changed=true;}}while(changed);return ids;}
  deleteSong(id){if(!this.songs.some(s=>s.id===id))throw Error('歌曲已不存在');this.data.songs.songs=this.songs.filter(s=>s.id!==id);}
  moveSong(id,pack){if(!this.pack(pack))throw Error('目标曲包已不存在');const s=this.songs.find(s=>s.id===id);if(!s)throw Error('歌曲已不存在');s.set=pack;}
  deletePack(id,contents){if(id==='base')throw Error('Arcaea 是默认导入曲包，请保留该入口；可以删除其中的歌曲');if(!this.pack(id))throw Error('曲包已不存在');const ids=this.descendants(id);this.data.packs.packs=this.packs.filter(p=>!ids.has(p.id));if(contents)this.data.songs.songs=this.songs.filter(s=>!ids.has(s.set));else for(const s of this.songs)if(ids.has(s.set))s.set='base';}
  movePack(id,section){if(!this.sections().some(s=>s.id===section))throw Error('分类已不存在');for(const p of this.packs)if(this.descendants(id).has(p.id))p.section=section;}
  deleteSection(id,contents){if(id==='arcaea')throw Error('Arcaea 是默认分类，请保留该入口');const ids=new Set(this.packs.filter(p=>p.section===id).flatMap(p=>[...this.descendants(p.id)]));if(contents){this.data.packs.packs=this.packs.filter(p=>!ids.has(p.id));this.data.songs.songs=this.songs.filter(s=>!ids.has(s.set));}else for(const p of this.packs)if(ids.has(p.id))p.section='arcaea';this.data.packs.practice_sections=(this.data.packs.practice_sections||[]).filter(s=>s.id!==id);}
  runtime(){const r=copy(this.data);r.packs.packs=r.packs.packs.filter(p=>!(p.id==='single'&&p.practice_virtual));delete r.packs.practice_sections;for(const p of r.packs.packs)if(!builtins.has(p.section))p.section='arcaea';return r;}
  importSong(prepared,pack='base'){
   if(!this.pack(pack))throw Error('目标曲包已不存在');
   let meta=JSON.parse(prepared.metadataRaw||'{}');if(Array.isArray(meta)) {if(meta.length!==1)throw Error('一次只导入一首歌曲');meta=meta[0];}else if(Array.isArray(meta.songs)){if(meta.songs.length!==1)throw Error('一次只导入一首歌曲');meta=meta.songs[0];}
   if(!meta||typeof meta!=='object'||Array.isArray(meta))throw Error('谱面信息必须是 JSON 对象');
   if(!safe(prepared.id)||!prepared.id.startsWith('local_')||this.songs.some(s=>s.id===prepared.id))throw Error('导入事务 ID 无效');
   const bgs=new Set(prepared.backgrounds||[]);const checkBG=o=>{for(const key of ['bg','bg_inverse'])if(o[key]&&(!safe(o[key])||!bgs.has(o[key])))throw Error('游戏内不存在背景：'+o[key]);};checkBG(meta);
   const hashes=prepared.chartHashes;
   if(hashes!==undefined){if(!Array.isArray(hashes)||!hashes.length||hashes.some(h=>typeof h!=='string'||!/^[a-f0-9]{64}$/.test(h)))throw Error('谱面内容校验信息无效');for(const song of this.songs)if(Array.isArray(song.practice_chart_hashes)&&hashes.some(h=>song.practice_chart_hashes.includes(h)))throw Error('相同谱面已存在于曲库，不能重复导入');}
   const s=copy(meta);s.id=prepared.id;s.idx=Math.max(-1,...this.songs.map((s,i)=>Number.isSafeInteger(s.idx)?s.idx:i))+1;s.set=pack;s.purchase='';if(hashes)s.practice_chart_hashes=[...new Set(hashes)];s.remote_dl=false;s.world_unlock=false;
   s.title_localized=localized(meta.title_localized,meta.title);s.artist=typeof meta.artist==='string'?meta.artist:'';s.bpm=String(meta.bpm||'120');s.bpm_base=finite(meta.bpm_base,120)||120;s.side=[0,1,2].includes(Number(meta.side))?Number(meta.side):0;s.bg=meta.bg||(s.side?'base_conflict':'base_light');
   if(!bgs.has(s.bg))throw Error('默认背景资源缺失');s.audioPreview=Math.max(0,Math.floor(finite(meta.audioPreview,0)));s.audioPreviewEnd=Math.max(s.audioPreview+1,Math.floor(finite(meta.audioPreviewEnd,15000)));s.date=Math.floor(Date.now()/1000);s.version=typeof meta.version==='string'&&meta.version?meta.version:'1.0';
   const source=Array.isArray(meta.difficulties)?meta.difficulties.filter(d=>d&&typeof d==='object'&&!Array.isArray(d)):[];const highest=Math.max(finite(meta.rating,9)||9,...source.map(d=>finite(d.rating,0)));
   if(!Array.isArray(prepared.chartClasses)||!prepared.chartClasses.length||new Set(prepared.chartClasses).size!==prepared.chartClasses.length)throw Error('没有可用谱面');
   s.difficulties=prepared.chartClasses.slice().sort().map(c=>{if(!Number.isInteger(c)||c<0||c>4)throw Error('难度编号无效');const d=copy(source.find(d=>d.ratingClass===c)||{});checkBG(d);d.ratingClass=c;d.rating=Math.floor(finite(d.rating,highest));if(d.rating<=0)d.rating=Math.floor(highest);if(d.rating>20)throw Error('谱面等级超出合理范围');if('ratingPlus'in d)d.ratingPlus=d.ratingPlus===true;d.chartDesigner=typeof d.chartDesigner==='string'?d.chartDesigner:(typeof meta.chartDesigner==='string'?meta.chartDesigner:'');d.jacketDesigner=typeof d.jacketDesigner==='string'?d.jacketDesigner:(typeof meta.jacketDesigner==='string'?meta.jacketDesigner:'');if(d.title_localized)d.title_localized=localized(d.title_localized,s.title_localized.en);d.world_unlock=false;d.hidden_until='';if(d.jacketOverride)d.jacketOverride=false;return d;});
   if(s.difficulties.some(d=>d.ratingClass===3))s.byd_local_unlock=true;
   this.songs.push(s);return s;
  }
 }
 return {Catalog,title,safe,copy};
})();
if(typeof module!=='undefined')module.exports=ArcCatalog;
