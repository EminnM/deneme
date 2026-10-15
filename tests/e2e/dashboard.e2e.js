// usage: DASH_DIR=<folder with dashboard.html, dash_nofix.html, dash_clean.html> node dashboard.e2e.js
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const D=(process.env.DASH_DIR||'.')+'/';
let pass=0, fail=0;
const ok=(c,m)=>{ if(c){pass++;console.log('PASS',m)} else {fail++;console.log('FAIL',m)} };
(async()=>{
  const b=await chromium.launch(); const errs=[];
  const ctx=await b.newContext({viewport:{width:1500,height:950},acceptDownloads:true,permissions:['clipboard-read','clipboard-write']});
  const pg=await ctx.newPage();
  pg.on('pageerror',e=>errs.push(String(e))); pg.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
  await pg.goto('file://'+D+'dashboard.html'); await pg.waitForTimeout(400);

  // header + data
  const stats=await pg.$$eval('.stat b',e=>e.map(x=>x.textContent));
  ok(stats[0]==='41'&&stats[1]==='35'&&stats[2]==='8', 'header stats '+stats.join('/'));
  ok(await pg.$$eval('.th',e=>e.length)===8,'8 slide thumbnails');
  ok(await pg.$$eval('#matrix td.c',e=>e.length)===64,'heatmap has 8x8 cells');
  ok((await pg.textContent('#sugg')).includes('Tool suggestion'),'tool verdict suggestion shown');

  // heatmap click jumps to slide + filters category
  await pg.click('#matrix td.c[data-n="5"][data-c="Lines and arrows"]'); await pg.waitForTimeout(200);
  ok((await pg.textContent('#stitle')).startsWith('Slide 5'),'heatmap click opens slide 5');
  ok(await pg.$eval('.chip.on',e=>e.textContent)==='Lines and arrows','heatmap click applies category filter');
  ok(await pg.$$eval('#issues .iss',e=>e.length)>=1 && (await pg.$$eval('#issues .cat',e=>e.every(x=>x.textContent==='Lines and arrows'))),'issue list filtered to category');
  await pg.click('.chip[data-c=""]'); await pg.waitForTimeout(100);
  const allCount=await pg.$$eval('#issues .iss',e=>e.length);
  ok(allCount>3,'All chip shows every issue on slide 5 ('+allCount+')');

  // tabs
  await pg.click('.tab[data-t="before"]'); ok(await pg.$$eval('#view img',e=>e.length)===1,'Original tab shows one image');
  await pg.click('.tab[data-t="after"]'); ok(await pg.$$eval('#view img',e=>e.length)===1,'After tab shows one image');
  await pg.click('.tab[data-t="compare"]'); ok(await pg.$$eval('#view img',e=>e.length)===2,'Compare tab shows two images');
  const boxes=await pg.$$eval('#view .box',e=>e.length); ok(boxes>0,'markers drawn ('+boxes+')');
  await pg.click('#tb'); ok(await pg.$$eval('#view .box',e=>e.length)===0,'Show markers toggle hides markers');
  await pg.click('#tb'); ok(await pg.$$eval('#view .box',e=>e.length)>0,'toggle shows markers again');

  // marker click highlights issue; issue click highlights marker
  await pg.click('#view .box >> nth=0'); await pg.waitForTimeout(150);
  ok(await pg.$$eval('#issues .iss.hl',e=>e.length)===1,'clicking a marker highlights its issue');
  await pg.click('#issues .iss >> nth=1', {position:{x:10,y:10}}); await pg.waitForTimeout(150);
  ok(await pg.$$eval('#view .box.hl',e=>e.length)>=1,'clicking an issue highlights its marker');

  // decisions
  await pg.click('.th[data-n="3"]'); await pg.waitForTimeout(150);
  ok((await pg.textContent('#stitle')).startsWith('Slide 3'),'thumbnail click opens slide 3');
  await pg.click('#issues .iss:has(.how) .btn.good >> nth=0'); await pg.waitForTimeout(100);
  await pg.click('#issues .iss:has(.how) .btn.badc >> nth=1'); await pg.waitForTimeout(100);
  const prog=await pg.textContent('#prog'); ok(prog.includes('1 fixes confirmed')&&prog.includes('1 fixes rejected'),'decision counters: '+prog);
  await pg.click('#issues .iss:has(.how) .btn.good >> nth=0'); await pg.waitForTimeout(100);
  ok((await pg.textContent('#prog')).includes('0 fixes confirmed'),'clicking a decision again un-sets it');
  await pg.click('#issues .iss:has(.how) .btn.good >> nth=0');

  // reviewed + keyboard
  await pg.click('#rvbtn'); ok((await pg.textContent('#rvbtn'))==='Reviewed','Mark reviewed toggles');
  ok((await pg.$$eval('.stat b',e=>e[4].textContent))==='1/8','reviewed counter 1/8');
  await pg.keyboard.press('ArrowRight'); await pg.waitForTimeout(100);
  ok((await pg.textContent('#stitle')).startsWith('Slide 4'),'ArrowRight goes to next slide');
  await pg.keyboard.press('ArrowLeft'); await pg.click('#next'); await pg.click('#prev');
  ok((await pg.textContent('#stitle')).startsWith('Slide 3'),'Prev/Next buttons work');

  // verdict + notes
  await pg.click('#verd [data-v="Reject"]'); ok(await pg.$eval('#verd [data-v="Reject"]',e=>e.classList.contains('on')),'verdict Reject selected');
  await pg.fill('#notes','Slide 4 chart overlaps table'); 

  // persistence
  await pg.reload(); await pg.waitForTimeout(300);
  ok((await pg.textContent('#stitle')).startsWith('Slide 3'),'reload keeps current slide');
  ok((await pg.$$eval('.stat b',e=>e[4].textContent))==='1/8','reload keeps reviewed state');
  ok(await pg.$eval('#verd [data-v="Reject"]',e=>e.classList.contains('on')),'reload keeps verdict');
  ok((await pg.inputValue('#notes'))==='Slide 4 chart overlaps table','reload keeps notes');
  ok((await pg.textContent('#prog')).includes('1 fixes confirmed'),'reload keeps decisions');

  // export json
  const [dl]=await Promise.all([pg.waitForEvent('download'),pg.click('#exp')]);
  const fs=require('fs'); const p=await dl.path(); const j=JSON.parse(fs.readFileSync(p,'utf8'));
  ok(j.verdict==='Reject'&&j.notes.includes('chart')&&Object.values(j.decisions).filter(Boolean).length===2&&j.reviewed['3'],'exported JSON has verdict, notes, decisions, reviewed');
  ok(j.summary.includes('Slide 3 (reviewed)')&&j.summary.includes('open:'),'summary lists open issues');
  // copy summary
  await pg.click('#cpy'); const clip=await pg.evaluate(()=>navigator.clipboard.readText());
  ok(clip.startsWith('Deck QA review - sloppy.pptx')&&clip.includes('Verdict: Reject'),'copy summary puts text on clipboard');

  // reset
  pg.once('dialog',d=>d.accept()); await pg.click('#rst'); await pg.waitForTimeout(200);
  ok((await pg.$$eval('.stat b',e=>e[4].textContent))==='0/8'&&(await pg.inputValue('#notes'))==='','reset clears decisions');

  // mobile layout
  await pg.setViewportSize({width:400,height:850}); await pg.waitForTimeout(200);
  const noScroll=await pg.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1);
  ok(noScroll,'phone width: no horizontal page scroll');
  ok(await pg.$eval('#rail',e=>getComputedStyle(e).flexDirection==='row'),'phone width: thumbnails become a horizontal strip');

  // no-fix dashboard (check only)
  const p2=await ctx.newPage(); p2.on('pageerror',e=>errs.push(String(e)));
  await p2.goto('file://'+D+'dash_nofix.html'); await p2.waitForTimeout(300);
  ok(await p2.$$eval('.tab',e=>e.map(x=>x.textContent).join()).then(t=>!t.includes('After')),'check-only mode has no After/Compare tabs');
  ok(await p2.$$eval('#issues .iss .how',e=>e.length)===0,'check-only mode shows no "fixed" items');
  ok(await p2.$$eval('#issues .iss',e=>e.length)>0,'check-only mode lists open issues');
  // clean deck
  const p3=await ctx.newPage(); p3.on('pageerror',e=>errs.push(String(e)));
  await p3.goto('file://'+D+'dash_clean.html'); await p3.waitForTimeout(300);
  ok((await p3.textContent('#stitle')).includes('clean'),'clean deck: slide marked clean');
  ok((await p3.textContent('#issues')).includes('Nothing found'),'clean deck: nothing found message');
  ok((await p3.textContent('#sugg')).includes('Accept'),'clean deck: suggests Accept');

  ok(errs.length===0,'no JS errors ('+errs.join(' | ')+')');
  console.log(`\n${pass} passed, ${fail} failed`); await b.close(); process.exit(fail?1:0);
})();
