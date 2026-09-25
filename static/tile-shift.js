(() => {
  const el = id => document.getElementById(id);
  const MAX_LEVEL = 1000;
  const COLORS = ['red','orange','yellow','green','blue','purple','cyan','pink'];
  const supportsPointerEvents = 'PointerEvent' in window;
  let level = readNumber('bubble-crush-level', 1);
  let config = null, board = [], frozen = [], moves = 0, score = 0, cleared = 0, started = 0, elapsed = 0, solved = false, selected = -1, animating = false, pointerStart = null, pointerTapHandled = false;

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
  function findMatches() {
    const found = new Set(), size = config.size;
    const scanLine = indexes => {
      let run = [];
      const addRun = () => { if (run.length >= 3) run.forEach(index => found.add(index)); };
      indexes.forEach(index => {
        const playable = board[index] !== null && !frozen[index];
        if (playable && (run.length === 0 || board[index] === board[run[0]])) run.push(index);
        else { addRun(); run = playable ? [index] : []; }
      });
      addRun();
    };
    for (let row = 0; row < size; row++) scanLine(Array.from({length: size}, (_, col) => row * size + col));
    for (let col = 0; col < size; col++) scanLine(Array.from({length: size}, (_, row) => row * size + col));
    return Array.from(found);
  }
  function swap(a, b) { const color = board[a]; board[a] = board[b]; board[b] = color; const ice = frozen[a]; frozen[a] = frozen[b]; frozen[b] = ice; }
  function hasValidSwap() {
    for (let index = 0; index < board.length; index++) {
      for (const next of neighbors(index)) {
        if (next <= index || board[index] === null || board[next] === null) continue;
        swap(index, next); const valid = findMatches().length > 0; swap(index, next);
        if (valid) return true;
      }
    }
    return false;
  }
  function makeBoard() {
    const cells = config.size * config.size;
    for (let attempts = 0; attempts < 10000; attempts++) {
      board = Array.from({length: cells}, randomColor); frozen = Array(cells).fill(0);
      const positions = Array.from({length: cells}, (_, i) => i).sort(() => Math.random() - .5);
      positions.slice(0, config.frozenCount).forEach(index => { frozen[index] = 2; });
      if (!findMatches().length && hasValidSwap()) return;
    }
    board = Array.from({length: cells}, (_, index) => (Math.floor(index / config.size) * 2 + index) % config.colors);
    frozen = Array(cells).fill(0);
  }
  function shufflePlayableBoard() {
    const colors = board.filter(color => color !== null).sort(() => Math.random() - .5);
    for (let attempts = 0; attempts < 10000; attempts++) {
      board = Array.from({length: config.size * config.size}, (_, index) => colors[index % colors.length]);
      board.sort(() => Math.random() - .5);
      if (!findMatches().length && hasValidSwap()) return;
    }
    makeBoard();
  }
  function beginGesture(index, event) {
    if (solved || animating || moves <= 0) return;
    if (selected >= 0) {
      pointerStart = null;
      pointerTapHandled = true;
      void choose(index);
      return;
    }
    pointerTapHandled = false;
    pointerStart = {index, x: event.clientX, y: event.clientY};
    if (event.pointerId != null && event.currentTarget?.setPointerCapture) event.currentTarget.setPointerCapture(event.pointerId);
  }
  function trackGesture(event) {
    if (pointerStart && Math.max(Math.abs(event.clientX - pointerStart.x), Math.abs(event.clientY - pointerStart.y)) >= 18) finishSwipe(event);
  }
  function render(animate = false) {
    const boardEl = el('board'); boardEl.style.setProperty('--size', config.size); boardEl.replaceChildren();
    if (supportsPointerEvents) {
      boardEl.onpointermove = trackGesture;
      boardEl.onpointerup = finishSwipe;
      boardEl.onpointercancel = () => { pointerStart = null; };
    } else {
      boardEl.onmousemove = trackGesture;
      boardEl.onmouseup = finishSwipe;
      boardEl.ontouchmove = event => { const touch = event.changedTouches[0]; if (touch) trackGesture(touch); };
      boardEl.ontouchend = event => { const touch = event.changedTouches[0]; if (touch) finishSwipe(touch); };
      boardEl.ontouchcancel = () => { pointerStart = null; };
    }
    board.forEach((color, index) => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'bubble ' + (COLORS[color] || 'blue') + (frozen[index] ? ' frozen' : '') + (selected === index ? ' selected' : '') + (animate ? ' drop-in' : '');
      button.dataset.index = index; button.setAttribute('role', 'gridcell'); button.setAttribute('aria-label', (COLORS[color] || 'bubble') + ' bubble' + (frozen[index] ? ', frozen' : '') + (selected === index ? ', selected' : ''));
      if (supportsPointerEvents) {
        button.addEventListener('click', () => {
          if (pointerTapHandled) { pointerTapHandled = false; return; }
          void choose(index);
        });
        button.addEventListener('pointerdown', event => { if (event.pointerType === 'mouse' && event.button !== 0) return; beginGesture(index, event); });
      } else {
        button.addEventListener('click', () => { void choose(index); });
        button.addEventListener('mousedown', event => { if (event.button === 0) beginGesture(index, event); });
        button.addEventListener('touchstart', event => { const touch = event.changedTouches[0]; if (touch) beginGesture(index, touch); }, {passive: true});
      }
      boardEl.appendChild(button);
    });
    el('level').textContent = level + ' / ' + MAX_LEVEL; el('moves').textContent = moves; el('score').textContent = score.toLocaleString(); el('goal').textContent = Math.min(cleared, config.target) + ' / ' + config.target;
    el('levelProgress').style.width = Math.max(.1, level / MAX_LEVEL * 100) + '%'; el('timer').textContent = clock(elapsed);
  }
  function finishSwipe(event) {
    if (!pointerStart) return;
    const start = pointerStart; pointerStart = null;
    const dx = event.clientX - start.x, dy = event.clientY - start.y;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < 18) return;
    event.preventDefault();
    const target = swipeDestination(start.index, dx, dy);
    if (target < 0) { selected = -1; el('message').textContent = 'Swipe one space toward the board.'; render(); return; }
    selected = start.index; render(); void choose(target);
  }
  function swipeDestination(index, dx, dy) {
    const row = Math.floor(index / config.size), col = index % config.size;
    if (Math.abs(dx) >= Math.abs(dy)) return dx > 0 ? (col < config.size - 1 ? index + 1 : -1) : (col > 0 ? index - 1 : -1);
    return dy > 0 ? (row < config.size - 1 ? index + config.size : -1) : (row > 0 ? index - config.size : -1);
  }
  async function choose(index) {
    if (solved || animating || moves <= 0) return;
    if (selected < 0) { selected = index; el('message').textContent = 'Now choose an adjacent bubble to swap.'; render(); return; }
    if (selected === index) { selected = -1; el('message').textContent = 'Select a bubble to begin a swap.'; render(); return; }
    if (!neighbors(selected).includes(index)) { selected = index; el('message').textContent = 'That bubble is too far away. Choose a neighbor.'; render(); return; }
    const first = selected; selected = -1; swap(first, index);
    if (!findMatches().length) { swap(first, index); el('message').textContent = 'That swap does not make three. Try another move.'; render(); return; }
    if (!started) started = Date.now(); moves--; animating = true; await resolveCascades(); animating = false; selected = -1;
    if (cleared >= config.target) finish(true); else if (moves <= 0) finish(false);
    else if (!hasValidSwap()) { shufflePlayableBoard(); el('message').textContent = 'No matches available — the board was reshuffled.'; }
    render();
  }
  async function resolveCascades() {
    selected = -1;
    let combo = 0, matches = findMatches();
    while (matches.length && combo < 50) {
      combo++; matches.forEach(index => el('board').children[index]?.classList.add('matched'));
      await new Promise(resolve => setTimeout(resolve, 260));
      matches.forEach(index => { board[index] = null; cleared++; neighbors(index).forEach(next => { if (frozen[next]) frozen[next]--; }); });
      score += matches.length * matches.length * 10 + combo * 35 + (matches.length >= 4 ? matches.length * 10 : 0);
      collapse(); render(true); await new Promise(resolve => setTimeout(resolve, 220)); matches = findMatches();
    }
    if (combo > 1) el('message').textContent = 'Cascade x' + combo + '! Keep it going.';
    else el('message').textContent = 'Match cleared. Find your next three.';
  }
  function refillColor(row, col) {
    const size = config.size;
    const leftOne = col > 0 ? board[row * size + col - 1] : null;
    const leftTwo = col > 1 ? board[row * size + col - 2] : null;
    const belowOne = row < size - 1 ? board[(row + 1) * size + col] : null;
    const belowTwo = row < size - 2 ? board[(row + 2) * size + col] : null;
    const candidates = Array.from({length: config.colors}, (_, color) => color).filter(color => {
      const makesRow = color === leftOne && color === leftTwo;
      const makesColumn = color === belowOne && color === belowTwo;
      return !makesRow && !makesColumn;
    });
    return candidates.length ? candidates[Math.floor(Math.random() * candidates.length)] : randomColor();
  }
  function collapse() {
    for (let col = 0; col < config.size; col++) {
      const kept = [];
      for (let row = config.size - 1; row >= 0; row--) { const index = row * config.size + col; if (board[index] !== null) kept.push({color: board[index], ice: frozen[index]}); }
      for (let row = config.size - 1; row >= 0; row--) { const item = kept[config.size - 1 - row]; const index = row * config.size + col; board[index] = item.color; frozen[index] = item.ice; }
      for (let row = config.size - kept.length - 1; row >= 0; row--) { const index = row * config.size + col; board[index] = refillColor(row, col); frozen[index] = 0; }
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
    el('message').textContent = 'Level ' + level + ' · Clear ' + config.target + ' bubbles in ' + config.moves + ' swaps.';
    el('instruction').textContent = level < 45 ? 'Swipe a bubble one space in any direction to swap. Only lines of three or more clear.' : 'Swipe one space at a time. Frozen bubbles take two neighboring matches to break. ' + config.colors + ' colors are in play — plan your chain carefully.';
    render(); bestText();
  }
  el('next').addEventListener('click', () => { if (level < MAX_LEVEL) { level++; start(); } });
  el('restart').addEventListener('click', start);
  el('reset').addEventListener('click', () => { level = 1; save('bubble-crush-level', 1); start(); });
  setInterval(() => { if (started && !solved) elapsed = Math.floor((Date.now() - started) / 1000); el('timer').textContent = clock(elapsed); }, 250);
  start();
})();
