(() => {
  const el = id => document.getElementById(id);
  const MAX_LEVEL = 1000;
  const COLORS = ['red','orange','yellow','green','blue','purple','cyan','pink'];
  let level = readNumber('bubble-crush-level', 1);
  let config = null, board = [], frozen = [], moves = 0, score = 0, cleared = 0, started = 0, elapsed = 0, solved = false, selected = -1;

  function readNumber(key, fallback) {
    try { const value = Number(localStorage.getItem(key)); return Number.isFinite(value) && value > 0 ? value : fallback; } catch { return fallback; }
  }
  function save(key, value) { try { localStorage.setItem(key, String(value)); } catch {} }
  function clock(seconds) { return Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0'); }
  function levelConfig(number) {
    const size = number <= 20 ? 7 : number <= 150 ? 8 : number <= 500 ? 9 : 10;
    const colors = Math.min(8, 4 + Math.floor((number - 1) / 140));
    const moves = Math.max(16, 30 - Math.floor((number - 1) / 72));
    const cells = size * size;
    const target = Math.min(Math.floor(cells * .72), Math.round(cells * (.24 + Math.min(.32, number / 3200))));
    const frozenCount = number < 45 ? 0 : Math.min(Math.floor(cells * .18), Math.floor((number - 35) / 22));
    return {size, colors, moves, target, frozenCount};
  }
  function randomColor() { return Math.floor(Math.random() * config.colors); }
  function neighbors(index) {
    const row = Math.floor(index / config.size), col = index % config.size, result = [];
    if (row) result.push(index - config.size); if (row < config.size - 1) result.push(index + config.size);
    if (col) result.push(index - 1); if (col < config.size - 1) result.push(index + 1);
    return result;
  }
  function groupAt(index) {
    if (board[index] === null || board[index] === undefined) return [];
    const color = board[index], group = [], queue = [index], seen = new Set([index]);
    while (queue.length) {
      const current = queue.shift(); group.push(current);
      neighbors(current).forEach(next => { if (!seen.has(next) && board[next] === color) { seen.add(next); queue.push(next); } });
    }
    return group;
  }
  function hasMove() { return board.some((value, index) => value !== null && groupAt(index).length >= 2); }
  function makeBoard() {
    const cells = config.size * config.size;
    board = Array.from({length: cells}, randomColor);
    frozen = Array(cells).fill(0);
    const positions = Array.from({length: cells}, (_, i) => i).sort(() => Math.random() - .5);
    positions.slice(0, config.frozenCount).forEach(index => { frozen[index] = 2; });
    let guard = 0; while (!hasMove() && guard++ < 20) board = Array.from({length: cells}, randomColor);
  }
  function render() {
    const boardEl = el('board'); boardEl.style.setProperty('--size', config.size); boardEl.replaceChildren();
    board.forEach((color, index) => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'bubble ' + (COLORS[color] || 'blue') + (frozen[index] ? ' frozen' : '');
      button.dataset.index = index; button.setAttribute('role', 'gridcell'); button.setAttribute('aria-label', (COLORS[color] || 'bubble') + ' bubble' + (frozen[index] ? ', frozen' : ''));
      button.addEventListener('click', () => choose(index)); boardEl.appendChild(button);
    });
    el('level').textContent = level + ' / ' + MAX_LEVEL; el('moves').textContent = moves; el('score').textContent = score.toLocaleString(); el('goal').textContent = Math.min(cleared, config.target) + ' / ' + config.target;
    el('levelProgress').style.width = Math.max(.1, level / MAX_LEVEL * 100) + '%';
    el('timer').textContent = clock(elapsed);
  }
  function choose(index) {
    if (solved || moves <= 0 || board[index] === null) return;
    const group = groupAt(index);
    if (group.length < 2) { selected = index; renderSelection(); el('message').textContent = 'That bubble needs a neighbor. Find a connected color group.'; return; }
    if (!started) started = Date.now();
    selected = -1; moves--; const bonus = group.length >= 7 ? 180 : group.length >= 5 ? 90 : group.length >= 4 ? 35 : 0;
    let removed = 0;
    group.forEach(cell => { if (frozen[cell]) frozen[cell]--; else { board[cell] = null; removed++; } });
    cleared += removed; score += removed * removed * 10 + bonus + (removed >= 4 ? removed * 5 : 0);
    collapse();
    if (cleared >= config.target) finish(true);
    else if (moves <= 0) finish(false);
    else if (!hasMove()) { score += 25; makeBoard(); el('message').textContent = 'No moves left on the board — reshuffled! +25'; }
    render();
  }
  function renderSelection() { Array.from(el('board').children).forEach((node, i) => node.classList.toggle('selected', i === selected)); }
  function collapse() {
    for (let col = 0; col < config.size; col++) {
      const kept = [];
      for (let row = config.size - 1; row >= 0; row--) { const index = row * config.size + col; if (board[index] !== null) kept.push({color: board[index], ice: frozen[index]}); }
      while (kept.length < config.size) kept.push({color: randomColor(), ice: 0});
      for (let row = config.size - 1; row >= 0; row--) { const item = kept[config.size - 1 - row]; const index = row * config.size + col; board[index] = item.color; frozen[index] = item.ice; }
    }
  }
  function finish(won) {
    solved = true; elapsed = Math.floor((Date.now() - started) / 1000);
    if (won) {
      const bestKey = 'bubble-crush-best-' + level, old = readBest(bestKey);
      if (!old || score > old.score || (score === old.score && moves > old.moves)) save(bestKey, JSON.stringify({score, moves, seconds: elapsed}));
      if (level < MAX_LEVEL) save('bubble-crush-level', level + 1);
      el('message').textContent = level === MAX_LEVEL ? 'Campaign complete! You crushed all 1,000 levels.' : 'Level cleared! ' + Math.max(0, moves) + ' moves left · ' + clock(elapsed) + '.';
      el('next').hidden = level >= MAX_LEVEL;
    } else el('message').textContent = 'Out of moves. You cleared ' + cleared + ' bubbles — try again.';
    bestText();
  }
  function readBest(key) { try { return JSON.parse(localStorage.getItem(key)); } catch { return null; } }
  function bestText() {
    const best = readBest('bubble-crush-best-' + level);
    el('best').textContent = best ? 'Level ' + level + ' best: ' + best.score.toLocaleString() + ' points · ' + best.moves + ' moves left' : 'Level ' + level + ' · ' + config.colors + ' colors · ' + (config.frozenCount ? config.frozenCount + ' frozen bubbles' : 'no frozen bubbles yet');
  }
  function start() {
    config = levelConfig(level); moves = config.moves; score = 0; cleared = 0; started = 0; elapsed = 0; solved = false; selected = -1; makeBoard(); el('next').hidden = true;
    el('message').textContent = 'Level ' + level + ' · Clear ' + config.target + ' bubbles in ' + config.moves + ' moves.';
    el('instruction').textContent = level < 45 ? 'Clear groups of two or more matching bubbles. Bigger groups create bigger combos.' : 'Frozen bubbles take two hits. ' + config.colors + ' colors are in play — plan your chain carefully.';
    render(); bestText();
  }
  el('next').addEventListener('click', () => { if (level < MAX_LEVEL) { level++; start(); } });
  el('restart').addEventListener('click', start);
  el('reset').addEventListener('click', () => { level = 1; save('bubble-crush-level', 1); start(); });
  setInterval(() => { if (started && !solved) elapsed = Math.floor((Date.now() - started) / 1000); el('timer').textContent = clock(elapsed); }, 250);
  start();
})();
