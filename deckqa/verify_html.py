"""Self-contained verification board page (one offline HTML file)."""
import base64, json


def _img(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def html(data, images, name="deck.pptx"):
    d = dict(data)
    d["name"] = name
    d["slides"] = [dict(s, img=_img(images[s["no"]]) if s["no"] in images else None) for s in data["slides"]]
    blob = json.dumps(d).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", blob)


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deck Verification Board</title>
<style>
:root{--bg:#f4f5f8;--card:#fff;--ink:#161b2b;--mute:#667085;--line:#e2e5ec;--navy:#0c1430;--ok:#1f8a5b;--bad:#c8372d;--na:#8b93a7;--fix:#3d53c6;--chip:#eef0f6}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f1320;--card:#181d2e;--ink:#e8ebf5;--mute:#98a1b8;--line:#2a3148;--navy:#0a0e1c;--chip:#232a40}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
button{font:inherit;color:inherit;cursor:pointer}
header{background:var(--navy);color:#fff;padding:14px 16px;display:flex;flex-wrap:wrap;gap:10px 24px;align-items:center}
header h1{font-size:17px;margin:0}header .sub{opacity:.78;font-size:12px;max-width:760px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-left:auto}.stat{background:rgba(255,255,255,.1);border-radius:10px;padding:6px 12px;min-width:84px}
.stat b{display:block;font-size:18px}.stat span{font-size:11px;opacity:.8}
.wrap{display:grid;grid-template-columns:130px minmax(0,1fr) 400px;gap:14px;padding:14px;align-items:start}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px}.pad{padding:12px 14px}
.rail{position:sticky;top:8px;max-height:calc(100vh - 16px);overflow:auto;display:flex;flex-direction:column;gap:8px}
.th{border:2px solid var(--line);border-radius:10px;background:var(--card);padding:4px;text-align:left;position:relative}
.th img{width:100%;display:block;border-radius:6px}.th small{display:flex;justify-content:space-between;color:var(--mute);margin-top:3px;padding:0 2px}
.th.sel{border-color:var(--fix)}.th .pc{font-size:11px}
.mid,.side{display:flex;flex-direction:column;gap:14px}.side{position:sticky;top:8px;max-height:calc(100vh - 16px);overflow:auto}
h3{margin:0 0 8px;font-size:14px}h3 small{color:var(--mute);font-weight:400}
.note{background:rgba(61,83,198,.08);border:1px solid rgba(61,83,198,.25);border-radius:10px;padding:8px 12px;font-size:12.5px}
table.mx{border-collapse:collapse;width:100%;font-size:11px}.mx th,.mx td{border:1px solid var(--line);padding:4px;text-align:center}
.mx th{color:var(--mute);font-weight:600}.mx td.c{cursor:pointer;font-weight:700}.mx .p{background:rgba(31,138,91,.16);color:var(--ok)}.mx .f{background:rgba(200,55,45,.2);color:var(--bad)}.mx .n{background:rgba(139,147,167,.14);color:var(--na)}
.mx td.dn{box-shadow:inset 0 0 0 2px var(--fix)}
table.inv{border-collapse:collapse;width:100%;font-size:12.5px;margin-bottom:10px}.inv th,.inv td{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left}.inv th{color:var(--mute);font-weight:600}
.sw{display:inline-block;width:14px;height:14px;border-radius:3px;border:1px solid var(--line);vertical-align:-2px;margin-right:6px}
.rare{color:var(--bad);font-size:11px}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:6px 18px}
@media (max-width:700px){.grid2{grid-template-columns:1fr}}
.viewer{position:relative;line-height:0}.viewer img{width:100%;border:1px solid var(--line);border-radius:8px;background:#fff}
.vb{position:absolute;border:2px solid var(--ok);background:none;border-radius:3px;pointer-events:none}
.vb.flag{border-color:var(--bad);background:rgba(200,55,45,.10)}
.vb.pick{border-color:#2f6fed;border-style:dashed;background:rgba(47,111,237,.12);box-shadow:0 0 0 2px rgba(47,111,237,.35)}
.vb .vl{position:absolute;left:-2px;top:-17px;font:600 10px/1 system-ui;background:var(--ok);color:#fff;padding:2px 4px;border-radius:3px;white-space:nowrap}
.vb.flag .vl{background:var(--bad)}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.chip{border:1px solid var(--line);background:var(--chip);border-radius:99px;padding:4px 12px}.chip.on{background:var(--fix);border-color:var(--fix);color:#fff}
.btn{border:1px solid var(--line);background:var(--chip);border-radius:8px;padding:4px 10px;font-size:12px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.crit{border:1px solid var(--line);border-radius:10px;margin-bottom:8px;background:var(--card);overflow:hidden}
.crit.sel{border-color:var(--fix);box-shadow:0 0 0 2px rgba(61,83,198,.25)}
.ch{display:flex;gap:8px;align-items:flex-start;padding:8px 10px;cursor:pointer}
.pill{font-size:11px;font-weight:700;border-radius:99px;padding:1px 8px;color:#fff;flex:none;margin-top:1px}.pill.pass{background:var(--ok)}.pill.flag{background:var(--bad)}.pill.na{background:var(--na)}
.ct{flex:1;min-width:0}.ct b{display:block}.ct span{color:var(--mute);font-size:12.5px;display:block}
.chk{display:flex;gap:4px;align-items:center;font-size:12px;color:var(--mute);flex:none}.chk input{width:18px;height:18px}
.cb{padding:0 10px 10px;font-size:13px}.cb ul{margin:4px 0 8px;padding-left:18px}.cb li{margin-bottom:4px}
.cb .g{color:var(--ok);font-weight:700}.cb .r{color:var(--bad);font-weight:700}.cb .m{color:var(--mute);font-size:12px}
.cb .why{color:var(--mute);font-size:12px}
textarea{width:100%;min-height:60px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);padding:8px;font:inherit}
@media (max-width:1100px){.wrap{grid-template-columns:minmax(0,1fr)}.rail{position:static;flex-direction:row;overflow-x:auto;max-height:none;gap:8px}.rail .th{min-width:100px;max-width:100px;flex:none}.side{position:static;max-height:none}}
</style></head><body>
<header><div><h1>Verification board</h1><div class="sub" id="sub"></div></div><div class="stats" id="stats"></div></header>
<div class="wrap">
<nav class="rail" id="rail" aria-label="Slides"></nav>
<main class="mid">
  <section class="note" id="gl"></section>
  <section class="card pad"><h3>Coverage <small>every slide x every checklist item. Tick = measured, no defect found. ! = look at it. - = does not apply. Blue frame = you checked it</small></h3><div style="overflow-x:auto" id="matrix"></div></section>
  <section class="card pad"><details id="invd"><summary><b>Deck inventory</b> <small class="mute" style="color:var(--mute)">fonts, sizes, colours, titles, page numbers across the whole deck</small></summary><div id="inv" style="margin-top:10px"></div></details></section>
  <section class="card pad">
    <div class="row" style="justify-content:space-between;margin-bottom:8px"><h3 id="stitle" style="margin:0"></h3>
      <div class="row"><button class="btn" id="prev">&larr; Prev</button><button class="btn" id="next">Next &rarr;</button></div></div>
    <div class="tabs" id="tabs"></div><div id="view"></div>
    <details style="margin-top:10px"><summary><b>Everything on this slide</b> <span id="ecount" style="color:var(--mute)"></span> <small style="color:var(--mute)">click a row to see it on the slide</small></summary><div style="overflow-x:auto"><table class="inv" id="elt"></table></div></details>
    <div class="note" style="margin-top:8px;line-height:1.35"><b style="color:var(--ok)">Green</b> = the tool measured this and found it correct. <b style="color:var(--bad)">Red</b> = look at this. Pick a checklist item on the right to see exactly what it refers to.</div>
  </section>
</main>
<aside class="side">
  <section class="card pad"><div class="row" style="justify-content:space-between"><h3 style="margin:0">Checklist for this slide</h3><span id="prog" class="m" style="color:var(--mute)"></span></div>
    <div class="row" style="margin:8px 0"><button class="btn" id="all">Tick all 8</button><button class="btn" id="none">Clear</button></div><div id="crits"></div></section>
  <section class="card pad"><h3>Your notes</h3><textarea id="notes" placeholder="Anything you noticed yourself..."></textarea>
    <div class="row" style="margin-top:8px"><button class="btn" id="exp">Download my checks (JSON)</button><button class="btn" id="rst">Reset</button></div></section>
</aside></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const KEY='deckqa-verify:'+D.name;
let S={slide:1,focus:null,chk:{},notes:'',boxes:true};let PICK=null;
try{Object.assign(S,JSON.parse(localStorage.getItem(KEY)||'{}'))}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}};
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const key=(n,c)=>n+'|'+c;
const cur=()=>D.slides[S.slide-1];
function checkedCount(n){return D.cats.filter(c=>S.chk[key(n,c)]).length}
function stats(){
  let pass=0,flag=0,na=0,okItems=0;
  D.slides.forEach(s=>s.items.forEach(i=>{if(i.status==='pass')pass++;else if(i.status==='flag')flag++;else na++;okItems+=i.ok.length}));
  const done=D.slides.reduce((a,s)=>a+checkedCount(s.no),0),total=D.slides.length*D.cats.length;
  $('sub').textContent=D.name+' - '+D.slides.length+' slides. This board shows the deck exactly as received: nothing has been fixed and no fixes are shown, so you form your own view first.';
  $('stats').innerHTML=[['Confirmed items',okItems],['Passed checks',pass],['Need a look',flag],['You checked',done+'/'+total]].map(([k,v])=>`<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');
  $('gl').innerHTML='<b>What this board cannot tell you.</b> '+esc(D.global_limits);
}
function rail(){
  $('rail').innerHTML=D.slides.map(s=>{const f=s.items.filter(i=>i.status==='flag').length;
    return `<button class="th ${s.no===S.slide?'sel':''}" data-n="${s.no}"><img src="${s.img||''}" alt=""><small><span>${s.no}</span><span class="pc">${checkedCount(s.no)}/8 ${f?'<b style="color:var(--bad)">! '+f+'</b>':''}</span></small></button>`}).join('');
  $('rail').querySelectorAll('.th').forEach(b=>b.onclick=()=>go(+b.dataset.n));
}
function matrix(){
  let h='<table class="mx"><tr><th>#</th>'+D.cats.map(c=>`<th>${esc(c.replace(' and ',' & '))}</th>`).join('')+'</tr>';
  for(const s of D.slides){h+=`<tr><th>${s.no}</th>`;
    s.items.forEach((i,k)=>{const c=D.cats[k];h+=`<td class="c ${i.status==='pass'?'p':i.status==='flag'?'f':'n'} ${S.chk[key(s.no,c)]?'dn':''}" data-n="${s.no}" data-c="${esc(c)}" title="${esc(i.summary)}">${i.status==='pass'?'&#10003;':i.status==='flag'?'!':'-'}</td>`});
    h+='</tr>'}
  $('matrix').innerHTML=h+'</table>';
  $('matrix').querySelectorAll('td.c').forEach(td=>td.onclick=()=>{S.focus=td.dataset.c;go(+td.dataset.n,true)});
}
function inventory(){
  const I=D.inventory;
  const tbl=(title,rows,sw)=>`<div><b>${title}</b><table class="inv"><tr><th>${sw?'Colour':'Value'}</th><th>Used</th><th>Slides</th></tr>`+rows.map(r=>`<tr><td>${r.swatch?'<span class="sw" style="background:'+r.swatch+'"></span>':''}${esc(r.value)} ${r.rare?'<span class="rare">only used here: worth a look</span>':''}</td><td>${r.count}</td><td>${r.slides.join(', ')}</td></tr>`).join('')+'</table></div>';
  const tt=`<div><b>Titles</b><table class="inv"><tr><th>Slide</th><th>Size</th><th>Position</th><th>Lines</th></tr>`+I.titles.map(t=>`<tr><td>${t.slide}</td><td>${t.size!=null?t.size+'pt':'-'}</td><td>${t.pos?t.pos.join(', '):'-'}</td><td>${t.lines!=null?t.lines:'-'}</td></tr>`).join('')+'</table></div>';
  const pn=`<div><b>Page numbers</b><table class="inv"><tr><th>Slide</th><th>Position</th></tr>`+Object.entries(I.page_numbers).map(([n,v])=>`<tr><td>${n}</td><td>${v?v.join(', '):'none'}</td></tr>`).join('')+'</table></div>';
  $('inv').innerHTML=`<div class="grid2">${tbl('Fonts',I.fonts)}${tbl('Font sizes',I.sizes)}${tbl('Fill colours',I.fills,true)}${tbl('Text colours',I.text_colours,true)}${tt}${pn}</div>`+(I.assumed_size_boxes?`<div class="m" style="color:var(--mute)">${I.assumed_size_boxes} text box(es) do not state a size in the file; the board assumes the theme default for those.</div>`:'');
}
function boxesFor(s){
  const out=[];const want=S.focus;
  s.items.forEach((it,k)=>{const c=D.cats[k];
    if(want){if(c!==want)return;
      it.ok.forEach(o=>o.boxes.forEach(b=>out.push(['ok',b])));it.flags.forEach(f=>f.boxes.forEach(b=>out.push(['flag',b])))}
    else{it.flags.forEach(f=>f.boxes.forEach(b=>out.push(['flag',b])))}});
  return out;
}
function view(){
  const s=cur();const f=s.items.filter(i=>i.status==='flag').length;
  $('stitle').textContent='Slide '+s.no+' - '+(f?f+' item(s) need a look':'all applicable checks passed');
  $('tabs').innerHTML=`<button class="chip ${S.focus?'':'on'}" data-c="">Flags only</button>`+D.cats.map((c,k)=>`<button class="chip ${S.focus===c?'on':''}" data-c="${esc(c)}">${esc(c)}</button>`).join('')+`<button class="chip ${S.boxes===false?'':'on'}" id="tb">Show boxes</button>`;
  $('tabs').querySelectorAll('[data-c]').forEach(b=>b.onclick=()=>{S.focus=b.dataset.c||null;save();view();crits()});
  $('tb').onclick=()=>{S.boxes=S.boxes===false;save();view()};
  const bx=S.boxes===false?[]:boxesFor(s).map(([k,b])=>{const [l,t,r,bt]=b.b;const a=(r-l)*(bt-t);
    return `<div class="vb ${k==='flag'?'flag':''}" style="z-index:${100+Math.round(1000-a/(D.w*D.h)*1000)};left:${l/D.w*100}%;top:${t/D.h*100}%;width:${(r-l)/D.w*100}%;height:${(bt-t)/D.h*100}%">${b.t?'<span class="vl">'+esc(b.t)+'</span>':''}</div>`}).join('');
  const pk=(PICK!=null&&s.elements[PICK])?(()=>{const [l,t,r,bt]=s.elements[PICK].b;return `<div class="vb pick" style="z-index:900;left:${l/D.w*100}%;top:${t/D.h*100}%;width:${(r-l)/D.w*100}%;height:${(bt-t)/D.h*100}%"></div>`})():'';
  $('view').innerHTML=`<div class="viewer"><img src="${s.img||''}" alt="Slide ${s.no}">${bx}${pk}</div>`;
  $('ecount').textContent='('+s.elements.length+' elements)';
  $('elt').innerHTML='<tr><th>Element</th><th>Type</th><th>Font</th><th>Size</th><th>Text colour</th><th>Fill</th><th>x, y</th><th>w x h</th></tr>'+s.elements.map((e,i)=>`<tr data-i="${i}" style="cursor:pointer;${PICK===i?'background:rgba(47,111,237,.12)':''}"><td>${esc(e.label)}</td><td>${esc(e.kind)}</td><td>${esc(e.font)}</td><td>${esc(e.size)}</td><td>${e.colour!=='-'?'<span class="sw" style="background:'+e.colour+'"></span>':''}${esc(e.colour)}</td><td>${e.fill!=='-'?'<span class="sw" style="background:'+e.fill+'"></span>':''}${esc(e.fill)}</td><td>${e.x}, ${e.y}</td><td>${e.w} x ${e.h}</td></tr>`).join('');
  $('elt').querySelectorAll('tr[data-i]').forEach(tr=>tr.onclick=()=>{const i=+tr.dataset.i;PICK=PICK===i?null:i;view()});
}
function crits(){
  const s=cur();
  $('prog').textContent=checkedCount(s.no)+' of 8 checked';
  $('crits').innerHTML=s.items.map((it,k)=>{const c=D.cats[k],sel=S.focus===c,done=!!S.chk[key(s.no,c)];
    const body=sel?`<div class="cb">${it.flags.length?'<div class="r">Needs a look</div><ul>'+it.flags.map(f=>`<li>${esc(f.text)}<div class="why">${esc(f.why)}</div></li>`).join('')+'</ul>':''}${it.ok.length?'<div class="g">Confirmed correct</div><ul>'+it.ok.map(o=>`<li>${esc(o.text)}</li>`).join('')+'</ul>':''}${it.status==='na'?'<div class="m">Does not apply: '+esc(it.summary)+'</div>':''}<div class="m"><b>Does not confirm:</b> ${esc(it.limits)}</div></div>`:'';
    return `<div class="crit ${sel?'sel':''}" data-c="${esc(c)}"><div class="ch"><span class="pill ${it.status}">${it.status==='pass'?'OK':it.status==='flag'?'LOOK':'N/A'}</span><div class="ct"><b>${esc(c)}</b><span>${esc(it.status==='flag'?it.summary:it.summary)}</span></div><label class="chk" onclick="event.stopPropagation()"><input type="checkbox" data-c="${esc(c)}" ${done?'checked':''}>checked</label></div>${body}</div>`}).join('');
  $('crits').querySelectorAll('.crit').forEach(el=>el.querySelector('.ch').onclick=()=>{S.focus=S.focus===el.dataset.c?null:el.dataset.c;save();view();crits()});
  $('crits').querySelectorAll('input[type=checkbox]').forEach(cb=>cb.onchange=()=>{S.chk[key(s.no,cb.dataset.c)]=cb.checked;save();stats();rail();matrix();$('prog').textContent=checkedCount(s.no)+' of 8 checked'});
}
function go(n,keepFocus){PICK=null;S.slide=Math.max(1,Math.min(D.slides.length,n));if(!keepFocus)S.focus=null;save();rail();view();crits();matrix()}
$('prev').onclick=()=>go(S.slide-1);$('next').onclick=()=>go(S.slide+1);
$('all').onclick=()=>{D.cats.forEach(c=>S.chk[key(S.slide,c)]=true);save();stats();rail();matrix();crits()};
$('none').onclick=()=>{D.cats.forEach(c=>delete S.chk[key(S.slide,c)]);save();stats();rail();matrix();crits()};
$('notes').oninput=e=>{S.notes=e.target.value;save()};
$('exp').onclick=()=>{const b=new Blob([JSON.stringify({deck:D.name,checked:S.chk,notes:S.notes},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='my-checks.json';a.click()};
$('rst').onclick=()=>{if(confirm('Clear all your ticks and notes for this deck?')){S={slide:1,focus:null,chk:{},notes:'',boxes:true};save();init()}};
document.addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA'||e.target.tagName==='INPUT')return;if(e.key==='ArrowRight'||e.key==='j')go(S.slide+1);if(e.key==='ArrowLeft'||e.key==='k')go(S.slide-1)});
function init(){stats();inventory();rail();matrix();view();crits();$('notes').value=S.notes||''}
init();
</script></body></html>
'''
