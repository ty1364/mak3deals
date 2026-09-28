(() => {
  const canvas = document.getElementById('royaleCanvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  const W = canvas.width;
  const H = canvas.height;
  const laneNames = ['LEFT', 'CENTER', 'RIGHT'];
  const runnerImage = new Image();
  const courseImage = new Image();
  runnerImage.src = '/static/assets/games/deal-dash-royale/runner-cutout-v1.png';
  courseImage.src = '/static/assets/games/deal-dash-royale/skyline-course-v1.png';

  const startOverlay = document.getElementById('startOverlay');
  const roundOverlay = document.getElementById('roundOverlay');
  const endOverlay = document.getElementById('endOverlay');
  const startBtn = document.getElementById('startBtn');
  const nextBtn = document.getElementById('nextRoundBtn');
  const restartBtn = document.getElementById('restartBtn');
  const roundEyebrow = document.getElementById('roundEyebrow');
  const roundTitle = document.getElementById('roundTitle');
  const roundCopy = document.getElementById('roundCopy');
  const scoreEl = document.getElementById('finalScore');
  const summaryEl = document.getElementById('runSummary');
  const nameEl = document.getElementById('playerName');
  const submitBtn = document.getElementById('submitScoreBtn');
  const messageEl = document.getElementById('scoreMessage');
  const monthEl = document.getElementById('leaderboardMonth');
  const listEl = document.getElementById('leaderboardList');

  const colors = ['#8df7c5', '#ff789f', '#ffd36f', '#8cecff', '#c59cff'];
  let phase = 'idle';
  let lastFrame = 0;
  let round = 1;
  let score = 0;
  let lives = 3;
  let elapsed = 0;
  let roundTime = 42;
  let runStartedAt = 0;
  let lastRun = null;
  let distance = 0;
  let spawnClock = 0;
  let sceneryClock = 0;
  let runnerLane = 1;
  let targetLane = 1;
  let jumpY = 0;
  let jumpVelocity = 0;
  let hurtCooldown = 0;
  let objects = [];
  let particles = [];
  let ai = [];
  let inputLock = false;

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[character]));

  function reset() {
    phase = 'idle'; round = 1; score = 0; lives = 3; elapsed = 0; roundTime = 42;
    lastRun = null; distance = 0; spawnClock = 0; sceneryClock = 0; runnerLane = 1;
    targetLane = 1; jumpY = 0; jumpVelocity = 0; objects = []; particles = [];
    hurtCooldown = 0;
    ai = makeRivals(10); messageEl.textContent = '';
  }

  function makeRivals(count) {
    return Array.from({ length: count }, (_, index) => ({
      lane: index % 3, z: 0.18 + index * 0.07, color: colors[(index + 1) % colors.length],
      wobble: Math.random() * Math.PI * 2, pace: 0.8 + Math.random() * 0.35
    }));
  }

  function start() {
    reset(); phase = 'race'; runStartedAt = Date.now();
    startOverlay.classList.add('hidden'); endOverlay.classList.add('hidden');
    roundOverlay.classList.add('hidden'); canvas.focus(); lastFrame = performance.now();
    requestAnimationFrame(loop);
  }

  function moveLane(direction) {
    if (phase !== 'race') return;
    targetLane = clamp(targetLane + direction, 0, 2);
    burst(laneX(targetLane), 520, '#8cecff', 4);
  }

  function jump() {
    if (phase === 'race' && jumpY <= 1) {
      jumpVelocity = 760; burst(laneX(targetLane), 535, '#ffd36f', 8);
    }
  }

  function laneX(lane) { return 440 + lane * 160; }
  function currentSpeed() { return 0.29 + round * 0.045 + Math.min(0.16, elapsed * 0.0022); }

  function spawnObject() {
    const lane = Math.floor(Math.random() * 3);
    const dangerous = Math.random() < 0.56;
    const type = dangerous ? (Math.random() < 0.5 ? 'gate' : 'bumper') : (Math.random() < 0.5 ? 'token' : 'spring');
    objects.push({ type, lane, z: 1.16, spin: Math.random() * Math.PI * 2, hit: false });
    if (type === 'gate' && Math.random() < 0.55) {
      const safeLane = (lane + (Math.random() < 0.5 ? 1 : 2)) % 3;
      objects.push({ type: 'token', lane: safeLane, z: 1.33, spin: 0, hit: false });
    }
  }

  function finish(won, reason) {
    phase = 'over';
    lastRun = { score: Math.max(1, Math.floor(score)), wave: round, duration: Math.max(10, Math.floor((Date.now() - runStartedAt) / 1000)) };
    scoreEl.textContent = lastRun.score.toLocaleString();
    summaryEl.textContent = `${reason} · ${lives} LIVES LEFT · ROUND ${round}`;
    document.getElementById('endTitle').textContent = won ? 'CHAMPION' : 'ELIMINATED';
    endOverlay.classList.remove('hidden'); loadBoard();
  }

  function clearRound() {
    phase = 'between'; score += 500 * round;
    roundEyebrow.textContent = `ROUND ${round} CLEARED`;
    roundTitle.textContent = 'YOU QUALIFIED.';
    roundCopy.textContent = 'The track is moving faster. The final round adds double obstacles.';
    roundOverlay.classList.remove('hidden');
  }

  function nextRound() {
    round += 1; roundTime = Math.max(28, 42 - round * 5); elapsed = 0; distance = 0;
    spawnClock = 0; objects = []; ai = makeRivals(Math.max(3, 11 - round * 3));
    runnerLane = 1; targetLane = 1; jumpY = 0; jumpVelocity = 0;
    hurtCooldown = 0;
    roundOverlay.classList.add('hidden'); phase = 'race'; lastFrame = performance.now();
    requestAnimationFrame(loop);
  }

  function loseLife() {
    if (hurtCooldown > 0) return;
    lives -= 1; burst(laneX(runnerLane), 470 - jumpY, '#ff668e', 18);
    hurtCooldown = 1.35;
    if (lives <= 0) finish(false, 'OUT OF LIVES');
  }

  function burst(x, y, color, count = 12) {
    for (let index = 0; index < count; index += 1) {
      particles.push({ x, y, vx: (Math.random() - 0.5) * 180, vy: (Math.random() - 0.75) * 190, life: 0.45 + Math.random() * 0.6, color });
    }
  }

  function update(dt) {
    if (phase !== 'race') return;
    elapsed += dt; roundTime -= dt; distance += currentSpeed() * dt;
    hurtCooldown = Math.max(0, hurtCooldown - dt);
    sceneryClock += dt * currentSpeed() * 9; spawnClock -= dt;
    if (spawnClock <= 0) {
      spawnObject(); spawnClock = Math.max(0.5, 0.92 - round * 0.1 - elapsed * 0.003);
    }
    runnerLane += (targetLane - runnerLane) * Math.min(1, dt * 12);
    if (jumpY > 0 || jumpVelocity > 0) {
      jumpY += jumpVelocity * dt; jumpVelocity -= 1850 * dt;
      if (jumpY <= 0) { jumpY = 0; jumpVelocity = 0; }
    }
    for (const item of objects) {
      item.z -= currentSpeed() * dt; item.spin += dt * 4;
      if (!item.hit && item.z < 0.13 && item.z > -0.03 && Math.abs(item.lane - Math.round(runnerLane)) === 0) {
        item.hit = true;
        if (item.type === 'token') { score += 120; burst(laneX(item.lane), 440, '#ffd36f', 16); }
        else if (item.type === 'spring') { jumpVelocity = 980; score += 60; burst(laneX(item.lane), 500, '#8cecff', 12); }
        else if (jumpY < 58) { loseLife(); item.z = -0.2; }
        else { score += 55; burst(laneX(item.lane), 440, '#8df7c5', 10); }
      }
    }
    objects = objects.filter(item => item.z > -0.25);
    for (const rival of ai) { rival.z -= currentSpeed() * dt * rival.pace; rival.wobble += dt * 8; if (rival.z < -0.15) rival.z = 0.5 + Math.random() * 0.8; }
    for (let index = particles.length - 1; index >= 0; index -= 1) {
      const particle = particles[index]; particle.x += particle.vx * dt; particle.y += particle.vy * dt; particle.vy += 240 * dt; particle.life -= dt;
      if (particle.life <= 0) particles.splice(index, 1);
    }
    if (roundTime <= 0) { if (round >= 3) finish(true, 'FINAL ROUND WINNER'); else clearRound(); }
  }

  function drawBackground() {
    const gradient = ctx.createLinearGradient(0, 0, 0, H);
    gradient.addColorStop(0, '#0b5f73'); gradient.addColorStop(0.58, '#123b58'); gradient.addColorStop(1, '#081728');
    ctx.fillStyle = gradient; ctx.fillRect(0, 0, W, H);
    if (courseImage.complete && courseImage.naturalWidth) { ctx.save(); ctx.globalAlpha = 0.38; ctx.drawImage(courseImage, 0, 34, W, 430); ctx.restore(); }
    ctx.fillStyle = 'rgba(5, 14, 30, .42)'; ctx.fillRect(0, 0, W, 250);
    ctx.fillStyle = '#9ef8ff';
    for (let index = 0; index < 18; index += 1) {
      const x = (index * 91 + sceneryClock * 28) % (W + 80) - 40; const y = 92 + (index % 4) * 28;
      ctx.globalAlpha = 0.25 + (index % 3) * 0.12; ctx.fillRect(x, y, 6, 6);
    }
    ctx.globalAlpha = 1;
  }

  function trackPoint(z) {
    const depth = clamp(z, 0, 1.15); const perspective = Math.pow(1 - depth / 1.15, 1.18);
    return { y: 154 + perspective * 360, width: 175 + perspective * 610, laneGap: 62 + perspective * 98 };
  }

  function drawTrack() {
    const horizon = trackPoint(1.15); const near = trackPoint(0);
    ctx.fillStyle = '#073045'; ctx.beginPath();
    ctx.moveTo(W / 2 - horizon.width / 2, horizon.y); ctx.lineTo(W / 2 + horizon.width / 2, horizon.y);
    ctx.lineTo(W / 2 + near.width / 2, near.y + 60); ctx.lineTo(W / 2 - near.width / 2, near.y + 60); ctx.closePath(); ctx.fill();
    for (let index = 0; index < 14; index += 1) {
      const z = ((index / 14) + sceneryClock * 0.42) % 1.15; const point = trackPoint(z); const next = trackPoint(Math.min(1.15, z + 0.045));
      ctx.fillStyle = index % 2 ? 'rgba(32, 111, 120, .92)' : 'rgba(18, 79, 100, .92)'; ctx.beginPath();
      ctx.moveTo(W / 2 - point.width / 2, point.y); ctx.lineTo(W / 2 + point.width / 2, point.y);
      ctx.lineTo(W / 2 + next.width / 2, next.y); ctx.lineTo(W / 2 - next.width / 2, next.y); ctx.closePath(); ctx.fill();
    }
    for (const offset of [-1, 1]) {
      ctx.strokeStyle = 'rgba(255, 211, 111, .72)'; ctx.lineWidth = 4; ctx.beginPath();
      ctx.moveTo(W / 2 + offset * horizon.laneGap / 2, horizon.y); ctx.lineTo(W / 2 + offset * near.laneGap * 1.55, near.y + 60); ctx.stroke();
    }
  }

  function drawRival(rival) {
    if (rival.z < 0 || rival.z > 1.2) return;
    const point = trackPoint(rival.z); const size = 18 + (1 - rival.z / 1.2) * 32; const x = W / 2 + (rival.lane - 1) * point.laneGap; const y = point.y - size + Math.sin(rival.wobble) * 3;
    ctx.save(); ctx.fillStyle = rival.color; ctx.shadowColor = rival.color; ctx.shadowBlur = 12; ctx.beginPath(); ctx.ellipse(x, y, size * 0.68, size, 0, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0; ctx.fillStyle = '#101a35'; ctx.fillRect(x - size * 0.34, y - size * 0.2, size * 0.68, size * 0.23); ctx.restore();
  }

  function drawObject(item) {
    if (item.z < 0 || item.z > 1.2) return;
    const point = trackPoint(item.z); const x = W / 2 + (item.lane - 1) * point.laneGap; const scale = 0.28 + (1 - item.z / 1.2) * 1.05; const y = point.y - 12 * scale;
    ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale);
    if (item.type === 'token') {
      ctx.rotate(item.spin); ctx.fillStyle = '#ffd36f'; ctx.shadowColor = '#ffd36f'; ctx.shadowBlur = 24; ctx.fillRect(-18, -18, 36, 36);
      ctx.rotate(-item.spin); ctx.fillStyle = '#7d4c19'; ctx.font = '900 26px system-ui'; ctx.textAlign = 'center'; ctx.fillText('%', 0, 9);
    } else if (item.type === 'spring') {
      ctx.fillStyle = '#18b9bf'; ctx.fillRect(-37, -12, 74, 24); ctx.fillStyle = '#ffd36f'; ctx.fillRect(-31, -7, 62, 8);
      ctx.strokeStyle = '#eefcff'; ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(0, 12, 25, Math.PI, Math.PI * 2); ctx.stroke();
    } else if (item.type === 'gate') {
      ctx.fillStyle = '#ef5d63'; ctx.fillRect(-10, -52, 20, 104); ctx.save(); ctx.rotate(item.spin); ctx.fillStyle = '#f7fbf5'; ctx.fillRect(-76, -11, 152, 22); ctx.fillStyle = '#ef5d63';
      for (let index = -3; index < 4; index += 2) ctx.fillRect(index * 22, -11, 22, 22); ctx.restore();
    } else {
      ctx.fillStyle = '#ff8b39'; ctx.beginPath(); ctx.roundRect(-29, -44, 58, 88, 18); ctx.fill(); ctx.fillStyle = '#ffd36f'; ctx.beginPath(); ctx.arc(0, -26, 8, 0, Math.PI * 2); ctx.fill();
    }
    ctx.restore();
  }

  function drawRunner() {
    const x = laneX(runnerLane); const bob = Math.sin(elapsed * 15) * 5; const tilt = Math.sin(elapsed * 15) * 0.035; const y = 535 - jumpY + bob;
    ctx.save(); ctx.translate(x, y); ctx.rotate(tilt); ctx.globalAlpha = 0.25; ctx.fillStyle = '#000'; ctx.beginPath(); ctx.ellipse(0, 8 + jumpY * 0.06, 62, 13, 0, 0, Math.PI * 2); ctx.fill(); ctx.globalAlpha = 1;
    if (runnerImage.complete && runnerImage.naturalWidth) ctx.drawImage(runnerImage, -78, -155, 156, 156);
    else { ctx.fillStyle = '#8df7c5'; ctx.beginPath(); ctx.ellipse(0, -75, 55, 76, 0, 0, Math.PI * 2); ctx.fill(); }
    ctx.restore();
  }

  function drawParticles() {
    for (const particle of particles) { ctx.globalAlpha = Math.max(0, particle.life); ctx.fillStyle = particle.color; ctx.fillRect(particle.x - 2, particle.y - 2, 6, 6); }
    ctx.globalAlpha = 1;
  }

  function draw() {
    drawBackground(); drawTrack(); for (const rival of ai) drawRival(rival); for (const item of objects) drawObject(item); drawRunner(); drawParticles();
    ctx.fillStyle = '#f8fbff'; ctx.font = '900 22px system-ui'; ctx.fillText('DEAL DASH ROYALE', 34, 40);
    ctx.font = '800 13px system-ui'; ctx.fillStyle = '#ffd36f'; ctx.fillText(`ROUND ${round}/3`, 38, 68);
    ctx.fillStyle = '#8df7c5'; ctx.fillText(`LANE ${laneNames[Math.round(runnerLane)]}`, 145, 68);
    ctx.fillStyle = '#cce8ee'; ctx.fillText(`SCORE ${Math.floor(score).toLocaleString()}`, 280, 68);
    ctx.fillStyle = '#ff9eae'; ctx.fillText(`LIVES ${'♥'.repeat(lives)}${'♡'.repeat(3 - lives)}`, W - 150, 42);
    ctx.fillStyle = '#cce8ee'; ctx.font = '700 12px system-ui'; ctx.fillText(`${Math.max(0, Math.ceil(roundTime))}s · A/D lane shift · SPACE jump`, W - 330, 68);
  }

  function loop(now) {
    if (phase === 'idle' || phase === 'over' || phase === 'between') return;
    const dt = Math.min(0.033, (now - lastFrame) / 1000); lastFrame = now; update(dt); draw();
    if (phase === 'race') requestAnimationFrame(loop);
  }

  window.addEventListener('keydown', event => {
    if (['ArrowLeft', 'a', 'A'].includes(event.key)) { event.preventDefault(); if (!inputLock) moveLane(-1); inputLock = true; }
    else if (['ArrowRight', 'd', 'D'].includes(event.key)) { event.preventDefault(); if (!inputLock) moveLane(1); inputLock = true; }
    else if (['ArrowUp', ' ', 'w', 'W'].includes(event.key)) { event.preventDefault(); jump(); }
  });
  window.addEventListener('keyup', event => { if (['ArrowLeft', 'ArrowRight', 'a', 'A', 'd', 'D'].includes(event.key)) inputLock = false; });
  canvas.addEventListener('pointerdown', jump); startBtn.addEventListener('click', start); nextBtn.addEventListener('click', nextRound); restartBtn.addEventListener('click', start);

  submitBtn.addEventListener('click', async () => {
    const name = nameEl.value.trim();
    if (name.length < 2) { messageEl.textContent = 'Enter at least 2 characters.'; return; }
    submitBtn.disabled = true; messageEl.textContent = 'Submitting…';
    try {
      const response = await fetch('/api/score', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ game: 'deal-dash-royale', name, ...lastRun }) });
      const data = await response.json(); messageEl.textContent = data.message || data.error || 'Done.'; loadBoard();
    } catch { messageEl.textContent = 'Could not submit right now.'; } finally { submitBtn.disabled = false; }
  });

  async function loadBoard() {
    try {
      const response = await fetch('/api/leaderboard?game=deal-dash-royale'); const data = await response.json(); monthEl.textContent = data.month || 'Current month'; listEl.replaceChildren();
      if (!data.scores.length) { const empty = document.createElement('li'); empty.textContent = 'No finalists yet — be the first to qualify.'; listEl.appendChild(empty); return; }
      data.scores.forEach((entry, index) => { const item = document.createElement('li'); item.innerHTML = `<span class="rank">${String(index + 1).padStart(2, '0')}</span><span>${escapeHtml(entry.player_name)}</span><strong>${Number(entry.score).toLocaleString()}</strong><small>ROUND ${entry.wave}</small>`; listEl.appendChild(item); });
    } catch { monthEl.textContent = 'Offline'; }
  }

  reset(); draw(); loadBoard();
})();
