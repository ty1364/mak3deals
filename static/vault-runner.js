(() => {
  const canvas = document.getElementById('vaultCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = 1200, H = 700, PAD = 48;
  const startOverlay = document.getElementById('startOverlay');
  const upgradeOverlay = document.getElementById('upgradeOverlay');
  const endOverlay = document.getElementById('endOverlay');
  const startBtn = document.getElementById('startBtn');
  const restartBtn = document.getElementById('restartBtn');
  const choicesEl = document.getElementById('upgradeChoices');
  const scoreEl = document.getElementById('finalScore');
  const runSummary = document.getElementById('runSummary');
  const playerName = document.getElementById('playerName');
  const submitBtn = document.getElementById('submitScoreBtn');
  const scoreMessage = document.getElementById('scoreMessage');
  const monthEl = document.getElementById('leaderboardMonth');
  const listEl = document.getElementById('leaderboardList');
  const keys = new Set();
  const upgrades = {
    magnet: {icon:'◎', title:'MAGNET CORE', copy:'Pull savings shards toward you from farther away.'},
    shield: {icon:'◇', title:'SCAM SHIELD', copy:'Absorb one scam bot hit every round.'},
    sprint: {icon:'»', title:'QUICK CART', copy:'Move faster and make tighter escapes.'},
    multiplier: {icon:'×', title:'STACKED SAVINGS', copy:'Every combo pays more points.'},
    extra: {icon:'♥', title:'EXTRA LIFE', copy:'Add one life to your run right now.'}
  };
  let phase='idle', last=0, round=1, score=0, lives=3, combo=0, bestCombo=0, collected=0, target=6, roundLeft=24, spawnClock=0, runStartedAt=0, lastRun=null;
  let player={x:W/2,y:H/2,r:19}, pointer={x:W/2,y:H/2,active:false}, objects=[], particles=[], shield=0, upgradeLevels={magnet:0,shield:0,sprint:0,multiplier:0,extra:0};
  const random = (min,max)=>min+Math.random()*(max-min);
  const dist = (a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
  const escapeHtml = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  function reset(){phase='idle';round=1;score=0;lives=3;combo=0;bestCombo=0;collected=0;target=6;roundLeft=24;spawnClock=0;objects=[];particles=[];shield=0;upgradeLevels={magnet:0,shield:0,sprint:0,multiplier:0,extra:0};player={x:W/2,y:H/2,r:19};pointer={x:W/2,y:H/2,active:false};lastRun=null;scoreMessage.textContent='';}
  function start(){reset();phase='running';runStartedAt=Date.now();startOverlay.classList.add('hidden');upgradeOverlay.classList.add('hidden');endOverlay.classList.add('hidden');canvas.focus();last=performance.now();requestAnimationFrame(loop);}
  function beginRound(){roundLeft=Math.max(12,24-round*.7);target=5+round*2;collected=0;objects=[];spawnClock=.2;player={x:W/2,y:H/2,r:19};phase='running';upgradeOverlay.classList.add('hidden');}
  function showUpgrade(){phase='upgrade';upgradeOverlay.classList.remove('hidden');const pool=Object.keys(upgrades).sort(()=>Math.random()-.5).slice(0,3);choicesEl.innerHTML=pool.map(key=>{const u=upgrades[key];return `<button class="upgrade-choice" data-upgrade="${key}" type="button"><span class="upgrade-icon">${u.icon}</span><strong>${u.title}</strong><small>${u.copy}</small></button>`;}).join('');choicesEl.querySelectorAll('[data-upgrade]').forEach(button=>button.addEventListener('click',()=>chooseUpgrade(button.dataset.upgrade)));}
  function chooseUpgrade(key){upgradeLevels[key]++;if(key==='shield'||key==='extra')shield++;if(key==='extra')lives++;round++;beginRound();}
  function end(reason){phase='over';lastRun={score:Math.max(1,Math.floor(score)),wave:round,duration:Math.max(10,Math.floor((Date.now()-runStartedAt)/1000))};scoreEl.textContent=lastRun.score.toLocaleString();runSummary.textContent=`${reason} · ROUND ${round} · BEST COMBO ${bestCombo}`;endOverlay.classList.remove('hidden');loadBoard();}
  function spawn(){const kind=Math.random()<Math.max(.58,.78-round*.018)?'deal':'hazard';const angle=random(0,Math.PI*2), radius=random(220,480);const x=Math.max(PAD+22,Math.min(W-PAD-22,W/2+Math.cos(angle)*radius)),y=Math.max(110,Math.min(H-110,H/2+Math.sin(angle)*radius));objects.push({kind,x,y,r:kind==='deal'?13:20,life:0,spin:random(0,6),value:80+round*12,speed:34+round*5});}
  function burst(x,y,color,count=15){for(let i=0;i<count;i++)particles.push({x,y,vx:random(-150,150),vy:random(-150,150),life:random(.35,.85),color});}
  function collect(obj){if(obj.kind==='hazard'){if(shield>0){shield--;burst(obj.x,obj.y,'#77e7ff',18);}else{lives--;combo=0;burst(obj.x,obj.y,'#ff607d',20);}return;}collected++;combo++;bestCombo=Math.max(bestCombo,combo);const multiplier=1+upgradeLevels.multiplier+Math.floor(combo/6);score+=obj.value*multiplier;burst(obj.x,obj.y,'#ffd36f',20);if(collected>=target)showUpgrade();}
  function update(dt){
    if(phase!=='running')return;roundLeft-=dt;spawnClock-=dt;
    if(spawnClock<=0){spawn();spawnClock=Math.max(.28,.9-round*.035);}
    let mx=(keys.has('ArrowRight')||keys.has('d')?1:0)-(keys.has('ArrowLeft')||keys.has('a')?1:0);let my=(keys.has('ArrowDown')||keys.has('s')?1:0)-(keys.has('ArrowUp')||keys.has('w')?1:0);const speed=210+upgradeLevels.sprint*42;
    if(mx||my){const len=Math.hypot(mx,my)||1;player.x+=mx/len*speed*dt;player.y+=my/len*speed*dt;}else if(pointer.active){const dx=pointer.x-player.x,dy=pointer.y-player.y,len=Math.hypot(dx,dy);if(len>5){player.x+=dx/len*speed*dt;player.y+=dy/len*speed*dt;}}
    player.x=Math.max(PAD+player.r,Math.min(W-PAD-player.r,player.x));player.y=Math.max(94+player.r,Math.min(H-70-player.r,player.y));
    for(const obj of objects){obj.life+=dt;if(obj.kind==='hazard'){const dx=player.x-obj.x,dy=player.y-obj.y,len=Math.hypot(dx,dy)||1;obj.x+=dx/len*obj.speed*dt;obj.y+=dy/len*obj.speed*dt;}if(dist(player,obj)<player.r+obj.r+(obj.kind==='deal'?upgradeLevels.magnet*18:0))obj.hit=true;}
    for(let i=objects.length-1;i>=0;i--)if(objects[i].hit){const obj=objects.splice(i,1)[0];collect(obj);if(phase!=='running')break;}
    for(let i=particles.length-1;i>=0;i--){const p=particles[i];p.x+=p.vx*dt;p.y+=p.vy*dt;p.vy+=80*dt;p.life-=dt;if(p.life<=0)particles.splice(i,1);}
    if(lives<=0)end('THE VAULT GOT YOU');else if(roundLeft<=0){lives--;if(lives<=0)end('TIME RAN OUT');else{combo=0;roundLeft=18;objects=[];player={x:W/2,y:H/2,r:19};}}
  }
  function diamond(x,y,r,fill){ctx.save();ctx.translate(x,y);ctx.rotate(Math.PI/4);ctx.fillStyle=fill;ctx.shadowColor=fill;ctx.shadowBlur=18;ctx.fillRect(-r/1.4,-r/1.4,r*1.4,r*1.4);ctx.restore();}
  function draw(){
    const g=ctx.createRadialGradient(W/2,H/2,30,W/2,H/2,650);g.addColorStop(0,'#24265e');g.addColorStop(.45,'#111637');g.addColorStop(1,'#080817');ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
    ctx.strokeStyle='rgba(141,247,197,.12)';ctx.lineWidth=2;for(let x=70;x<W;x+=120){ctx.beginPath();ctx.moveTo(x,90);ctx.lineTo(x,630);ctx.stroke();}for(let y=120;y<640;y+=90){ctx.beginPath();ctx.moveTo(48,y);ctx.lineTo(W-48,y);ctx.stroke();}
    ctx.strokeStyle='rgba(255,211,111,.15)';ctx.lineWidth=5;ctx.strokeRect(48,90,W-96,H-160);ctx.fillStyle='rgba(255,211,111,.05)';for(let i=0;i<6;i++){ctx.fillRect(70+i*190,110,140,8);ctx.fillRect(70+i*190,580,140,8);}
    ctx.fillStyle='#f8fbff';ctx.font='900 22px system-ui';ctx.fillText('VAULT RUNNER',34,40);ctx.font='800 13px system-ui';ctx.fillStyle='#ffd36f';ctx.fillText('ROUND '+round,36,66);ctx.fillStyle='#8df7c5';ctx.fillText('SAVINGS '+collected+'/'+target,155,66);ctx.fillStyle='#c6c8e7';ctx.fillText('SCORE '+Math.floor(score).toLocaleString(),325,66);ctx.fillStyle='#ff9eae';ctx.fillText('LIVES '+'♥'.repeat(Math.max(0,lives)),475,66);ctx.fillStyle='#ffd36f';ctx.fillText('TIME '+Math.max(0,Math.ceil(roundLeft))+'s',W-130,40);
    for(const obj of objects){if(obj.kind==='deal'){diamond(obj.x,obj.y,15,'#ffd36f');ctx.fillStyle='#1a1638';ctx.font='900 15px system-ui';ctx.fillText('$',obj.x-5,obj.y+6);}else{ctx.save();ctx.translate(obj.x,obj.y);ctx.rotate(Math.PI/4);ctx.fillStyle='#ff5f7c';ctx.shadowColor='#ff416c';ctx.shadowBlur=22;ctx.fillRect(-15,-15,30,30);ctx.restore();ctx.fillStyle='#fff';ctx.font='900 14px system-ui';ctx.fillText('!',obj.x-4,obj.y+5);}}
    ctx.save();ctx.translate(player.x,player.y);if(shield){ctx.strokeStyle='rgba(119,231,255,.8)';ctx.lineWidth=5;ctx.shadowColor='#77e7ff';ctx.shadowBlur=20;ctx.beginPath();ctx.arc(0,0,42,0,Math.PI*2);ctx.stroke();}ctx.fillStyle='#8df7c5';ctx.shadowColor='#8df7c5';ctx.shadowBlur=24;ctx.beginPath();ctx.arc(0,0,player.r,0,Math.PI*2);ctx.fill();ctx.fillStyle='#111637';ctx.font='900 15px system-ui';ctx.fillText('M',-6,5);ctx.fillStyle='#ffd36f';ctx.fillRect(-12,25,24,5);ctx.restore();
    for(const p of particles){ctx.globalAlpha=Math.max(0,p.life);ctx.fillStyle=p.color;ctx.fillRect(p.x,p.y,5,5);}ctx.globalAlpha=1;
  }
  function loop(now){if(phase==='idle'||phase==='over')return;const dt=Math.min(.033,(now-last)/1000);last=now;update(dt);draw();if(phase!=='over')requestAnimationFrame(loop);}
  function movePointer(e){const r=canvas.getBoundingClientRect();pointer.x=(e.clientX-r.left)*(W/r.width);pointer.y=(e.clientY-r.top)*(H/r.height);pointer.active=true;}
  canvas.addEventListener('pointermove',movePointer);canvas.addEventListener('pointerdown',e=>{movePointer(e);canvas.setPointerCapture?.(e.pointerId);});
  window.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','w','a','s','d'].includes(e.key)){e.preventDefault();keys.add(e.key);}});window.addEventListener('keyup',e=>keys.delete(e.key));
  startBtn.addEventListener('click',start);restartBtn.addEventListener('click',start);
  submitBtn.addEventListener('click',async()=>{const name=playerName.value.trim();if(name.length<2){scoreMessage.textContent='Enter at least 2 characters.';return;}submitBtn.disabled=true;scoreMessage.textContent='Submitting…';try{const res=await fetch('/api/score',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({game:'vault-runner',name,...lastRun})});const data=await res.json();scoreMessage.textContent=data.message||data.error||'Done.';loadBoard();}catch{scoreMessage.textContent='Could not submit right now.';}finally{submitBtn.disabled=false;}});
  async function loadBoard(){try{const res=await fetch('/api/leaderboard?game=vault-runner');const data=await res.json();monthEl.textContent=data.month||'Current month';listEl.replaceChildren();if(!data.scores.length){const li=document.createElement('li');li.textContent='No raids yet — be the first runner.';listEl.appendChild(li);return;}data.scores.forEach((entry,i)=>{const li=document.createElement('li');li.innerHTML='<span class="rank">'+String(i+1).padStart(2,'0')+'</span><span>'+escapeHtml(entry.player_name)+'</span><strong>'+Number(entry.score).toLocaleString()+'</strong><small>ROUND '+entry.wave+'</small>';listEl.appendChild(li);});}catch{monthEl.textContent='Offline';}}
  reset();draw();loadBoard();
})();
