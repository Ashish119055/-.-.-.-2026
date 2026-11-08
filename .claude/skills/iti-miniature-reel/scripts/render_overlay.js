#!/usr/bin/env node
// Render the transparent text/glow overlay as a PNG sequence with an HTML canvas in headless Chromium.
// usage: node render_overlay.js timeline.json OUT_DIR [--times 1.2,4.5,...]
//   without --times: every frame 0..duration at fps  -> OUT_DIR/0000.png ...
//   with --times:   only those moments             -> OUT_DIR/still_<t>.png
// timeline.json:
// { "duration": 13.5, "fps": 30, "join": 6.9, "join_style": "flame" | "bloom",
//   "lines": [ {"text":"…", "icon":"🔧", "t":0.8}, …, {"text":"ITI મણિનગર — પ્રવેશ ચાલુ", "icon":"✅", "t":10.6, "cta":true} ] }
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');

const [tlPath, outDir, ...rest] = process.argv.slice(2);
if (!tlPath || !outDir) { console.error('usage: node render_overlay.js timeline.json OUT_DIR [--times a,b]'); process.exit(2); }
const tl = JSON.parse(fs.readFileSync(tlPath, 'utf8'));
const ti = rest.indexOf('--times');
const times = ti >= 0 ? rest[ti + 1].split(',').map(Number) : null;
if (!tl.lines || tl.lines.length < 1 || tl.lines.length > 3) { console.error('timeline needs 1–3 lines'); process.exit(2); }
fs.mkdirSync(outDir, { recursive: true });

const PAGE = `<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Gujarati:wght@900&family=Hind+Vadodara:wght@700&display=block" rel="stylesheet">
<style>html,body{margin:0;background:transparent}</style></head>
<body><canvas id="c" width="1080" height="1920"></canvas>
<script>
const W=1080,H=1920;
// SAFE AREA: nothing in top 250, bottom 420, right 150.
const SAFE={x0:70,x1:W-150,y0:250,y1:H-420};
const INK='#1b1446', CREAM='#fff6e0', BAR='#FFD21F';
const c=document.getElementById('c'), g=c.getContext('2d');
let FAMILY=null, TL=null;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const easeOutCubic=x=>1-Math.pow(1-x,3), easeInOut=x=>0.5-0.5*Math.cos(Math.PI*x);
function scaleAt(dt){            // 60% -> 110% -> settle 100%. Never a plain fade.
  if(dt<0) return 0;
  if(dt<0.22) return 0.6+0.5*easeOutCubic(dt/0.22);
  if(dt<0.40) return 1.1-0.1*easeInOut((dt-0.22)/0.18);
  return 1;
}
function barAt(dt){ return clamp((dt-0.06)/0.38,0,1); }   // highlight sweep, left -> right
function font(px){ return '900 '+px+'px "'+FAMILY+'"'; }
const EMOJI='"Noto Color Emoji","Apple Color Emoji","Segoe UI Emoji"';
function layout(line){
  const maxW=SAFE.x1-SAFE.x0-40;
  let px=line.cta?108:100, iconPx, iw, tw;
  for(;px>=52;px-=2){
    iconPx=Math.round(px*0.9);
    g.font=font(px); tw=g.measureText(line.text).width;
    g.font=iconPx+'px '+EMOJI; iw=g.measureText(line.icon||'').width;
    if(tw+iw+px*0.35+48<=maxW) break;
  }
  if(px<52) throw new Error('line too long for safe area: '+line.text);
  return {px,iconPx,iw,tw,h:Math.round(px*1.55),w:tw+iw+px*0.35+48};
}
function draw(t){
  g.clearRect(0,0,W,H);
  // join glow (hides the cut between clip 1 and clip 2)
  const jd=t-TL.join, k=Math.exp(-(jd*jd)/(2*0.16*0.16));
  if(k>0.003){
    g.save(); g.globalCompositeOperation='lighter';
    const flame=TL.join_style!=='bloom';
    const r=g.createRadialGradient(W/2,H*0.5,0,W/2,H*0.5,H*(0.35+0.4*k));
    if(flame){ r.addColorStop(0,'rgba(255,236,170,'+(0.95*k)+')'); r.addColorStop(0.35,'rgba(255,170,40,'+(0.7*k)+')'); r.addColorStop(1,'rgba(120,40,0,0)'); }
    else     { r.addColorStop(0,'rgba(255,246,224,'+(0.9*k)+')'); r.addColorStop(0.5,'rgba(240,120,150,'+(0.45*k)+')'); r.addColorStop(1,'rgba(40,60,160,0)'); }
    g.fillStyle=r; g.fillRect(0,0,W,H); g.restore();
  }
  // text block, bottom-anchored inside the safe area; earlier lines stay
  const L=TL.lines.map(l=>({...l,...layout(l)}));
  const gap=34; let y=SAFE.y1-40;
  const ys=[]; for(let i=L.length-1;i>=0;i--){ y-=L[i].h; ys[i]=y; y-=gap; }
  if(ys[0]<SAFE.y0) throw new Error('text block exceeds safe area');
  L.forEach((l,i)=>{
    const dt=t-l.t, s=scaleAt(dt); if(s<=0) return;
    const x=SAFE.x0, yy=ys[i], cx=x+l.w/2, cy=yy+l.h/2;
    g.save(); g.translate(cx,cy); g.scale(s,s); g.translate(-cx,-cy);
    // yellow highlight bar sweeping behind the words
    const bw=l.w*easeOutCubic(barAt(dt));
    if(bw>1){ g.fillStyle='rgba(0,0,0,0.28)'; roundRect(x+8,yy+10,bw,l.h,18); g.fill();
              g.fillStyle=BAR; roundRect(x,yy,bw,l.h,18); g.fill(); }
    // icon
    g.font=l.iconPx+'px '+EMOJI; g.textBaseline='middle'; g.textAlign='left';
    g.fillText(l.icon||'',x+20,cy+2);
    // text: cream outline so it reads on paint before the bar arrives
    const tx=x+20+l.iw+l.px*0.35;
    g.font=font(l.px); g.lineJoin='round';
    g.lineWidth=l.px*0.16; g.strokeStyle=CREAM; g.strokeText(l.text,tx,cy+l.px*0.06);
    g.fillStyle=INK; g.fillText(l.text,tx,cy+l.px*0.06);
    g.restore();
  });
}
function roundRect(x,y,w,h,r){ r=Math.min(r,w/2,h/2); g.beginPath(); g.moveTo(x+r,y); g.arcTo(x+w,y,x+w,y+h,r); g.arcTo(x+w,y+h,x,y+h,r); g.arcTo(x,y+h,x,y,r); g.arcTo(x,y,x+w,y,r); g.closePath(); }
window.setup=async(tl)=>{
  TL=tl;
  const sample=tl.lines.map(l=>l.text).join(' ');
  await Promise.all([document.fonts.load('900 80px "Noto Sans Gujarati"',sample),document.fonts.load('700 80px "Hind Vadodara"',sample)]).catch(()=>{});
  await document.fonts.ready;
  if(document.fonts.check('900 80px "Noto Sans Gujarati"',sample)) FAMILY='Noto Sans Gujarati';
  else if(document.fonts.check('700 80px "Hind Vadodara"',sample)) FAMILY='Hind Vadodara';
  // verify the font really loaded (check() is true for system fallbacks too)
  const ok=[...document.fonts].some(f=>f.status==='loaded'&&/Gujarati|Vadodara/.test(f.family));
  if(!FAMILY||!ok) throw new Error('Gujarati font (Noto Sans Gujarati Black / Hind Vadodara Bold) failed to load');
  return FAMILY;
};
window.frame=(t)=>{ draw(t); return c.toDataURL('image/png'); };
</script></body></html>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.setContent(PAGE, { waitUntil: 'networkidle' });
  const fam = await page.evaluate(tl => window.setup(tl), tl);
  console.error('font:', fam);
  const save = (file, url) => fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
  if (times) {
    for (const t of times) save(path.join(outDir, `still_${t.toFixed(2)}.png`), await page.evaluate(t => window.frame(t), t));
  } else {
    const n = Math.round(tl.duration * tl.fps);
    for (let i = 0; i < n; i++) {
      save(path.join(outDir, String(i).padStart(4, '0') + '.png'), await page.evaluate(t => window.frame(t), i / tl.fps));
      if (i % 60 === 0) console.error(`overlay ${i}/${n}`);
    }
  }
  await browser.close();
})().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
