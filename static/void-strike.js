const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const scoreEl = document.getElementById('score');
const waveEl = document.getElementById('wave');
const comboEl = document.getElementById('combo');
const livesEl = document.getElementById('lives');
const rapidStatusEl = document.getElementById('rapidStatus');
const novaFill = document.getElementById('novaFill');
const startScreen = document.getElementById('startScreen');
const gameOver = document.getElementById('gameOver');
const finalScore = document.getElementById('finalScore');
const bossWarning = document.getElementById('bossWarning');
const startBtn = document.getElementById('startBtn');
const restartBtn = document.getElementById('restartBtn');

const TAU = Math.PI * 2;
let W = 1280, H = 720, dpr = 1;
let running = false, last = 0, elapsed = 0, spawnClock = 0;
let score = 0, wave = 1, combo = 1, comboTimer = 0, shake = 0;
let runStartedAt = 0;
let nova = 1, novaCooldown = 7;
let mouse = { x: W / 2, y: H / 2, down: false };
let bullets = [], enemies = [], particles = [], rings = [], texts = [], stars = [], pickups = [];
let core = { x: W / 2, y: H / 2, hp: 100, radius: 34, lives: 3, invuln: 0 };
let rapidFire = { active: false, timer: 0, shotClock: 0, duration: 9, interval: 0.07 };
let pickupClock = 7;

function resize() {
  const rect = canvas.getBoundingClientRect();
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.floor(rect.width * dpr);
  canvas.height = Math.floor(rect.height * dpr);
  W = rect.width; H = rect.height;
  core.x = W / 2; core.y = H / 2;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
window.addEventListener('resize', resize);
resize();

function rand(a,b){ return a + Math.random() * (b-a); }
function clamp(v,a,b){ return Math.max(a,Math.min(b,v)); }
function dist(a,b){ return Math.hypot(a.x-b.x,a.y-b.y); }

function resetGame(){
  score=0; wave=1; combo=1; comboTimer=0; elapsed=0; spawnClock=0; nova=1; shake=0;
  bullets=[]; enemies=[]; particles=[]; rings=[]; texts=[]; pickups=[];
  core.hp=100; core.lives=3; core.invuln=0; core.x=W/2; core.y=H/2;
  rapidFire.active=false; rapidFire.timer=0; rapidFire.shotClock=0; pickupClock=6;
  stars = Array.from({length:170},()=>({x:Math.random()*W,y:Math.random()*H,z:rand(.2,1),tw:rand(0,TAU)}));
  updateHUD();
}

function startGame(){
  resetGame(); running=true; runStartedAt=Date.now(); last=performance.now();
  startScreen.classList.add('hidden'); gameOver.classList.add('hidden');
  requestAnimationFrame(loop);
}
startBtn.addEventListener('click',startGame);
restartBtn.addEventListener('click',startGame);

canvas.addEventListener('mousemove', e => {
  const r=canvas.getBoundingClientRect(); mouse.x=e.clientX-r.left; mouse.y=e.clientY-r.top;
});
canvas.addEventListener('mousedown', e => {
  if(e.button===0){ mouse.down=true; if(running) fire(); }
});
window.addEventListener('mouseup', e => { if(e.button===0) mouse.down=false; });
window.addEventListener('keydown', e => {
  if(e.code==='Space'){
    e.preventDefault();
    if(!running && !startScreen.classList.contains('hidden')) startGame();
    else if(running) novaBlast();
  }
});

function fire(){
  const dx=mouse.x-core.x, dy=mouse.y-core.y, len=Math.hypot(dx,dy)||1;
  const ux=dx/len, uy=dy/len;
  const speed = rapidFire.active ? 1100 : 980;
  bullets.push({x:core.x+ux*42,y:core.y+uy*42,vx:ux*speed,vy:uy*speed,r:rapidFire.active?4:5,life:1.1,power:rapidFire.active?1:1});
  muzzle(core.x+ux*42,core.y+uy*42,ux,uy,rapidFire.active?'#ffe94d':'#4ff2ff');
  shake=Math.max(shake,rapidFire.active?1.4:2.2);
}

function novaBlast(){
  if(nova < .999) return;
  nova=0;
  rings.push({x:core.x,y:core.y,r:20,max:Math.min(W,H)*.64,life:.65,age:0,color:'#69f5ff'});
  shake=18;
  let killed=0;
  enemies.forEach(e=>{
    if(dist(e,core)<Math.min(W,H)*.42){ e.dead=true; burst(e.x,e.y,e.color,22,2.3); maybeDrop(e); killed++; }
  });
  if(killed){ score += killed*250*combo; combo=Math.min(combo+killed,99); comboTimer=2.4; }
  flashText('NOVA // '+killed+' ERASED',core.x,core.y-80,'#ffffff',34);
}

function spawnEnemy(){
  const side=Math.floor(Math.random()*4); let x,y;
  if(side===0){x=rand(-40,W+40);y=-40;} else if(side===1){x=W+40;y=rand(-40,H+40);} else if(side===2){x=rand(-40,W+40);y=H+40;} else {x=-40;y=rand(-40,H+40);}
  const roll=Math.random();
  const type = roll < .12 && wave>2 ? 'tank' : roll < .34 && wave>1 ? 'zig' : 'drone';
  const scale = 1 + Math.min(1.8, (wave - 1) * .055);
  const spec = type==='tank' ? {r:25,hp:4 + Math.floor(wave / 5),speed:42,color:'#ff335f',score:450} : type==='zig' ? {r:14,hp:2 + Math.floor(wave / 8),speed:95,color:'#b65cff',score:260} : {r:11,hp:1,speed:72,color:'#2be8ff',score:140};
  enemies.push({x,y,phase:rand(0,TAU),type,...spec,speed:spec.speed*scale,dead:false});
}

function spawnPickup(type=null,x=null,y=null){
  const kinds=['energy','life','rapid'];
  const chosen=type || kinds[Math.floor(Math.random()*kinds.length)];
  pickups.push({
    x:x ?? rand(W*.18,W*.82),
    y:y ?? rand(H*.18,H*.82),
    type:chosen,
    r:16,
    age:0,
    life:11,
    phase:rand(0,TAU)
  });
}

function maybeDrop(enemy){
  const chance = enemy.type==='tank' ? .36 : .11;
  if(Math.random() > chance) return;
  const r=Math.random();
  const type = r < .22 ? 'life' : r < .58 ? 'rapid' : 'energy';
  spawnPickup(type,enemy.x,enemy.y);
}

function collectPickup(p){
  if(p.type==='life'){
    core.lives=Math.min(5,core.lives+1);
    flashText('+1 LIFE',p.x,p.y,'#ff5bd7',28);
    rings.push({x:p.x,y:p.y,r:8,max:75,life:.45,age:0,color:'#ff5bd7'});
  } else if(p.type==='energy'){
    core.hp=Math.min(100,core.hp+35);
    nova=Math.min(1,nova+.35);
    flashText('ENERGY +35',p.x,p.y,'#55f7ff',26);
    rings.push({x:p.x,y:p.y,r:8,max:75,life:.45,age:0,color:'#55f7ff'});
  } else {
    rapidFire.active=true;
    rapidFire.timer=rapidFire.duration;
    rapidFire.shotClock=0;
    flashText('RAPID FIRE!',p.x,p.y,'#ffe94d',30);
    rings.push({x:p.x,y:p.y,r:8,max:90,life:.5,age:0,color:'#ffe94d'});
  }
  burst(p.x,p.y,p.type==='life'?'#ff5bd7':p.type==='rapid'?'#ffe94d':'#55f7ff',28,1.5);
}

function takeCoreDamage(amount){
  if(core.invuln>0) return;
  core.hp -= amount;
  shake=14;
  combo=1; comboTimer=0;
  if(core.hp>0) return;
  core.lives--;
  if(core.lives<=0){ endGame(); return; }
  core.hp=100;
  core.invuln=2.2;
  enemies.forEach(e=>{ if(dist(e,core)<160){e.dead=true;burst(e.x,e.y,e.color,16,1.4);} });
  rings.push({x:core.x,y:core.y,r:18,max:220,life:.65,age:0,color:'#ffffff'});
  flashText('LIFE LOST // '+core.lives+' LEFT',core.x,core.y-95,'#ff5bd7',30);
}

function update(dt){
  elapsed += dt;
  const newWave = 1 + Math.floor(elapsed/22);
  if(newWave!==wave){ wave=newWave; flashText('WAVE '+wave, W/2, H*.28, '#ffffff', 46); if(wave%3===0) showBossWarning(); }
  spawnClock -= dt;
  const interval=Math.max(.14,.72-wave*.05);
  if(spawnClock<=0){
    spawnEnemy();
    if(wave>=4 && Math.random()<Math.min(.52,.16+wave*.025)) spawnEnemy();
    if(wave>=9 && Math.random()<.16) spawnEnemy();
    spawnClock=interval;
  }

  pickupClock -= dt;
  if(pickupClock<=0){ spawnPickup(); pickupClock=rand(8,13); }

  nova = Math.min(1, nova + dt/novaCooldown);
  if(core.invuln>0) core.invuln-=dt;
  if(comboTimer>0){ comboTimer-=dt; } else combo=Math.max(1,combo-1);
  shake*=Math.pow(.02,dt);

  if(rapidFire.active){
    rapidFire.timer-=dt;
    rapidFire.shotClock-=dt;
    if(mouse.down && rapidFire.shotClock<=0){ fire(); rapidFire.shotClock=rapidFire.interval; }
    if(rapidFire.timer<=0){ rapidFire.active=false; rapidFire.timer=0; flashText('RAPID FIRE OFFLINE',core.x,core.y+82,'#ffd34d',20); }
  }

  for(const b of bullets){ b.x+=b.vx*dt; b.y+=b.vy*dt; b.life-=dt; }
  bullets=bullets.filter(b=>b.life>0 && b.x>-50&&b.x<W+50&&b.y>-50&&b.y<H+50);

  for(const e of enemies){
    if(e.dead) continue;
    let dx=core.x-e.x, dy=core.y-e.y, len=Math.hypot(dx,dy)||1;
    let ux=dx/len, uy=dy/len;
    if(e.type==='zig'){ const s=Math.sin(elapsed*5+e.phase)*.8; const px=-uy, py=ux; ux+=px*s; uy+=py*s; const n=Math.hypot(ux,uy)||1; ux/=n; uy/=n; }
    e.x += ux*e.speed*(1+wave*.035)*dt; e.y += uy*e.speed*(1+wave*.035)*dt;
    if(Math.hypot(e.x-core.x,e.y-core.y)<e.r+core.radius){
      e.dead=true;
      burst(e.x,e.y,'#ff315e',25,2);
      const damageScale = 1 + Math.min(.85, (wave - 1) * .035);
      takeCoreDamage(Math.ceil((e.type==='tank'?30:e.type==='zig'?18:12) * damageScale));
    }
  }

  for(const b of bullets){
    for(const e of enemies){
      if(e.dead) continue;
      if(Math.hypot(b.x-e.x,b.y-e.y)<b.r+e.r){
        b.life=0; e.hp-=b.power; spark(b.x,b.y,e.color,8);
        if(e.hp<=0){
          e.dead=true; score += e.score*combo; combo=Math.min(combo+1,99); comboTimer=2.1;
          burst(e.x,e.y,e.color,e.type==='tank'?34:18,e.type==='tank'?2.5:1.8);
          maybeDrop(e);
          shake=Math.max(shake,e.type==='tank'?9:4);
          if(combo%10===0) flashText(combo+'X COMBO',e.x,e.y-18,'#ff4ed8',24);
        }
        break;
      }
    }
  }
  enemies=enemies.filter(e=>!e.dead);

  for(const p of pickups){
    p.age+=dt; p.life-=dt;
    if(Math.hypot(p.x-core.x,p.y-core.y)<p.r+core.radius+8){ p.collected=true; collectPickup(p); }
  }
  pickups=pickups.filter(p=>!p.collected && p.life>0);

  for(const p of particles){ p.x+=p.vx*dt; p.y+=p.vy*dt; p.vx*=Math.pow(.08,dt); p.vy*=Math.pow(.08,dt); p.life-=dt; p.rot+=p.spin*dt; }
  particles=particles.filter(p=>p.life>0);
  for(const r of rings){ r.age+=dt; r.r += (r.max-r.r)*Math.min(1,dt*8); r.life-=dt; }
  rings=rings.filter(r=>r.life>0);
  for(const t of texts){ t.y-=26*dt; t.life-=dt; }
  texts=texts.filter(t=>t.life>0);
  updateHUD();
}

function updateHUD(){
  scoreEl.textContent=Math.floor(score).toLocaleString();
  waveEl.textContent=wave;
  comboEl.textContent=combo+'X';
  livesEl.textContent=core.lives;
  novaFill.style.width=(nova*100)+'%';
  rapidStatusEl.textContent=rapidFire.active ? rapidFire.timer.toFixed(1)+'s' : 'OFF';
  rapidStatusEl.style.color=rapidFire.active?'#ffe94d':'';
}

function draw(){
  ctx.save();
  const sx=rand(-shake,shake), sy=rand(-shake,shake); ctx.translate(sx,sy);
  ctx.fillStyle='#02030a'; ctx.fillRect(-30,-30,W+60,H+60);
  drawBackground(); drawRings(); drawPickups(); drawCore(); drawBullets(); drawEnemies(); drawParticles(); drawTexts(); drawVignette();
  ctx.restore();
}

function drawBackground(){
  const g=ctx.createRadialGradient(W/2,H/2,10,W/2,H/2,Math.max(W,H)*.65);
  g.addColorStop(0,'#111845');g.addColorStop(.42,'#080b20');g.addColorStop(1,'#010208');ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
  ctx.save(); ctx.globalCompositeOperation='lighter';
  for(const s of stars){ s.tw+=.02; const a=.18+s.z*.65*(.6+.4*Math.sin(s.tw)); ctx.fillStyle=`rgba(130,220,255,${a})`;ctx.fillRect(s.x,s.y,1+s.z*1.3,1+s.z*1.3); }
  ctx.strokeStyle='rgba(70,110,220,.12)';ctx.lineWidth=1;
  for(let r=90;r<Math.max(W,H);r+=90){ctx.beginPath();ctx.arc(W/2,H/2,r,0,TAU);ctx.stroke();}
  ctx.restore();
}

function drawCore(){
  const hp=clamp(core.hp/100,0,1);
  ctx.save();ctx.translate(core.x,core.y);ctx.globalCompositeOperation='lighter';
  if(core.invuln>0){ctx.globalAlpha=.35+.45*Math.abs(Math.sin(elapsed*14));}
  const glow=ctx.createRadialGradient(0,0,4,0,0,70);glow.addColorStop(0,'rgba(255,255,255,.95)');glow.addColorStop(.16,'rgba(38,235,255,.9)');glow.addColorStop(.5,'rgba(112,68,255,.35)');glow.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=glow;ctx.beginPath();ctx.arc(0,0,72,0,TAU);ctx.fill();
  ctx.rotate(elapsed*.65);ctx.strokeStyle='#70f4ff';ctx.lineWidth=3;ctx.beginPath();for(let i=0;i<6;i++){const a=i*TAU/6;const x=Math.cos(a)*34,y=Math.sin(a)*34;i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.closePath();ctx.stroke();
  ctx.rotate(-elapsed*1.7);ctx.strokeStyle=rapidFire.active?'#ffe94d':'#ff4bd6';ctx.lineWidth=2;ctx.beginPath();ctx.arc(0,0,24,0,TAU);ctx.stroke();
  ctx.restore();
  ctx.fillStyle='rgba(255,255,255,.12)';ctx.fillRect(W/2-76,H-25,152,6);ctx.fillStyle=hp>.5?'#58f2ff':hp>.25?'#ffb72e':'#ff315d';ctx.fillRect(W/2-76,H-25,152*hp,6);
}

function drawBullets(){
  ctx.save();ctx.globalCompositeOperation='lighter';
  for(const b of bullets){
    const c=rapidFire.active?'#ffe94d':'#4ff2ff';
    ctx.strokeStyle=rapidFire.active?'rgba(255,233,77,.5)':'rgba(83,241,255,.45)';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(b.x-b.vx*.02,b.y-b.vy*.02);ctx.lineTo(b.x,b.y);ctx.stroke();ctx.fillStyle='#fff';ctx.shadowBlur=16;ctx.shadowColor=c;ctx.beginPath();ctx.arc(b.x,b.y,b.r,0,TAU);ctx.fill();
  }
  ctx.restore();
}

function drawEnemies(){
  ctx.save();ctx.globalCompositeOperation='lighter';
  for(const e of enemies){ctx.save();ctx.translate(e.x,e.y);ctx.rotate(elapsed*(e.type==='tank'?.5:1.6)+e.phase);ctx.shadowBlur=e.type==='tank'?26:14;ctx.shadowColor=e.color;ctx.strokeStyle=e.color;ctx.fillStyle=e.type==='tank'?'rgba(255,40,88,.16)':'rgba(120,80,255,.10)';ctx.lineWidth=e.type==='tank'?4:2;ctx.beginPath();const sides=e.type==='tank'?8:e.type==='zig'?4:3;for(let i=0;i<sides;i++){const a=i*TAU/sides, rr=e.r*(i%2?0.82:1);const x=Math.cos(a)*rr,y=Math.sin(a)*rr;i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.closePath();ctx.fill();ctx.stroke();ctx.restore();}
  ctx.restore();
}

function drawPickups(){
  ctx.save();ctx.globalCompositeOperation='lighter';
  for(const p of pickups){
    const color=p.type==='life'?'#ff5bd7':p.type==='rapid'?'#ffe94d':'#55f7ff';
    const pulse=1+Math.sin(elapsed*5+p.phase)*.12;
    ctx.save();ctx.translate(p.x,p.y);ctx.rotate(elapsed*1.4+p.phase);ctx.scale(pulse,pulse);ctx.shadowBlur=28;ctx.shadowColor=color;ctx.strokeStyle=color;ctx.fillStyle='rgba(255,255,255,.08)';ctx.lineWidth=3;
    ctx.beginPath();
    for(let i=0;i<6;i++){const a=i*TAU/6;const x=Math.cos(a)*p.r,y=Math.sin(a)*p.r;i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.closePath();ctx.fill();ctx.stroke();
    ctx.rotate(-elapsed*1.4-p.phase);ctx.fillStyle=color;ctx.font='900 14px system-ui';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(p.type==='life'?'+1':p.type==='rapid'?'RF':'E',0,1);ctx.restore();
  }
  ctx.restore();
}

function drawParticles(){
  ctx.save();ctx.globalCompositeOperation='lighter';
  for(const p of particles){ctx.globalAlpha=clamp(p.life/p.maxLife,0,1);ctx.fillStyle=p.color;ctx.shadowBlur=10;ctx.shadowColor=p.color;ctx.save();ctx.translate(p.x,p.y);ctx.rotate(p.rot);ctx.fillRect(-p.size/2,-p.size/2,p.size,p.size*.45);ctx.restore();}
  ctx.restore();ctx.globalAlpha=1;
}

function drawRings(){
  ctx.save();ctx.globalCompositeOperation='lighter';
  for(const r of rings){const a=clamp(r.life/.65,0,1);ctx.strokeStyle=r.color?hexAlpha(r.color,a):`rgba(105,245,255,${a})`;ctx.lineWidth=12*a+2;ctx.shadowBlur=40;ctx.shadowColor=r.color||'#c94cff';ctx.beginPath();ctx.arc(r.x,r.y,r.r,0,TAU);ctx.stroke();}
  ctx.restore();
}

function drawTexts(){
  ctx.save();ctx.textAlign='center';ctx.textBaseline='middle';
  for(const t of texts){ctx.globalAlpha=clamp(t.life/t.maxLife,0,1);ctx.fillStyle=t.color;ctx.shadowBlur=18;ctx.shadowColor=t.color;ctx.font=`900 ${t.size}px system-ui`;ctx.fillText(t.text,t.x,t.y);}
  ctx.restore();ctx.globalAlpha=1;
}

function drawVignette(){
  const g=ctx.createRadialGradient(W/2,H/2,Math.min(W,H)*.24,W/2,H/2,Math.max(W,H)*.7);g.addColorStop(0,'rgba(0,0,0,0)');g.addColorStop(.72,'rgba(0,0,0,.18)');g.addColorStop(1,'rgba(0,0,0,.72)');ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
}

function burst(x,y,color,count=18,power=1.8){
  for(let i=0;i<count;i++){const a=Math.random()*TAU,s=rand(90,330)*power;particles.push({x,y,vx:Math.cos(a)*s,vy:Math.sin(a)*s,life:rand(.28,.72),maxLife:.72,size:rand(3,9),color,rot:rand(0,TAU),spin:rand(-9,9)});}
}
function spark(x,y,color,count=8){burst(x,y,color,count,.55);}
function muzzle(x,y,ux,uy,color='#4ff2ff'){
  for(let i=0;i<7;i++){const a=Math.atan2(uy,ux)+rand(-.45,.45),s=rand(70,220);particles.push({x,y,vx:Math.cos(a)*s,vy:Math.sin(a)*s,life:rand(.08,.22),maxLife:.22,size:rand(2,6),color,rot:rand(0,TAU),spin:rand(-12,12)});}
}
function flashText(text,x,y,color='#fff',size=24){texts.push({text,x,y,color,size,life:1.05,maxLife:1.05});}
function showBossWarning(){
  bossWarning.classList.remove('hidden');
  setTimeout(()=>bossWarning.classList.add('hidden'),1200);
}
function endGame(){
  if(!running) return;
  running=false; mouse.down=false; finalScore.textContent=Math.floor(score).toLocaleString(); gameOver.classList.remove('hidden');
  window.dispatchEvent(new CustomEvent('void-strike-ended', {detail:{score:Math.floor(score),wave,duration:Math.max(10,Math.floor((Date.now()-runStartedAt)/1000))}}));
}
function hexAlpha(hex,a){
  const h=hex.replace('#',''); const v=parseInt(h.length===3?h.split('').map(c=>c+c).join(''):h,16);
  const r=(v>>16)&255,g=(v>>8)&255,b=v&255; return `rgba(${r},${g},${b},${a})`;
}

function loop(now){
  if(!running) return;
  const dt=Math.min(.033,(now-last)/1000||0); last=now;
  update(dt); draw(); requestAnimationFrame(loop);
}

const playerName = document.getElementById('playerName');
const submitScoreBtn = document.getElementById('submitScoreBtn');
const scoreMessage = document.getElementById('scoreMessage');
const leaderboardList = document.getElementById('leaderboardList');
const leaderboardMonth = document.getElementById('leaderboardMonth');
let lastRun = null;

window.addEventListener('void-strike-ended', event => { lastRun = event.detail; if(playerName) playerName.focus(); });

async function loadLeaderboard(){
  try {
    const response = await fetch('/api/leaderboard', {headers:{Accept:'application/json'}});
    const data = await response.json();
    leaderboardMonth.textContent = data.month || 'Current month';
    leaderboardList.replaceChildren();
    if(!data.scores.length){ const li=document.createElement('li'); li.textContent='No runs yet — be the first signal on the board.'; leaderboardList.appendChild(li); return; }
    data.scores.forEach((entry, index) => {
      const li=document.createElement('li');
      li.innerHTML=`<span class="rank">${String(index+1).padStart(2,'0')}</span><span class="player">${escapeHtml(entry.player_name)}</span><strong>${Number(entry.score).toLocaleString()}</strong><small>WAVE ${entry.wave}</small>`;
      leaderboardList.appendChild(li);
    });
  } catch { leaderboardMonth.textContent='Offline'; }
}

function escapeHtml(value){ const div=document.createElement('div'); div.textContent=value; return div.innerHTML; }

submitScoreBtn?.addEventListener('click', async () => {
  if(!lastRun) return;
  const name=(playerName.value||'').trim();
  if(name.length<2){ scoreMessage.textContent='Enter at least 2 characters.'; return; }
  submitScoreBtn.disabled=true; scoreMessage.textContent='Submitting…';
  try {
    const response=await fetch('/api/score',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,...lastRun})});
    const data=await response.json();
    scoreMessage.textContent=data.message||data.error||'Done.';
    if(response.ok) loadLeaderboard();
  } catch { scoreMessage.textContent='Could not submit right now.'; }
  submitScoreBtn.disabled=false;
});

loadLeaderboard();

