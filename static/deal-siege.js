(() => {
  const canvas = document.getElementById('siegeCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width; const H = canvas.height; const FLOOR = 575;
  const asset = new Image(); asset.src = '/static/assets/games/deal-siege/deal-siege-asset-sheet-v1.png';
  const sprites = {
    teal: [0, 0, 510, 470], coral: [510, 0, 510, 470], gold: [1020, 0, 660, 470],
    crate: [0, 440, 360, 480], coin: [340, 430, 360, 480], bomb: [690, 430, 350, 480],
    shield: [1000, 430, 410, 480], sling: [1370, 430, 310, 480]
  };
  const palette = { teal: '#20d8c6', coral: '#ff6b70', gold: '#ffc438' };
  const startOverlay = document.getElementById('startOverlay'); const endOverlay = document.getElementById('endOverlay');
  const startBtn = document.getElementById('startBtn'); const restartBtn = document.getElementById('restartBtn');
  const fireBtn = document.getElementById('fireBtn');
  const scoreEl = document.getElementById('finalScore'); const summaryEl = document.getElementById('runSummary');
  const nameEl = document.getElementById('playerName'); const submitBtn = document.getElementById('submitScoreBtn'); const messageEl = document.getElementById('scoreMessage');
  const monthEl = document.getElementById('leaderboardMonth'); const listEl = document.getElementById('leaderboardList');
  let phase = 'idle'; let lastFrame = 0; let elapsed = 0; let timeLeft = 45; let playerScore = 0; let rivalScore = 0;
  let playerColor = 'teal'; let rivalColor = 'coral'; let playerTargets = []; let rivalTargets = []; let projectiles = []; let particles = [];
  let aim = { dragging: false, x: 120, y: 520 }; let aiClock = 1.8; let runStartedAt = 0; let lastRun = null; let lastLaunchAt = 0;

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));

  function drawSprite(name, x, y, width, height, flip = false, alpha = 1) {
    if (!asset.complete || !asset.naturalWidth) return false;
    const [sx, sy, sw, sh] = sprites[name]; ctx.save(); ctx.globalAlpha = alpha; ctx.translate(x + (flip ? width : 0), y); ctx.scale(flip ? -1 : 1, 1);
    ctx.drawImage(asset, sx, sy, sw, sh, 0, 0, width, height); ctx.restore(); return true;
  }

  function buildTargets(side) {
    const baseX = side === 'player' ? 340 : 860; const direction = side === 'player' ? 1 : -1;
    const positions = [
      [0, 0], [1, 0], [2, 0], [0.5, 1], [1.5, 1], [1, 2]
    ];
    return positions.map(([column, row], index) => ({
      owner: side, x: baseX + direction * column * 58, y: FLOOR - row * 58, type: index === 2 ? 'bomb' : index === 4 ? 'shield' : 'crate',
      health: index === 5 ? 2 : 1, maxHealth: index === 5 ? 2 : 1, alive: true, reinforced: 0, wobble: 0
    }));
  }

  function reset() {
    phase = 'idle'; elapsed = 0; timeLeft = 45; playerScore = 0; rivalScore = 0; playerTargets = buildTargets('player'); rivalTargets = buildTargets('rival');
    projectiles = []; particles = []; aiClock = 1.8; aim = { dragging: false, x: 120, y: 520 }; lastRun = null; messageEl.textContent = '';
  }

  function start() {
    reset(); phase = 'race'; runStartedAt = Date.now(); startOverlay.classList.add('hidden'); endOverlay.classList.add('hidden'); fireBtn.classList.remove('hidden'); canvas.focus(); lastFrame = performance.now(); requestAnimationFrame(loop);
  }

  function finish() {
    phase = 'over'; const winner = playerScore === rivalScore ? 'TIE GAME' : playerScore > rivalScore ? 'YOU WIN' : 'RIVAL WINS';
    lastRun = { score: Math.max(1, Math.floor(playerScore)), wave: Math.max(1, Math.floor(playerScore / 100)), duration: Math.max(10, Math.floor((Date.now() - runStartedAt) / 1000)) };
    scoreEl.textContent = lastRun.score.toLocaleString(); summaryEl.textContent = `${winner} · ${playerScore} YOUR POINTS · ${rivalScore} RIVAL POINTS`;
    document.getElementById('endTitle').textContent = winner === 'YOU WIN' ? 'CHAMPION' : winner === 'TIE GAME' ? 'DEAD EVEN' : 'RIVAL WINS'; fireBtn.classList.add('hidden'); endOverlay.classList.remove('hidden'); loadBoard();
  }

  function screenPoint(event) { const rect = canvas.getBoundingClientRect(); return { x: (event.clientX - rect.left) * W / rect.width, y: (event.clientY - rect.top) * H / rect.height }; }
  function launchPlayer(point) {
    const origin = { x: 128, y: 520 }; const dx = clamp(point.x - origin.x, 70, 280); const dy = clamp(point.y - origin.y, -260, 120); const power = clamp(Math.hypot(dx, dy), 70, 300);
    projectiles.push({ x: origin.x, y: origin.y, vx: dx * 2.6, vy: dy * 2.6, owner: 'player', radius: 18, spin: 0 }); aim.dragging = false; lastLaunchAt = performance.now(); burst(origin.x, origin.y, palette[playerColor], 8);
  }

  function fireDefault() { if (phase === 'race') launchPlayer({ x: W * .8, y: 450 }); }

  function launchAi() {
    const living = playerTargets.filter(target => target.alive); if (!living.length) return;
    const target = living[Math.floor(Math.random() * living.length)]; const origin = { x: 1070, y: 520 }; const dx = target.x - origin.x; const dy = target.y - origin.y - 100;
    projectiles.push({ x: origin.x, y: origin.y, vx: dx * .92, vy: dy * .92, owner: 'rival', radius: 18, spin: 0 }); burst(origin.x, origin.y, palette[rivalColor], 6);
  }

  function knock(target, owner) {
    if (!target.alive) return;
    target.alive = false; target.wobble = 1; if (owner === 'player') playerScore += 100; else rivalScore += 100;
    burst(target.x, target.y - 25, target.type === 'bomb' ? '#ff6b70' : '#ffd36f', target.type === 'bomb' ? 28 : 16);
    if (target.type === 'bomb') {
      const all = target.owner === 'player' ? playerTargets : rivalTargets;
      all.filter(other => other.alive && distance(target, other) < 145).forEach(other => { other.alive = false; if (owner === 'player') playerScore += 100; else rivalScore += 100; burst(other.x, other.y - 24, '#ff9a70', 14); });
    }
    if (target.type === 'shield') {
      const all = target.owner === 'player' ? playerTargets : rivalTargets;
      all.filter(other => other.alive && distance(target, other) < 190).forEach(other => { other.health = Math.min(other.maxHealth + 1, other.health + 1); other.maxHealth += 1; other.reinforced = 1.8; });
    }
  }

  function impact(target, projectile) {
    if (projectile.owner === target.owner) return;
    if (target.type === 'shield') { knock(target, projectile.owner); return; }
    target.health -= 1; target.reinforced = 0; if (target.health <= 0) knock(target, projectile.owner); else burst(target.x, target.y - 20, '#fff', 6);
  }

  function burst(x, y, color, count = 12) { for (let index = 0; index < count; index += 1) particles.push({ x, y, vx: (Math.random() - .5) * 260, vy: (Math.random() - .75) * 240, life: .45 + Math.random() * .65, color }); }

  function update(dt) {
    if (phase !== 'race') return;
    elapsed += dt; timeLeft -= dt; aiClock -= dt;
    if (aiClock <= 0) { launchAi(); aiClock = 2.2 + Math.random() * 1.4; }
    for (const projectile of projectiles) { projectile.x += projectile.vx * dt; projectile.y += projectile.vy * dt; projectile.vy += 420 * dt; projectile.spin += dt * 7; }
    for (const projectile of projectiles) {
      if (!projectile.active) continue;
      const targets = projectile.owner === 'player' ? rivalTargets : playerTargets;
      const hit = targets.find(target => target.alive && distance(projectile, { x: target.x, y: target.y - 28 }) < projectile.radius + 30);
      if (hit) { impact(hit, projectile); projectile.active = false; }
      if (projectile.x < -80 || projectile.x > W + 80 || projectile.y > H + 80 || projectile.y < -80) projectile.active = false;
    }
    projectiles = projectiles.filter(projectile => projectile.active); for (const target of [...playerTargets, ...rivalTargets]) target.reinforced = Math.max(0, target.reinforced - dt);
    for (let index = particles.length - 1; index >= 0; index -= 1) { const particle = particles[index]; particle.x += particle.vx * dt; particle.y += particle.vy * dt; particle.vy += 280 * dt; particle.life -= dt; if (particle.life <= 0) particles.splice(index, 1); }
    if (timeLeft <= 0 || !rivalTargets.some(target => target.alive) || !playerTargets.some(target => target.alive)) finish();
  }

  function drawBackground() {
    const sky = ctx.createLinearGradient(0, 0, 0, H); sky.addColorStop(0, '#a7f3f0'); sky.addColorStop(.55, '#4bbfc0'); sky.addColorStop(1, '#0b4657'); ctx.fillStyle = sky; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#f9d58a'; ctx.globalAlpha = .8; ctx.beginPath(); ctx.arc(990, 120, 70, 0, Math.PI * 2); ctx.fill(); ctx.globalAlpha = 1;
    ctx.fillStyle = '#27798a'; ctx.beginPath(); ctx.moveTo(0, 350); ctx.lineTo(170, 210); ctx.lineTo(310, 360); ctx.lineTo(470, 190); ctx.lineTo(650, 360); ctx.lineTo(820, 220); ctx.lineTo(1010, 360); ctx.lineTo(1200, 190); ctx.lineTo(1200, FLOOR); ctx.lineTo(0, FLOOR); ctx.closePath(); ctx.fill();
    ctx.fillStyle = '#0e4d55'; ctx.fillRect(0, FLOOR, W, H - FLOOR); ctx.fillStyle = '#41c57f'; ctx.fillRect(0, FLOOR - 9, W, 9);
    ctx.strokeStyle = '#ffd36f66'; ctx.lineWidth = 3; for (let x = 0; x < W; x += 70) { ctx.beginPath(); ctx.moveTo(x, FLOOR + 38); ctx.lineTo(x + 25, FLOOR + 6); ctx.stroke(); }
  }

  function drawTarget(target) {
    if (!target.alive) return;
    const size = 66; const sprite = target.type === 'bomb' ? 'bomb' : target.type === 'shield' ? 'shield' : 'crate'; drawSprite(sprite, target.x - size / 2, target.y - size, size, size);
    if (target.health > 1) { ctx.fillStyle = '#10253699'; ctx.fillRect(target.x - 26, target.y - 77, 52, 5); ctx.fillStyle = '#8df7c5'; ctx.fillRect(target.x - 26, target.y - 77, 52 * target.health / target.maxHealth, 5); }
    if (target.reinforced > 0) { ctx.strokeStyle = '#8df7c5'; ctx.lineWidth = 3; ctx.setLineDash([6, 5]); ctx.beginPath(); ctx.arc(target.x, target.y - 32, 42, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]); }
  }

  function drawProjectile(projectile) { ctx.save(); ctx.translate(projectile.x, projectile.y); ctx.rotate(projectile.spin); ctx.fillStyle = projectile.owner === 'player' ? palette[playerColor] : palette[rivalColor]; ctx.shadowColor = ctx.fillStyle; ctx.shadowBlur = 15; ctx.beginPath(); ctx.arc(0, 0, projectile.radius, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0; ctx.fillStyle = '#fff'; ctx.font = '900 16px system-ui'; ctx.textAlign = 'center'; ctx.fillText('%', 0, 6); ctx.restore(); }

  function drawFighter(color, x, y, flip = false, label = 'YOU') { drawSprite(color, x - 42, y - 80, 84, 80, flip); ctx.fillStyle = '#fff'; ctx.font = '900 11px system-ui'; ctx.textAlign = 'center'; ctx.fillText(label, x, y + 14); }
  function drawAim() { if (!aim.dragging) return; const origin = { x: 128, y: 520 }; ctx.save(); ctx.strokeStyle = palette[playerColor]; ctx.globalAlpha = .75; ctx.lineWidth = 5; ctx.setLineDash([10, 8]); ctx.beginPath(); ctx.moveTo(origin.x, origin.y); ctx.lineTo(aim.x, aim.y); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = .35; ctx.beginPath(); ctx.arc(aim.x, aim.y, 20, 0, Math.PI * 2); ctx.stroke(); ctx.restore(); }
  function drawParticles() { for (const particle of particles) { ctx.globalAlpha = Math.max(0, particle.life); ctx.fillStyle = particle.color; ctx.fillRect(particle.x - 3, particle.y - 3, 7, 7); } ctx.globalAlpha = 1; }

  function draw() {
    drawBackground(); drawSprite('sling', 68, 474, 120, 120); drawSprite('sling', 1012, 474, 120, 120, true); drawFighter(playerColor, 126, 455, false, 'YOU'); drawFighter(rivalColor, 1074, 455, true, 'RIVAL');
    playerTargets.forEach(drawTarget); rivalTargets.forEach(drawTarget); projectiles.forEach(drawProjectile); drawAim(); drawParticles();
    ctx.fillStyle = '#072032d9'; ctx.fillRect(0, 0, W, 78); ctx.fillStyle = '#fff'; ctx.font = '900 22px system-ui'; ctx.textAlign = 'left'; ctx.fillText('DEAL SIEGE', 30, 33); ctx.font = '800 13px system-ui'; ctx.fillStyle = '#8df7c5'; ctx.fillText('YOUR KNOCKDOWNS', 30, 58); ctx.fillStyle = '#ffd36f'; ctx.font = '900 24px system-ui'; ctx.fillText(playerScore, 190, 58); ctx.fillStyle = '#ff9eae'; ctx.font = '800 13px system-ui'; ctx.fillText('RIVAL', 320, 58); ctx.fillStyle = '#fff'; ctx.font = '900 24px system-ui'; ctx.fillText(rivalScore, 370, 58); ctx.fillStyle = '#ffd36f'; ctx.font = '900 28px system-ui'; ctx.textAlign = 'center'; ctx.fillText(`${Math.max(0, Math.ceil(timeLeft))}s`, W / 2, 48); ctx.font = '800 12px system-ui'; ctx.fillStyle = '#d7eef0'; ctx.fillText('KNOCK MORE TARGETS BEFORE TIME RUNS OUT', W / 2, 68); ctx.textAlign = 'right'; ctx.fillStyle = '#d7eef0'; ctx.font = '800 12px system-ui'; ctx.fillText(`AIM WITH MOUSE/TOUCH · ${playerColor.toUpperCase()} RACER`, W - 30, 45);
  }

  function loop(now) { if (phase === 'idle' || phase === 'over') return; const dt = Math.min(.033, (now - lastFrame) / 1000); lastFrame = now; update(dt); draw(); if (phase === 'race') requestAnimationFrame(loop); }

  canvas.addEventListener('pointerdown', event => { if (phase !== 'race') return; const point = screenPoint(event); if (point.x < 245 && point.y > 410) { aim.dragging = true; aim.x = point.x; aim.y = point.y; canvas.setPointerCapture(event.pointerId); } });
  canvas.addEventListener('pointermove', event => { if (!aim.dragging) return; const point = screenPoint(event); aim.x = clamp(point.x, 170, 480); aim.y = clamp(point.y, 230, 570); });
  canvas.addEventListener('pointerup', event => { if (!aim.dragging) return; launchPlayer(screenPoint(event)); });
  canvas.addEventListener('click', event => { if (phase !== 'race' || performance.now() - lastLaunchAt < 250) return; const point = screenPoint(event); if (point.x > 180) launchPlayer({ x: W * .8, y: 450 }); });
  window.addEventListener('keydown', event => { if (event.key.toLowerCase() === 'r') start(); else if (event.key === ' ') { event.preventDefault(); fireDefault(); } });
  document.querySelectorAll('.color-choice').forEach(button => button.addEventListener('click', () => { playerColor = button.dataset.color; document.querySelectorAll('.color-choice').forEach(choice => choice.classList.toggle('selected', choice === button)); }));
  startBtn.addEventListener('click', start); restartBtn.addEventListener('click', start); fireBtn.addEventListener('click', fireDefault);
  submitBtn.addEventListener('click', async () => { const name = nameEl.value.trim(); if (name.length < 2) { messageEl.textContent = 'Enter at least 2 characters.'; return; } submitBtn.disabled = true; messageEl.textContent = 'Submitting…'; try { const response = await fetch('/api/score', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ game: 'deal-siege', name, ...lastRun }) }); const data = await response.json(); messageEl.textContent = data.message || data.error || 'Done.'; loadBoard(); } catch { messageEl.textContent = 'Could not submit right now.'; } finally { submitBtn.disabled = false; } });
  async function loadBoard() { try { const response = await fetch('/api/leaderboard?game=deal-siege'); const data = await response.json(); monthEl.textContent = data.month || 'Current month'; listEl.replaceChildren(); if (!data.scores.length) { const empty = document.createElement('li'); empty.textContent = 'No finalists yet — be the first to qualify.'; listEl.appendChild(empty); return; } data.scores.forEach((entry, index) => { const item = document.createElement('li'); item.innerHTML = `<span class="rank">${String(index + 1).padStart(2, '0')}</span><span>${escapeHtml(entry.player_name)}</span><strong>${Number(entry.score).toLocaleString()}</strong><small>ROUND ${entry.wave}</small>`; listEl.appendChild(item); }); } catch { monthEl.textContent = 'Offline'; } }
  reset(); draw(); loadBoard();
})();
