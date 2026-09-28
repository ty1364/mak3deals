(() => {
  const canvas = document.getElementById('cartCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = 1200, H = 680;
  const startOverlay = document.getElementById('startOverlay');
  const endOverlay = document.getElementById('endOverlay');
  const startBtn = document.getElementById('startBtn');
  const restartBtn = document.getElementById('restartBtn');
  const scoreEl = document.getElementById('finalScore');
  const runSummary = document.getElementById('runSummary');
  const playerName = document.getElementById('playerName');
  const submitBtn = document.getElementById('submitScoreBtn');
  const scoreMessage = document.getElementById('scoreMessage');
  const monthEl = document.getElementById('leaderboardMonth');
  const listEl = document.getElementById('leaderboardList');
  const keys = new Set();
  let running = false, last = 0, elapsed = 0, score = 0, lives = 3, combo = 0, bestCombo = 0, level = 1;
  let spawnClock = 0, objects = [], sparks = [], shield = 0, pointerX = W / 2, runStartedAt = 0, lastRun = null;
  const products = [
    ['GROCERY DROP', '🛍', '#72f1be', 120], ['TECH DEAL', '▣', '#77e7ff', 160], ['HOME FIND', '⌂', '#ffd36f', 135],
    ['PET PICK', '♥', '#ff9fca', 110], ['KITCHEN WIN', '✦', '#c1a7ff', 145]
  ];
  const escapeHtml = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  function rounded(x,y,w,h,r){ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fill();}
  function reset(){running=false;elapsed=0;score=0;lives=3;combo=0;bestCombo=0;level=1;spawnClock=0;objects=[];sparks=[];shield=0;pointerX=W/2;lastRun=null;scoreMessage.textContent='';}
  function start(){reset();running=true;runStartedAt=Date.now();startOverlay.classList.add('hidden');endOverlay.classList.add('hidden');canvas.focus();last=performance.now();requestAnimationFrame(loop);}
  function end(reason){running=false;lastRun={score:Math.max(1,Math.floor(score)),wave:level,duration:Math.max(10,Math.floor((Date.now()-runStartedAt)/1000))};scoreEl.textContent=lastRun.score.toLocaleString();runSummary.textContent=reason+' · BEST STREAK '+bestCombo;endOverlay.classList.remove('hidden');loadBoard();}
  function spawn(){
    const roll=Math.random(); let kind='deal';
    if(roll>.83) kind='fee'; else if(roll>.72) kind='jackpot'; else if(roll>.65) kind='shield';
    const p=products[Math.floor(Math.random()*products.length)];
    objects.push({x:95+Math.random()*(W-190),y:-80,w:150,h:76,vy:130+level*18+Math.random()*90,kind,label:kind==='fee'?'CHECKOUT FEE':kind==='jackpot'?'JACKPOT DROP':kind==='shield'?'CART SHIELD':p[0],icon:kind==='fee'?'!':kind==='jackpot'?'★':kind==='shield'?'◆':p[1],color:kind==='fee'?'#ff7088':kind==='jackpot'?'#ffd36f':kind==='shield'?'#77e7ff':p[2],value:kind==='jackpot'?650:p[3]});
  }
  function burst(x,y,color,count=12){for(let i=0;i<count;i++) sparks.push({x,y,vx:(Math.random()-.5)*190,vy:(Math.random()-.8)*190,life:.6+Math.random()*.5,color});}
  function collide(o){const px=pointerX, py=H-104;return o.x<px+78&&o.x+o.w>px-78&&o.y<py+65&&o.y+o.h>py-65;}
  function catchObject(o){
    burst(o.x+o.w/2,o.y+o.h/2,o.color,o.kind==='fee'?8:18);
    if(o.kind==='fee'){if(shield){shield=0;score=Math.max(0,score-30);}else{lives--;combo=0;}return;}
    if(o.kind==='shield'){shield=1;score+=80;return;}
    combo++;bestCombo=Math.max(bestCombo,combo);const multiplier=Math.min(5,1+Math.floor(combo/5));score+=o.value*multiplier+(o.kind==='jackpot'?combo*100:0);
  }
  function update(dt){
    elapsed+=dt;level=1+Math.floor(elapsed/9);spawnClock-=dt;
    if(spawnClock<=0){spawn();spawnClock=Math.max(.27,.88-level*.045);}
    const move=(keys.has('ArrowLeft')||keys.has('a')?-1:0)+(keys.has('ArrowRight')||keys.has('d')?1:0); pointerX+=move*(520+level*12)*dt; pointerX=Math.max(110,Math.min(W-110,pointerX));
    if(typeof window.__cartPointer==='number') pointerX=window.__cartPointer;
    for(let i=objects.length-1;i>=0;i--){const o=objects[i];o.y+=o.vy*dt;if(collide(o)){catchObject(o);objects.splice(i,1);}else if(o.y>H+100){objects.splice(i,1);combo=0;}}
    for(let i=sparks.length-1;i>=0;i--){const s=sparks[i];s.x+=s.vx*dt;s.y+=s.vy*dt;s.vy+=220*dt;s.life-=dt;if(s.life<=0)sparks.splice(i,1);}
    if(lives<=0) end('CART WIPED OUT'); else if(elapsed>=60) end('TIME CALLED');
  }
  function draw(){
    const grad=ctx.createLinearGradient(0,0,0,H);grad.addColorStop(0,'#0d3140');grad.addColorStop(.58,'#081a25');grad.addColorStop(1,'#061018');ctx.fillStyle=grad;ctx.fillRect(0,0,W,H);
    ctx.fillStyle='rgba(141,247,197,.08)';for(let i=0;i<8;i++){ctx.fillRect(40+i*165,100,120,7);ctx.fillRect(40+i*165,270,120,7);}
    ctx.strokeStyle='rgba(141,247,197,.12)';ctx.lineWidth=2;for(let i=0;i<8;i++){ctx.beginPath();ctx.moveTo(55+i*165,0);ctx.lineTo(55+i*165,560);ctx.stroke();}
    ctx.fillStyle='#0b222d';ctx.fillRect(0,540,W,140);ctx.strokeStyle='rgba(255,211,111,.18)';ctx.lineWidth=3;for(let x=-H;x<W;x+=90){ctx.beginPath();ctx.moveTo(x,680);ctx.lineTo(x+140,540);ctx.stroke();}
    ctx.fillStyle='#eafff8';ctx.font='900 22px system-ui';ctx.fillText('CART QUEST',35,42);ctx.fillStyle='#8df7c5';ctx.font='700 13px system-ui';ctx.fillText('WAVE '+level,38,68);ctx.fillStyle='#ffd36f';ctx.fillText('SCORE '+Math.floor(score).toLocaleString(),185,68);ctx.fillStyle='#c9e5de';ctx.fillText('STREAK '+combo,370,68);ctx.fillStyle='#ff9eae';ctx.fillText('LIVES '+'♥'.repeat(lives)+'♡'.repeat(Math.max(0,3-lives)),500,68);ctx.fillStyle='#c9e5de';ctx.fillText('TIME '+Math.max(0,60-Math.floor(elapsed))+'s',W-140,42);
    for(const o of objects){ctx.fillStyle='rgba(0,0,0,.25)';rounded(o.x+5,o.y+8,o.w,o.h,15);ctx.fillStyle=o.color;rounded(o.x,o.y,o.w,o.h,15);ctx.fillStyle='#06202a';ctx.font='900 13px system-ui';ctx.fillText(o.label,o.x+14,o.y+23);ctx.font='32px system-ui';ctx.fillText(o.icon,o.x+14,o.y+59);ctx.font='900 18px system-ui';ctx.fillText(o.kind==='fee'?'− LIFE':o.kind==='shield'?'BLOCK':(o.kind==='jackpot'?'+650':'+'+o.value),o.x+65,o.y+54);}
    const px=pointerX,py=H-104;ctx.save();ctx.translate(px,py);if(shield){ctx.strokeStyle='rgba(119,231,255,.75)';ctx.lineWidth=6;ctx.beginPath();ctx.arc(0,0,88,0,Math.PI*2);ctx.stroke();}ctx.fillStyle='#d8fff0';rounded(-68,-18,136,62,15);ctx.fillStyle='#8df7c5';rounded(-52,-52,104,48,14);ctx.fillStyle='#163846';ctx.font='900 19px system-ui';ctx.fillText('MAK3',-29,-20);ctx.fillStyle='#ffd36f';ctx.fillRect(-35,25,70,10);ctx.restore();
    for(const s of sparks){ctx.globalAlpha=Math.max(0,s.life);ctx.fillStyle=s.color;ctx.fillRect(s.x,s.y,5,5);}ctx.globalAlpha=1;
  }
  function loop(now){if(!running)return;const dt=Math.min(.033,(now-last)/1000);last=now;update(dt);draw();if(running)requestAnimationFrame(loop);}
  function movePointer(e){const r=canvas.getBoundingClientRect();window.__cartPointer=Math.max(110,Math.min(W-110,(e.clientX-r.left)*(W/r.width)));}
  canvas.addEventListener('pointermove',movePointer);canvas.addEventListener('pointerdown',e=>{movePointer(e);canvas.setPointerCapture?.(e.pointerId);});
  window.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','a','d'].includes(e.key)){e.preventDefault();keys.add(e.key);}});window.addEventListener('keyup',e=>keys.delete(e.key));
  startBtn.addEventListener('click',start);restartBtn.addEventListener('click',start);
  submitBtn.addEventListener('click',async()=>{const name=playerName.value.trim();if(name.length<2){scoreMessage.textContent='Enter at least 2 characters.';return;}submitBtn.disabled=true;scoreMessage.textContent='Submitting…';try{const res=await fetch('/api/score',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({game:'cart-quest',name,...lastRun})});const data=await res.json();scoreMessage.textContent=data.message||data.error||'Done.';loadBoard();}catch{scoreMessage.textContent='Could not submit right now.';}finally{submitBtn.disabled=false;}});
  async function loadBoard(){try{const res=await fetch('/api/leaderboard?game=cart-quest');const data=await res.json();monthEl.textContent=data.month||'Current month';listEl.replaceChildren();if(!data.scores.length){const li=document.createElement('li');li.textContent='No runs yet — be the first cart captain.';listEl.appendChild(li);return;}data.scores.forEach((entry,i)=>{const li=document.createElement('li');li.innerHTML='<span class="rank">'+String(i+1).padStart(2,'0')+'</span><span>'+escapeHtml(entry.player_name)+'</span><strong>'+Number(entry.score).toLocaleString()+'</strong><small>WAVE '+entry.wave+'</small>';listEl.appendChild(li);});}catch{monthEl.textContent='Offline';}}
  reset();draw();loadBoard();
})();
