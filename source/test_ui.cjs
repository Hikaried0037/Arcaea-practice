/* Browser layout/behavior QA. This does not execute WKWebView or iOS UIKit. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');const {Catalog}=require('./catalog.js');
const playwright=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await playwright.chromium.launch({channel:'msedge',headless:true});let checks=[],screens=[];
 const data={songs:{songs:[{idx:0,id:'sayonara',set:'base',title_localized:{en:'Sayonara Hatsukoi'},artist:'REDSHiFT',difficulties:[{ratingClass:2,rating:7}]},{idx:1,id:'old_import',set:'arcprac_another',title_localized:{en:'Old imported chart'},artist:'Test',difficulties:[{ratingClass:3,rating:12}]}]},packs:{packs:[Catalog.newPack('base','Arcaea','arcaea'),Catalog.newPack('arcprac_another','Another','arcaea')]}};
 for(const size of [{width:1194,height:834},{width:834,height:1194},{width:375,height:667},{width:667,height:375},{width:2560,height:1600}]){
  const page=await browser.newPage({viewport:size});let errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(({data})=>{window.sent=[];window.webkit={messageHandlers:{library:{postMessage:m=>{window.sent.push(m);if(m.action==='refresh')setTimeout(()=>window.receive({type:'catalog',data,covers:{}}),10);else if(m.action==='commit')setTimeout(()=>window.receive({type:'catalog',data:JSON.parse(m.masterText),covers:{}}),10);}}}};},{data});
  await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);await page.getByRole('button',{name:'Arcaea',exact:true}).waitFor();await page.waitForTimeout(100);
  const migrated=await page.evaluate(()=>window.sent.find(m=>m.action==='commit'));assert.ok(migrated);assert.equal(JSON.parse(migrated.songText).songs[1].set,'base');checks.push(size.width+'x'+size.height+'_automatic_migration');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);checks.push(size.width+'x'+size.height+'_no_horizontal_overflow');
  const nav=await page.locator('nav').boundingBox(),main=await page.locator('main').boundingBox();assert.ok(nav.y+nav.height<=main.y);assert.ok(main.height>100);checks.push(size.width+'x'+size.height+'_header_does_not_overlap_content');
  await page.getByRole('button',{name:'Arcaea',exact:false}).last().click();await page.getByRole('button',{name:'更换封面',exact:true}).waitFor();assert.ok((await page.locator('.songs').innerText()).includes('Beyond 12'));checks.push(size.width+'x'+size.height+'_pack_opens_and_displays_available_chart_difficulty');
  await page.getByRole('button',{name:'删除',exact:true}).last().click();await page.locator('#confirm').click();await page.waitForTimeout(100);assert.equal(await page.locator('.song').count(),1);checks.push(size.width+'x'+size.height+'_song_delete_commits');
  await page.getByRole('button',{name:'新建曲包',exact:true}).click();await page.locator('dialog input').fill('测试曲包');await page.locator('#confirm').click();await page.waitForTimeout(100);assert.ok((await page.locator('#content').innerText()).includes('测试曲包'));checks.push(size.width+'x'+size.height+'_pack_creation');
  const file='ui-'+size.width+'x'+size.height+'.png';await page.screenshot({path:path.join(__dirname,file)});screens.push(file);assert.deepEqual(errors,[]);checks.push(size.width+'x'+size.height+'_no_script_errors');await page.close();
 }
 await browser.close();fs.writeFileSync(path.join(__dirname,'ui-regression.json'),JSON.stringify({passed:true,checks:checks.length,cases:checks,screenshots:screens,scope:'Microsoft Edge desktop responsive layout and JS behavior; not iOS WKWebView or actual native catalog display.'},null,2));console.log('UI regression PASS',checks.length);
})().catch(e=>{console.error(e);process.exit(1)});
