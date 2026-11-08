#!/usr/bin/env node
// Lyric + title + join-light overlay, drawn on an HTML canvas frame by frame in headless Chromium.
// usage: node render_overlay.js plan.json timing.json base.timing.json OUT_DIR [--times 3.2,10.5] [--force]
//   no --times : every frame -> OUT_DIR/00000.png …      --times : OUT_DIR/still_<t>.png
//
// plan.json
// { "title": {"text": "ख़त", "artist": "Navjot Ahuja", "in": 0.4, "out": 5.0, "x": 0.5, "y": 0.42},
//   "cards": [ { "words": [0, 3],            // first..last word index from timing.json (inclusive), ≤ 6 words
//                "x": 0.70, "y": 0.30, "align": "center",     // anchor, fractions of the frame
//                "size": 76, "font": "serif" | "hand",          // Tiro Devanagari Hindi | Kalam
//                "effect": "ink" | "write" | "rise" | "fold" | "drybrush" | "wind" | "envelope",
//                "slip": true,                                  // torn paper slip behind (busy shots)
//                "color": "#fff6e3", "out": 18.4,               // optional; out defaults to next card's first word
//                "source": [0.5, 0.62],                         // rise: where the words come from (flame)
//                "path": [ {"t": 52.0, "x": 0.5, "y": 0.6, "rot": -4, "scale": 1}, … ] } ] } // envelope track
// timing.json : from separate_align.py (word start times are used as-is — never typed by hand)
// base.timing.json : from assemble.py base (duration, fps, size, joins)
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
process.on('uncaughtException', e => { console.error('ERROR:', e.message); process.exit(1); });

const argv = process.argv.slice(2);
const pos = argv.filter((a, i) => !a.startsWith('--') && argv[i - 1] !== '--times');
const [planP, timingP, metaP, outDir] = pos;
if (!outDir) { console.error('usage: node render_overlay.js plan.json timing.json base.timing.json OUT_DIR [--times a,b]'); process.exit(2); }
const ti = argv.indexOf('--times');
const times = ti >= 0 ? argv[ti + 1].split(',').map(Number) : null;
const plan = JSON.parse(fs.readFileSync(planP, 'utf8'));
const timing = JSON.parse(fs.readFileSync(timingP, 'utf8'));
const meta = JSON.parse(fs.readFileSync(metaP, 'utf8'));

// ---- validation (fail loudly, never guess) ----
const words = timing.words;
const cards = plan.cards || [];
cards.forEach((c, k) => {
  const [a, b] = c.words;
  if (!(a >= 0 && b < words.length && a <= b)) throw new Error(`card ${k}: word range ${a}-${b} outside timing.json`);
  if (b - a + 1 > 6) throw new Error(`card ${k}: ${b - a + 1} words — keep it to a few words (≤ 6)`);
  if (c.effect === 'envelope' && !(c.path && c.path.length >= 2)) throw new Error(`card ${k}: envelope needs a path`);
  if (c.effect === 'rise' && !c.source) throw new Error(`card ${k}: rise needs a source point`);
});
const covered = new Set(); cards.forEach(c => { for (let i = c.words[0]; i <= c.words[1]; i++) covered.add(i); });
const missing = words.filter(w => !covered.has(w.i)).map(w => `#${w.i} ${w.word}`);
if (missing.length) console.error('WARNING: words not on any card:', missing.join(', '));
if (plan.title && cards.length && plan.title.out > words[cards[0].words[0]].start - 0.15)
  throw new Error('title must fade out before the first sung word');
if (fs.existsSync(outDir) && fs.readdirSync(outDir).some(f => times ? f.startsWith('still_') : /^\d{5}\.png$/.test(f)) && !argv.includes('--force'))
  throw new Error(`REFUSING to overwrite files in ${outDir} — ask the user, then re-run with --force`);
fs.mkdirSync(outDir, { recursive: true });

const data = { plan, words, meta };

const PAGE = `<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Tiro+Devanagari+Hindi&family=Kalam:wght@400;700&family=Caladea:wght@400;700&display=block" rel="stylesheet">
<style>html,body{margin:0;background:transparent}</style></head><body><canvas id="c"></canvas>
<script>
let D, W, H, g, c;
const INK='#1d1a4f', CREAM='#fff6e3', GOLD='#ffcf5a';
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)), lerp=(a,b,k)=>a+(b-a)*k;
const eOut=x=>1-Math.pow(1-clamp(x,0,1),3), eInOut=x=>{x=clamp(x,0,1);return x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;};
const eBack=x=>{x=clamp(x,0,1);const s=1.6;return 1+(s+1)*Math.pow(x-1,3)+s*Math.pow(x-1,2);};
function rng(seed){let s=seed>>>0||1;return()=>((s=Math.imul(s^(s>>>15),2246822507)^Math.imul(s^(s>>>13),3266489909),(s>>>0)/4294967296));}
const FONT={serif:'"Tiro Devanagari Hindi"',hand:'"Kalam"'};
function fontOf(card,px){return (card.font==='hand'||card.effect==='write'||card.effect==='envelope'?'700 ':'400 ')+px+'px '+(card.font==='hand'||card.effect==='write'||card.effect==='envelope'?FONT.hand:FONT.serif);}

// ---------- layout ----------
function layout(card){
  const px=card.size||72; g.font=fontOf(card,px);
  const ws=[]; for(let i=card.words[0];i<=card.words[1];i++) ws.push(D.words[i]);
  const space=g.measureText(' ').width, widths=ws.map(w=>g.measureText(w.word).width);
  const total=widths.reduce((a,b)=>a+b,0)+space*(ws.length-1);
  let x0=card.x*W - (card.align==='left'?0:card.align==='right'?total:total/2);
  const y=card.y*H, items=[];
  ws.forEach((w,k)=>{items.push({w,x:x0,width:widths[k]}); x0+=widths[k]+space;});
  return {px,items,total,y,left:items[0].x,right:items[0].x+total};
}
function cardOut(k){const cd=D.plan.cards[k]; if(cd.out!=null) return cd.out;
  const nx=D.plan.cards[k+1]; return nx? D.words[nx.words[0]].start-0.05 : D.meta.duration;}

// ---------- torn paper slip ----------
function slip(L,k,alpha){
  const r=rng(k*7919+13), pad=L.px*0.45, x0=L.left-pad, x1=L.right+pad, y0=L.y-L.px*0.95, y1=L.y+L.px*0.5;
  g.save(); g.globalAlpha=alpha*0.96; g.beginPath();
  const step=14; g.moveTo(x0,y0);
  for(let x=x0;x<=x1;x+=step) g.lineTo(x,y0+(r()-0.5)*7);
  for(let y=y0;y<=y1;y+=step) g.lineTo(x1+(r()-0.5)*7,y);
  for(let x=x1;x>=x0;x-=step) g.lineTo(x,y1+(r()-0.5)*9);
  for(let y=y1;y>=y0;y-=step) g.lineTo(x0+(r()-0.5)*7,y);
  g.closePath(); g.shadowColor='rgba(40,20,10,.35)'; g.shadowBlur=14; g.shadowOffsetY=5;
  const gr=g.createLinearGradient(0,y0,0,y1); gr.addColorStop(0,'#fbf1dc'); gr.addColorStop(1,'#efe0bf');
  g.fillStyle=gr; g.fill(); g.restore();
}

// ---------- word effects (lt = seconds since the word is sung) ----------
function baseStyle(card){ const onSlip=!!card.slip; return {fill:card.color||(onSlip?INK:CREAM), shadow:onSlip?null:'rgba(15,10,40,.75)'}; }
function plainWord(it,y,st,alpha){ g.globalAlpha=alpha; if(st.shadow){g.shadowColor=st.shadow; g.shadowBlur=12;} g.fillStyle=st.fill; g.fillText(it.w.word,it.x,y); g.shadowBlur=0; }

const FX={
  ink(card,it,y,lt,st){ const k=eOut(lt/0.4); g.save(); g.filter='blur('+((1-k)*8).toFixed(2)+'px)'; plainWord(it,y+(1-k)*10,st,k); g.restore(); },
  // written on stroke by stroke: outline draws in left->right with the pen, then the ink fills
  write(card,it,y,lt,st){
    const dur=clamp((it.w.end-it.w.start)*0.9,0.3,0.8), k=clamp(lt/dur,0,1);
    g.save(); g.beginPath(); g.rect(it.x-8,y-card._L.px*1.4,(it.width+16)*eInOut(k)+1,card._L.px*2.2); g.clip();
    g.setLineDash([card._L.px*3,card._L.px*30]); g.lineDashOffset=card._L.px*3*(1-k);
    g.lineWidth=Math.max(1.5,card._L.px*0.035); g.strokeStyle=st.fill; g.strokeText(it.w.word,it.x,y); g.setLineDash([]);
    g.globalAlpha=clamp((lt-dur*0.35)/(dur*0.8),0,1); if(st.shadow){g.shadowColor=st.shadow; g.shadowBlur=10;}
    g.fillStyle=st.fill; g.fillText(it.w.word,it.x,y); g.restore();
    if(k<1){ const px=it.x+it.width*eInOut(k), py=y-card._L.px*0.35+Math.sin(lt*40)*card._L.px*0.12;  // pen nib
      g.save(); g.fillStyle=st.fill; g.beginPath(); g.arc(px,py,Math.max(2,card._L.px*0.04),0,7); g.fill(); g.restore(); }
  },
  // the prayer rises out of the diya flame
  rise(card,it,y,lt,st){
    const k=eOut(lt/1.0), sx=card.source[0]*W, sy=card.source[1]*H, tx=it.x+it.width/2;
    const cx=lerp(sx,tx,k)+Math.sin(lt*3+it.w.i)*(1-k)*30, cy=lerp(sy,y,k)-Math.sin(k*Math.PI)*60;
    g.save(); g.translate(cx,cy); g.scale(lerp(0.25,1,k),lerp(0.25,1,k));
    g.globalAlpha=clamp(lt/0.25,0,1); g.shadowColor='rgba(255,190,60,'+(0.9*(1-k*0.6))+')'; g.shadowBlur=30*(1-k)+12;
    g.fillStyle=k<1?mix(GOLD,st.fill,k):st.fill; g.fillText(it.w.word,-it.width/2,0); g.restore();
    const r=rng(it.w.i*31+7); g.save(); g.globalCompositeOperation='lighter';
    for(let e=0;e<10;e++){ const a=clamp(lt*1.2-r()*0.6,0,1); if(a<=0||a>=1) continue;
      g.fillStyle='rgba(255,'+(170+r()*60|0)+',60,'+(1-a)+')';
      g.beginPath(); g.arc(lerp(sx,tx,a)+(r()-.5)*80, lerp(sy,y,a)-a*60-(r()*40), 2+r()*3,0,7); g.fill(); }
    g.restore();
  },
  // folds up from its baseline like the pop-up house
  fold(card,it,y,lt,st){
    const k=eBack(lt/0.55); if(k<=0) return; g.save(); g.translate(it.x,y);
    g.transform(1,0,-0.35*(1-clamp(lt/0.55,0,1)),Math.max(0.001,k),0,0);
    if(st.shadow){g.shadowColor=st.shadow; g.shadowBlur=10;}
    g.fillStyle=st.fill; g.globalAlpha=clamp(lt/0.12,0,1); g.fillText(it.w.word,0,0);
    g.globalAlpha=0.35*(1-clamp(lt/0.55,0,1)); g.fillStyle='#000'; g.fillText(it.w.word,0,0); g.restore();
  },
  // revealed by a dry ultramarine brush stroke
  drybrush(card,it,y,lt,st){
    const dur=clamp(it.w.end-it.w.start,0.35,0.8), k=eInOut(lt/dur), px=card._L.px, r=rng(it.w.i*97+3);
    const top=y-px*1.05, h=px*1.45, n=26, bw=it.width+px*0.4;
    const off=card._off||(card._off=document.createElement('canvas')); off.width=W; off.height=H; const o=off.getContext('2d');
    const mk=card._mask||(card._mask=document.createElement('canvas')); mk.width=W; mk.height=H; const m=mk.getContext('2d');
    for(let s=0;s<n;s++){ const lag=r()*0.25, len=clamp((k-lag)/(1-lag),0,1)*bw*(0.85+r()*0.15);
      m.fillRect(it.x-px*0.2,top+s*h/n,len,h/n+0.6); }          // bristle mask
    o.clearRect(0,0,W,H); o.font=g.font; o.textBaseline=g.textBaseline; o.fillStyle=st.fill; o.fillText(it.w.word,it.x,y);
    o.globalCompositeOperation='destination-in'; o.drawImage(mk,0,0); o.globalCompositeOperation='source-over';
    g.save(); if(st.shadow){g.shadowColor=st.shadow; g.shadowBlur=8;} g.drawImage(off,0,0); g.restore();
    if(k<1){ g.save(); g.globalAlpha=0.85*(1-k*0.3);  // the wet bristle streaks of the brush head
      for(let s=0;s<n;s++){ const lag=r()*0.25, len=clamp((k-lag)/(1-lag),0,1)*bw;
        g.fillStyle='rgba(30,60,190,'+(0.35+r()*0.5)+')'; g.fillRect(it.x-px*0.2+len-px*0.5*r(),top+s*h/n,px*0.5*r(),h/n*0.7); }
      g.restore(); }
  },
  // blows in on the wind
  wind(card,it,y,lt,st){
    const k=eOut(lt/0.8), r=rng(it.w.i*13+1);
    g.save(); g.translate(it.x+it.width/2+(1-k)*(-260-r()*120), y+(1-k)*(60+r()*40)+Math.sin(lt*6)*(1-k)*18);
    g.rotate((1-k)*(-0.5-r()*0.3)); g.globalAlpha=clamp(lt/0.2,0,1);
    if(st.shadow){g.shadowColor=st.shadow; g.shadowBlur=10;} g.fillStyle=st.fill; g.fillText(it.w.word,-it.width/2,0); g.restore();
    g.save(); for(let p=0;p<5;p++){ const a=clamp((lt-r()*0.3)/1.4,0,1); if(a<=0||a>=1) continue;   // petals
      g.globalAlpha=1-a; g.fillStyle=r()<0.5?'#f39abf':'#4a6be0';
      g.beginPath(); g.ellipse(it.x-200+a*(it.width+420),y-40+Math.sin(a*9+p)*50+(r()-.5)*80,9,4,a*6+p,0,7); g.fill(); }
    g.restore();
  }
};
FX.envelope=FX.write;
function mix(a,b,k){const p=s=>[1,3,5].map(i=>parseInt(s.slice(i,i+2),16));const A=p(a),B=p(b);return 'rgb('+A.map((v,i)=>Math.round(lerp(v,B[i],k))).join(',')+')';}

function trackAt(path,t){ if(t<=path[0].t) return path[0]; const L=path[path.length-1]; if(t>=L.t) return L;
  for(let i=0;i<path.length-1;i++){const a=path[i],b=path[i+1]; if(t<=b.t){const k=eInOut((t-a.t)/(b.t-a.t));
    return {x:lerp(a.x,b.x,k),y:lerp(a.y,b.y,k),rot:lerp(a.rot||0,b.rot||0,k),scale:lerp(a.scale||1,b.scale||1,k)};}} }

function drawCard(card,k,t){
  const L=card._L||(card._L=layout(card)), first=L.items[0].w.start, out=cardOut(k);
  if(t<first-0.05||t>out+0.45) return;
  const exit=1-clamp((t-out)/0.45,0,1);
  g.save(); g.globalAlpha=exit; g.font=fontOf(card,L.px); g.textBaseline='alphabetic';
  if(card.effect==='envelope'){ const p=trackAt(card.path,t), ax=card.x*W, ay=card.y*H;
    g.translate(p.x*W,p.y*H); g.rotate((p.rot||0)*Math.PI/180); g.scale(p.scale||1,p.scale||1); g.translate(-ax,-ay); }
  if(card.slip) slip(L,k,clamp((t-first+0.05)/0.25,0,1));
  const st=baseStyle(card), fx=FX[card.effect||'ink']; if(!fx) throw new Error('unknown effect '+card.effect);
  for(const it of L.items){ const lt=t-it.w.start; if(lt<0) continue; g.save(); g.globalAlpha*=1; fx(card,it,L.y,lt,st); g.restore(); }
  g.restore();
}

function drawTitle(t){
  const T=D.plan.title; if(!T||t<T.in||t>T.out) return;
  const a=Math.min(eOut((t-T.in)/0.8),1-eInOut((t-(T.out-0.9))/0.9));
  const x=(T.x??0.5)*W, y=(T.y??0.42)*H; g.save(); g.globalAlpha=a; g.textAlign='center';
  g.shadowColor='rgba(15,10,40,.7)'; g.shadowBlur=18; g.fillStyle=CREAM;
  g.font='700 '+(T.size||120)+'px "Caladea"'; g.fillText(T.text,x,y);
  g.font='400 '+Math.round((T.size||120)*0.32)+'px "Caladea"'; g.globalAlpha=a*0.9; g.fillText(T.artist||'',x,y+(T.size||120)*0.62);
  g.restore();
}

function drawJoins(t){
  for(const j of D.meta.joins){ if(j.style!=='glow'&&j.style!=='bloom') continue;
    const s=j.dur*0.45, d=t-j.t, k=Math.exp(-(d*d)/(2*s*s)); if(k<0.004) continue;
    g.save(); g.globalCompositeOperation=j.style==='glow'?'lighter':'source-over';
    if(j.style==='glow'){ const r=g.createRadialGradient(W/2,H/2,0,W/2,H/2,W*(0.25+0.45*k));
      r.addColorStop(0,'rgba(255,238,180,'+0.95*k+')'); r.addColorStop(0.4,'rgba(255,165,40,'+0.6*k+')'); r.addColorStop(1,'rgba(120,40,0,0)');
      g.fillStyle=r; g.fillRect(0,0,W,H); }
    else { const r0=rng(Math.round(j.t*100)), grow=clamp((d/(j.dur)+0.6),0,1.4);   // watercolour bloom spreading
      const cols=['244,236,214','74,107,224','243,154,191','255,207,90'];
      for(let b=0;b<14;b++){ const bx=W*(0.2+r0()*0.6), by=H*(0.2+r0()*0.6), rad=W*(0.15+r0()*0.35)*(0.3+grow);
        const gr=g.createRadialGradient(bx,by,rad*0.2,bx,by,rad); const col=cols[b%cols.length];
        gr.addColorStop(0,'rgba('+col+','+0.55*k+')'); gr.addColorStop(0.75,'rgba('+col+','+0.4*k+')'); gr.addColorStop(1,'rgba('+col+',0)');
        g.fillStyle=gr; g.beginPath(); g.arc(bx,by,rad,0,7); g.fill(); } }
    g.restore(); }
}

window.setup=async(data)=>{
  D=data; [W,H]=D.meta.size; c=document.getElementById('c'); c.width=W; c.height=H; g=c.getContext('2d');
  const sample=D.words.map(w=>w.word).join(' ');
  const want=[['400 60px "Tiro Devanagari Hindi"',sample],['700 60px "Kalam"',sample],['700 60px "Caladea"',(D.plan.title?.text||'')+(D.plan.title?.artist||'')+'Aa']];
  await Promise.all(want.map(([f,s])=>document.fonts.load(f,s).catch(()=>{}))); await document.fonts.ready;
  const loaded=new Set([...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family.replace(/"/g,'')));
  const need=['Tiro Devanagari Hindi','Kalam']; if(D.plan.title) need.push('Caladea');
  const miss=need.filter(n=>!loaded.has(n)); if(miss.length) throw new Error('fonts failed to load: '+miss.join(', '));
  return [...loaded].join(', ');
};
window.frame=(t)=>{ g.clearRect(0,0,W,H); drawJoins(t); drawTitle(t); D.plan.cards.forEach((cd,k)=>drawCard(cd,k,t)); return c.toDataURL('image/png'); };
</script></body></html>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: meta.size[0], height: meta.size[1] } });
  await page.setContent(PAGE, { waitUntil: 'networkidle' });
  console.error('fonts:', await page.evaluate(d => window.setup(d), data));
  const save = (f, url) => fs.writeFileSync(f, Buffer.from(url.split(',')[1], 'base64'));
  if (times) for (const t of times) save(path.join(outDir, `still_${t.toFixed(2)}.png`), await page.evaluate(t => window.frame(t), t));
  else {
    const n = Math.round(meta.duration * meta.fps);
    for (let i = 0; i < n; i++) {
      save(path.join(outDir, String(i).padStart(5, '0') + '.png'), await page.evaluate(t => window.frame(t), i / meta.fps));
      if (i % 150 === 0) console.error(`overlay ${i}/${n}`);
    }
  }
  await browser.close();
})().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
