(() => {
  const GAME = 'deal-dash';
  const arena = document.getElementById('arena');
  const intro = document.getElementById('intro');
  const end = document.getElementById('end');
  const startBtn = document.getElementById('startBtn');
  const restartBtn = document.getElementById('restartBtn');
  const scoreEl = document.getElementById('score');
  const streakEl = document.getElementById('streak');
  const timeEl = document.getElementById('time');
  const levelEl = document.getElementById('level');
  const livesEl = document.getElementById('lives');
  const finalScore = document.getElementById('finalScore');
  const playerName = document.getElementById('playerName');
  const submitScoreBtn = document.getElementById('submitScoreBtn');
  const scoreMessage = document.getElementById('scoreMessage');
  const leaderboardList = document.getElementById('leaderboardList');
  const leaderboardMonth = document.getElementById('leaderboardMonth');
  const products = [['Kitchen deal', '$29.90', 'deal'], ['Home refresh', '$14.00', 'deal'], ['Tech markdown', '$39.99', 'deal'], ['Pet savings', '$11.50', 'deal'], ['Grocery grab', '$6.99', 'deal'], ['Full price', '$89.99', 'trap'], ['No coupon', '$72.00', 'trap'], ['Budget trap', '$120.00', 'trap']];
  let running = false, score = 0, streak = 0, lives = 3, level = 1, seconds = 30, startedAt = 0, clock = null, spawner = null, lastRun = null;

  function updateHud() { scoreEl.textContent = score.toLocaleString(); streakEl.textContent = streak; timeEl.textContent = seconds; levelEl.textContent = level; livesEl.textContent = lives; }
  function clearCards() { arena.querySelectorAll('.dash-card').forEach(card => card.remove()); }
  function spawnCard() {
    if (!running) return;
    const item = products[Math.floor(Math.random() * products.length)];
    const card = document.createElement('button'); card.type = 'button'; card.className = `dash-card ${item[2]}`;
    card.innerHTML = `<small>${item[2] === 'deal' ? 'VERIFIED SAVING' : 'CHECK THE PRICE'}</small><strong>${item[0]}</strong><span>${item[1]}</span>`;
    card.style.left = `${12 + Math.random() * Math.max(1, arena.clientWidth - 155)}px`; card.style.top = `${12 + Math.random() * Math.max(1, arena.clientHeight - 145)}px`;
    card.addEventListener('click', () => { if (!running) return; card.remove(); if (item[2] === 'deal') { streak += 1; score += 10 * level + Math.min(streak, 10) * 2; } else { lives -= 1; streak = 0; score = Math.max(0, score - 12 * level); if (lives <= 0) finish(); } updateHud(); });
    arena.appendChild(card); window.setTimeout(() => card.remove(), Math.max(850, 2400 - level * 150));
  }
  function scheduleSpawn() { if (!running) return; spawnCard(); spawner = window.setTimeout(scheduleSpawn, Math.max(300, 900 - level * 65)); }
  function start() { clearCards(); running = true; score = 0; streak = 0; lives = 3; level = 1; seconds = 30; startedAt = Date.now(); lastRun = null; intro.classList.add('hidden'); end.classList.add('hidden'); scoreMessage.textContent = ''; updateHud(); arena.focus(); scheduleSpawn(); clock = window.setInterval(() => { seconds -= 1; level = Math.min(9, 1 + Math.floor((30 - seconds) / 5)); updateHud(); if (seconds <= 0) finish(); }, 1000); }
  function finish() { if (!running) return; running = false; window.clearInterval(clock); window.clearTimeout(spawner); clearCards(); lastRun = {game: GAME, score, wave: level, duration: Math.max(10, Math.round((Date.now() - startedAt) / 1000))}; finalScore.textContent = score.toLocaleString(); end.classList.remove('hidden'); }
  function escapeHtml(value) { const div = document.createElement('div'); div.textContent = value; return div.innerHTML; }
  async function loadLeaderboard() { try { const response = await fetch(`/api/leaderboard?game=${GAME}`, {headers: {Accept: 'application/json'}}); const data = await response.json(); leaderboardMonth.textContent = data.month || 'Current month'; leaderboardList.replaceChildren(); if (!data.scores.length) { const li = document.createElement('li'); li.textContent = 'No runs yet — take the first dash.'; leaderboardList.appendChild(li); return; } data.scores.forEach((entry, index) => { const li = document.createElement('li'); li.innerHTML = `<span class="rank">${String(index + 1).padStart(2, '0')}</span><span>${escapeHtml(entry.player_name)}</span><strong>${Number(entry.score).toLocaleString()}</strong><small>LEVEL ${entry.wave}</small>`; leaderboardList.appendChild(li); }); } catch { leaderboardMonth.textContent = 'Offline'; } }
  async function submitScore() { if (!lastRun) return; const name = (playerName.value || '').trim(); if (name.length < 2) { scoreMessage.textContent = 'Enter at least 2 characters.'; return; } submitScoreBtn.disabled = true; scoreMessage.textContent = 'Submitting…'; try { const response = await fetch('/api/score', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name, ...lastRun})}); const data = await response.json(); scoreMessage.textContent = data.message || data.error || 'Done.'; if (response.ok) { try { localStorage.setItem('dealDashName', name); } catch {} loadLeaderboard(); } } catch { scoreMessage.textContent = 'Could not submit right now.'; } submitScoreBtn.disabled = false; }
  try { playerName.value = localStorage.getItem('dealDashName') || ''; } catch {}
  startBtn.addEventListener('click', start); restartBtn.addEventListener('click', start); submitScoreBtn.addEventListener('click', submitScore); loadLeaderboard(); updateHud();
})();
