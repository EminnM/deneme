"""Self-contained reviewer dashboard (one HTML file, works offline)."""
import base64, json

from .config import CATEGORIES
from .report import deck_verdict, describe_fix
from . import explain as ex


def _img(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def build_data(deck, before, after, img_before, img_after, name):
    verdict, mins = deck_verdict(before, after)
    left = after if after is not None else before
    slides = []
    for sl in deck.slides:
        b = [i for i in before if i.slide == sl.no]
        a = [i for i in left if i.slide == sl.no]

        def row(i, remaining):
            e = ex.explain(i, deck.width, deck.height)
            return dict(cat=i.category, msg=i.message, fixable=i.fixable, status=i.status,
                        label=e["label"], why=e["why"], tip=e["fix"], sev=e["severity"], where=e["where"],
                        bbox=[round(v, 1) for v in i.bbox] if i.bbox else None,
                        how=describe_fix(i) if (i.status == "fixed") else "", remaining=remaining)
        fixed = [row(i, False) for i in b if i.status == "fixed"]
        rem = [row(i, True) for i in a]
        found = [row(i, False) for i in b]
        slides.append(dict(no=sl.no, before=_img(img_before[sl.no]) if sl.no in img_before else None,
                           after=_img(img_after[sl.no]) if (after is not None and sl.no in img_after) else None,
                           found=found, fixed=fixed, left=rem,
                           state="clean" if not b else ("fixed" if not a else "attention")))
    return dict(name=name, notes=ex.notes(before, deck.width, deck.height), w=deck.width, h=deck.height, cats=CATEGORIES, slides=slides,
                verdict=verdict, minutes=round(mins, 1), has_fix=after is not None,
                n_found=len(before), n_fixed=sum(1 for i in before if i.status == "fixed"), n_left=len(left))


def html(deck, before, after, img_before, img_after, name="deck.pptx"):
    data = build_data(deck, before, after, img_before, img_after, name)
    blob = json.dumps(data).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", blob)


TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deck QA Dashboard</title>
<style>
:root{--bg:#f4f5f8;--card:#fff;--ink:#161b2b;--mute:#667085;--line:#e2e5ec;--navy:#0c1430;--ok:#1f8a5b;--fix:#3d53c6;--bad:#c8372d;--warn:#b7791f;--chip:#eef0f6}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f1320;--card:#181d2e;--ink:#e8ebf5;--mute:#98a1b8;--line:#2a3148;--navy:#0a0e1c;--chip:#232a40}}
:root[data-theme=dark]{--bg:#0f1320;--card:#181d2e;--ink:#e8ebf5;--mute:#98a1b8;--line:#2a3148;--navy:#0a0e1c;--chip:#232a40}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
button{font:inherit;color:inherit;cursor:pointer}
header{background:var(--navy);color:#fff;padding:14px 16px;display:flex;flex-wrap:wrap;gap:14px 24px;align-items:center}
header h1{font-size:17px;margin:0}header .sub{opacity:.75;font-size:12px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-left:auto}
.stat{background:rgba(255,255,255,.1);border-radius:10px;padding:6px 12px;min-width:84px}
.stat b{display:block;font-size:18px}.stat span{font-size:11px;opacity:.8}
.wrap{display:grid;grid-template-columns:150px minmax(0,1fr) 360px;gap:14px;padding:14px;align-items:start}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px}
.pad{padding:12px 14px}
.rail{position:sticky;top:8px;max-height:calc(100vh - 16px);overflow:auto;display:flex;flex-direction:column;gap:8px}
.th{border:2px solid var(--line);border-radius:10px;background:var(--card);padding:4px;text-align:left;position:relative}
.th img{width:100%;display:block;border-radius:6px}.th small{display:flex;justify-content:space-between;color:var(--mute);margin-top:3px;padding:0 2px}
.th.sel{border-color:var(--fix)}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.dot.clean{background:var(--ok)}.dot.fixed{background:var(--fix)}.dot.attention{background:var(--bad)}
.th .rv{position:absolute;top:6px;right:6px;background:var(--ok);color:#fff;border-radius:99px;font-size:11px;padding:0 6px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.tab,.chip{border:1px solid var(--line);background:var(--chip);border-radius:99px;padding:5px 12px}
.tab.on,.chip.on{background:var(--fix);border-color:var(--fix);color:#fff}
.viewer{position:relative;line-height:0}
.viewer img{width:100%;border:1px solid var(--line);border-radius:8px;background:#fff}
.box{position:absolute;border:2px solid var(--bad);border-radius:4px;background:rgba(200,55,45,.08);cursor:pointer;transition:.15s}
.box.fixed{border-color:var(--fix);background:rgba(61,83,198,.08);border-style:dashed}
.box.hl{box-shadow:0 0 0 3px #ffb703;background:rgba(255,183,3,.22);z-index:3}
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:10px}.cmp h4{margin:0 0 4px;font-size:12px;color:var(--mute);line-height:1.3}
@media (max-width:700px){.cmp{grid-template-columns:1fr}}
h3{margin:0 0 8px;font-size:14px}h3 small{color:var(--mute);font-weight:400}
.iss{border:1px solid var(--line);border-radius:10px;padding:8px 10px;margin-bottom:8px;background:var(--card)}
.iss.hl{border-color:#ffb703;box-shadow:0 0 0 2px rgba(255,183,3,.4)}
.cat{font-size:11px;font-weight:600;padding:1px 8px;border-radius:99px;color:#fff;display:inline-block}
.sev{font-size:10px;text-transform:uppercase;border-radius:6px;padding:0 6px;border:1px solid var(--line)}.sev.high{color:var(--bad);border-color:var(--bad)}.sev.medium{color:var(--warn);border-color:var(--warn)}details{margin-top:3px}summary{cursor:pointer;font-size:12px}\n.how{color:var(--fix);font-size:12px;margin-top:3px}.mute{color:var(--mute)}
.acts{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap}
.btn{border:1px solid var(--line);background:var(--chip);border-radius:8px;padding:3px 10px;font-size:12px}
.btn.on.good{background:var(--ok);border-color:var(--ok);color:#fff}.btn.on.badc{background:var(--bad);border-color:var(--bad);color:#fff}.btn.on.neutral{background:var(--mute);border-color:var(--mute);color:#fff}
table.mx{border-collapse:collapse;width:100%;font-size:11px}.mx th,.mx td{border:1px solid var(--line);padding:3px 4px;text-align:center}
.mx th{font-weight:600;color:var(--mute)}.mx td.c{cursor:pointer}.mx .f{background:rgba(200,55,45,.25)}.mx .x{background:rgba(61,83,198,.22)}.mx .o{background:rgba(31,138,91,.14)}
.verd{display:flex;gap:8px;margin:6px 0}.verd .btn{flex:1;padding:8px;font-weight:600}
textarea{width:100%;min-height:70px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);padding:8px;font:inherit}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.sugg{font-size:12px;color:var(--mute)}
.mid{display:flex;flex-direction:column;gap:14px}.side{display:flex;flex-direction:column;gap:14px;position:sticky;top:8px;max-height:calc(100vh - 16px);overflow:auto}
@media (max-width:1100px){.wrap{grid-template-columns:minmax(0,1fr)}.rail{position:static;flex-direction:row;overflow-x:auto;max-height:none;gap:8px;padding-bottom:4px}.rail .th{min-width:110px;max-width:110px;flex:none}.side{position:static;max-height:none}}
</style></head><body>
<header>
  <div><h1>Deck QA dashboard</h1><div class="sub" id="dname"></div></div>
  <div class="stats" id="stats"></div>
</header>
<div class="wrap">
  <nav class="rail" id="rail" aria-label="Slides"></nav>
  <main class="mid">
    <section class="card pad"><h3>Checklist heatmap <small>click a cell to jump</small></h3><div id="matrix" style="overflow-x:auto"></div></section>
    <section class="card pad">
      <div class="row" style="justify-content:space-between;margin-bottom:8px"><h3 id="stitle" style="margin:0"></h3>
        <div class="row"><button class="btn" id="prev">&larr; Prev</button><button class="btn" id="next">Next &rarr;</button><button class="btn" id="rvbtn"></button></div></div>
      <div class="tabs" id="tabs"></div>
      <div id="view"></div>
    </section>
  </main>
  <aside class="side">
    <section class="card pad"><h3>This slide</h3><div class="tabs" id="filters"></div><div id="issues"></div></section>
    <section class="card pad"><h3>Your verdict</h3><div class="sugg" id="sugg"></div>
      <div class="verd" id="verd"></div><textarea id="notes" placeholder="Notes on the problems you found..."></textarea>
      <div class="row" style="margin-top:8px"><button class="btn" id="ins">Insert tool notes</button><button class="btn" id="exp">Download decisions (JSON)</button><button class="btn" id="cpy">Copy summary</button><button class="btn" id="rst">Reset</button></div>
      <div class="sugg" id="prog" style="margin-top:6px"></div></section>
  </aside>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const KEY='deckqa:'+D.name;
const COL={'Alignment':'#6d5acd','Spacing':'#d9822b','Text fit':'#c0392b','Lines and arrows':'#1a7f8e','Titles':'#8e44ad','Readability':'#b7791f','Leftover graphics':'#7f8c8d','Consistency':'#2e7d32'};
let S={slide:1,tab:D.has_fix?'compare':'before',dec:{},rev:{},verdict:'',notes:'',cat:null};
try{Object.assign(S,JSON.parse(localStorage.getItem(KEY)||'{}'))}catch(e){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}}
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let HL=null;

function stats(){
  const rv=Object.keys(S.rev).filter(k=>S.rev[k]).length;
  $('dname').textContent=D.name+' - '+D.slides.length+' slides';
  $('stats').innerHTML=[['Found',D.n_found],['Auto-fixed',D.n_fixed],['For a human',D.n_left],['Est. human min',D.minutes],['Reviewed',rv+'/'+D.slides.length]]
   .map(([k,v])=>`<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');
}
function rail(){
  $('rail').innerHTML=D.slides.map(s=>`<button class="th ${s.no===S.slide?'sel':''}" data-n="${s.no}" aria-label="Slide ${s.no}">
   ${S.rev[s.no]?'<span class="rv">done</span>':''}<img src="${s.before||''}" alt=""><small><span>${s.no}</span><span class="dot ${s.state}" title="${s.state}"></span></small></button>`).join('');
  $('rail').querySelectorAll('.th').forEach(b=>b.onclick=()=>go(+b.dataset.n));
}
function matrix(){
  let h='<table class="mx"><tr><th>#</th>'+D.cats.map(c=>`<th>${c.replace(' and ',' & ')}</th>`).join('')+'</tr>';
  for(const s of D.slides){
    h+=`<tr><th>${s.no}</th>`;
    for(const c of D.cats){
      const f=s.left.some(i=>i.cat===c),x=s.fixed.some(i=>i.cat===c);
      h+=`<td class="c ${f?'f':x?'x':'o'}" data-n="${s.no}" data-c="${esc(c)}" title="${f?'needs attention':x?'auto-fixed':'ok'}">${f?'!':x?'fixed':'ok'}</td>`;
    }
    h+='</tr>';
  }
  h+='</table><div class="sugg" style="margin-top:6px">! needs a human &nbsp; fixed = auto-fixed &nbsp; ok = passed</div>';
  $('matrix').innerHTML=h;
  $('matrix').querySelectorAll('td.c').forEach(td=>td.onclick=()=>{S.cat=td.dataset.c;go(+td.dataset.n,true)});
}
function z(i){const [l,t,r,b]=i.bbox;return 100+Math.round(1000-((r-l)*(b-t))/(D.w*D.h)*1000)}
function boxes(list,cls){
  return list.filter(i=>i.bbox).map((i,k)=>{
    const [l,t,r,b]=i.bbox;
    return `<div class="box ${cls||''}" data-k="${i._k}" style="z-index:${z(i)};left:${l/D.w*100}%;top:${t/D.h*100}%;width:${(r-l)/D.w*100}%;height:${(b-t)/D.h*100}%;border-color:${cls==='fixed'?'':COL[i.cat]}" title="${esc(i.cat+': '+i.msg)}"></div>`}).join('');
}
function view(){
  const s=D.slides[S.slide-1];
  $('stitle').textContent='Slide '+s.no+' - '+(s.state==='clean'?'clean':s.state==='fixed'?'all issues auto-fixed':'needs attention');
  const tabs=[['before','Original']];if(D.has_fix){tabs.push(['after','After fix'],['compare','Compare'])}
  $('tabs').innerHTML=tabs.map(([k,v])=>`<button class="tab ${S.tab===k?'on':''}" data-t="${k}">${v}</button>`).join('')+
    `<button class="tab ${S.showBoxes===false?'':'on'}" id="tb">Show markers</button>`;
  $('tabs').querySelectorAll('[data-t]').forEach(b=>b.onclick=()=>{S.tab=b.dataset.t;save();view()});
  $('tb').onclick=()=>{S.showBoxes=S.showBoxes===false;save();view()};
  const sb=S.showBoxes!==false;
  s.found.forEach((i,k)=>i._k='f'+k);s.left.forEach((i,k)=>i._k='l'+k);
  const orig=`<div class="viewer"><img src="${s.before||''}" alt="Original slide ${s.no}">${sb?boxes(s.found.map(i=>i),'').replace(/class="box "/g,'class="box"'):''}</div>`;
  const fixedBoxes=s.found.map(i=>({...i,_k:i._k}));
  const origHtml=`<div class="viewer"><img src="${s.before||''}" alt="Original">${sb?s.found.filter(i=>i.bbox).map(i=>{const [l,t,r,b]=i.bbox;return `<div class="box ${i.status==='fixed'?'fixed':''}" data-k="${i._k}" style="z-index:${z(i)};left:${l/D.w*100}%;top:${t/D.h*100}%;width:${(r-l)/D.w*100}%;height:${(b-t)/D.h*100}%;${i.status==='fixed'?'':'border-color:'+COL[i.cat]}" title="${esc(i.cat+': '+i.msg)}"></div>`}).join(''):''}</div>`;
  const aftHtml=s.after?`<div class="viewer"><img src="${s.after}" alt="After">${sb?boxes(s.left,''):''}</div>`:'';
  if(S.tab==='before')$('view').innerHTML=origHtml;
  else if(S.tab==='after')$('view').innerHTML=aftHtml||origHtml;
  else $('view').innerHTML=`<div class="cmp"><div><h4>Original - red = still open, blue dashed = auto-fixed</h4>${origHtml}</div><div><h4>After auto-fix - red = still needs you</h4>${aftHtml}</div></div>`;
  $('view').querySelectorAll('.box').forEach(b=>b.onclick=()=>hl(b.dataset.k));
  $('rvbtn').textContent=S.rev[s.no]?'Reviewed':'Mark reviewed';$('rvbtn').className='btn'+(S.rev[s.no]?' on good':'');
}
function dec(k){return S.dec[S.slide+'|'+k]||''}
function setDec(k,v){const key=S.slide+'|'+k;S.dec[key]=S.dec[key]===v?'':v;save();issues();prog()}
function issues(){
  const s=D.slides[S.slide-1];
  const cats=[...new Set([...s.found,...s.left].map(i=>i.cat))];
  $('filters').innerHTML=(cats.length?`<button class="chip ${S.cat?'':'on'}" data-c="">All</button>`:'')+cats.map(c=>`<button class="chip ${S.cat===c?'on':''}" data-c="${esc(c)}">${esc(c)}</button>`).join('');
  $('filters').querySelectorAll('.chip').forEach(b=>b.onclick=()=>{S.cat=b.dataset.c||null;save();issues()});
  const f=i=>!S.cat||i.cat===S.cat;
  const fx=s.found.filter(i=>i.status==='fixed'&&f(i)),rem=s.left.filter(f);
  const card=(i,fixed)=>{const k=i._k,d=dec(k);
    return `<div class="iss ${HL===k?'hl':''}" data-k="${k}"><span class="cat" style="background:${COL[i.cat]}">${esc(i.cat)}</span> <span class="sev ${i.sev}">${i.sev}</span> <b>${esc(i.label)}</b> <span class="mute">(${esc(i.where)})</span><div>${esc(i.msg)}</div>
     <details><summary class="mute">Why it matters / how to fix</summary><div class="mute"><b>Why:</b> ${esc(i.why)}<br><b>Fix:</b> ${esc(i.tip)}</div></details>
     ${fixed?`<div class="how">Auto-fix: ${esc(i.how)}</div>`:`<div class="mute">${i.fixable?'Auto-fix could not resolve this':'Manual - needs your judgement'}</div>`}
     <div class="acts">${fixed?`<button class="btn good ${d==='ok'?'on':''}" data-a="ok">Fix is good</button><button class="btn badc ${d==='bad'?'on':''}" data-a="bad">Fix is wrong</button>`
        :`<button class="btn good ${d==='done'?'on':''}" data-a="done">Handled</button><button class="btn neutral ${d==='ignore'?'on':''}" data-a="ignore">Not a problem</button><button class="btn badc ${d==='todo'?'on':''}" data-a="todo">Needs rework</button>`}</div></div>`};
  $('issues').innerHTML=(rem.length?`<h3>Needs you <small>(${rem.length})</small></h3>`+rem.map(i=>card(i,false)).join(''):'')+
    (fx.length?`<h3>Auto-fixed <small>(${fx.length}) - confirm each looks right</small></h3>`+fx.map(i=>card(i,true)).join(''):'')+
    ((!rem.length&&!fx.length)?'<div class="mute">Nothing found on this slide.</div>':'');
  $('issues').querySelectorAll('.iss').forEach(el=>{el.onclick=e=>{if(e.target.dataset.a)return;hl(el.dataset.k)};
    el.querySelectorAll('[data-a]').forEach(b=>b.onclick=()=>setDec(el.dataset.k,b.dataset.a))});
}
function hl(k){HL=HL===k?null:k;document.querySelectorAll('.box').forEach(b=>b.classList.toggle('hl',b.dataset.k===HL));
  document.querySelectorAll('.iss').forEach(b=>{b.classList.toggle('hl',b.dataset.k===HL);if(b.dataset.k===HL)b.scrollIntoView({block:'nearest',behavior:'smooth'})})}
function verdict(){
  $('sugg').textContent='Tool suggestion: '+D.verdict+' (about '+D.minutes+' min of human work; Fix = 5 min or less, Reject = more). Your call overrides it.';
  $('verd').innerHTML=['Accept','Fix','Reject'].map(v=>`<button class="btn ${S.verdict===v?'on '+(v==='Reject'?'badc':v==='Accept'?'good':'neutral'):''}" data-v="${v}">${v}</button>`).join('');
  $('verd').querySelectorAll('button').forEach(b=>b.onclick=()=>{S.verdict=S.verdict===b.dataset.v?'':b.dataset.v;save();verdict()});
  $('notes').value=S.notes||'';$('notes').oninput=e=>{S.notes=e.target.value;save()};
}
function prog(){
  const v=Object.values(S.dec);const c=k=>v.filter(x=>x===k).length;
  $('prog').textContent=`Decisions: ${c('ok')} fixes confirmed, ${c('bad')} fixes rejected, ${c('todo')} need rework, ${c('done')} handled, ${c('ignore')} dismissed.`;
  stats();
}
function summary(){
  const lines=[`Deck QA review - ${D.name}`,`Verdict: ${S.verdict||'(none)'} (tool suggested ${D.verdict}, ~${D.minutes} min)`,''];
  for(const s of D.slides){
    const bad=[...s.found,...s.left].map((i,_)=>i);
    const r=[];s.found.forEach((i,k)=>{const d=S.dec[s.no+'|f'+k];if(i.status==='fixed'&&d==='bad')r.push('  fix rejected: '+i.cat+' - '+i.msg)});
    s.left.forEach((i,k)=>{const d=S.dec[s.no+'|l'+k];if(d!=='ignore'&&d!=='done')r.push('  open: '+i.cat+' - '+i.msg+(d==='todo'?' [needs rework]':''))});
    lines.push(`Slide ${s.no} (${S.rev[s.no]?'reviewed':'not reviewed'})`+(r.length?'':': ok'));lines.push(...r);
  }
  if(S.notes)lines.push('','Notes: '+S.notes);return lines.join('\n');
}
function go(n,keep){S.slide=Math.max(1,Math.min(D.slides.length,n));HL=null;if(!keep)S.cat=null;save();rail();view();issues()}
$('prev').onclick=()=>go(S.slide-1);$('next').onclick=()=>go(S.slide+1);
$('rvbtn').onclick=()=>{S.rev[S.slide]=!S.rev[S.slide];save();rail();view();stats()};
$('ins').onclick=()=>{const cur=S.notes?S.notes.trim()+'\\n':'';if(!cur.includes(D.notes.split('\\n')[0])){S.notes=cur+D.notes;save();$('notes').value=S.notes}};
$('exp').onclick=()=>{const b=new Blob([JSON.stringify({deck:D.name,verdict:S.verdict,notes:S.notes,decisions:S.dec,reviewed:S.rev,summary:summary()},null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='deck-review.json';a.click()};
$('cpy').onclick=async()=>{try{await navigator.clipboard.writeText(summary());$('cpy').textContent='Copied'}catch(e){prompt('Copy:',summary())}setTimeout(()=>$('cpy').textContent='Copy summary',1500)};
$('rst').onclick=()=>{if(confirm('Clear all your decisions for this deck?')){S={slide:1,tab:S.tab,dec:{},rev:{},verdict:'',notes:'',cat:null};save();init()}};
document.addEventListener('keydown',e=>{if(e.target.tagName==='TEXTAREA')return;if(e.key==='ArrowRight'||e.key==='j')go(S.slide+1);if(e.key==='ArrowLeft'||e.key==='k')go(S.slide-1)});
function init(){stats();rail();matrix();view();issues();verdict();prog()}
init();
</script></body></html>
'''
