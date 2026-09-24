(() => {
  const el = id => document.getElementById(id);
  let level = 1, size = 3, tiles = [], initial = [], moves = 0, started = 0, elapsed = 0, solved = false;
  const neighbors = (index, n) => [index-n,index+n,index-1,index+1].filter(i => i>=0 && i<n*n && Math.abs(i%n-index%n)+Math.abs(Math.floor(i/n)-Math.floor(index/n))===1);
  const complete = a => a.every((v,i) => v === (i+1)%a.length);
  const clock = seconds => `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
  function bestText() {
    try { const best = JSON.parse(localStorage.getItem(`tile-shift-best-${level}`)); el('best').textContent = best ? `Level ${level} best: ${best.moves} moves · ${clock(best.seconds)}` : 'Solve this level to set your first personal best.'; }
    catch { el('best').textContent = 'Personal-best storage unavailable.'; }
  }
  function render(focusValue) {
    const blank = tiles.indexOf(0), available = neighbors(blank,size);
    el('board').style.setProperty('--size',size);
    el('board').replaceChildren(...tiles.map((value,index) => {
      const tile = document.createElement(value ? 'button' : 'div');
      tile.className = value ? `tile${value===index+1?' correct':''}${available.includes(index)?' movable':''}` : 'empty';
      if (value) { tile.textContent=value; tile.dataset.value=value; tile.setAttribute('aria-label',`Tile ${value}${available.includes(index)?', slide into empty space':''}`); tile.disabled=solved; tile.addEventListener('click',()=>move(index)); }
      else tile.setAttribute('aria-label','Empty space');
      return tile;
    }));
    el('level').textContent=level; el('moves').textContent=moves;
    if(focusValue) el('board').querySelector(`[data-value="${focusValue}"]`)?.focus({preventScroll:true});
  }
  function move(index) {
    const blank=tiles.indexOf(0);
    if(solved || !neighbors(blank,size).includes(index)) return;
    if(!started) started=Date.now();
    const value=tiles[index]; [tiles[index],tiles[blank]]=[tiles[blank],tiles[index]]; moves++;
    solved=complete(tiles);
    if(solved) {
      elapsed=Math.floor((Date.now()-started)/1000);
      el('message').textContent=`Solved! ${moves} moves in ${clock(elapsed)}.`;
      el('next').hidden=false;
      try { const key=`tile-shift-best-${level}`, old=JSON.parse(localStorage.getItem(key)); if(!old || moves<old.moves || (moves===old.moves && elapsed<old.seconds)) localStorage.setItem(key,JSON.stringify({moves,seconds:elapsed})); } catch {}
      bestText();
    }
    render(value);
    if(solved) el('next').focus({preventScroll:true});
  }
  function start(newPuzzle=true) {
    size=level<=3?3:4;
    if(newPuzzle) {
      tiles=Array.from({length:size*size},(_,i)=>(i+1)%(size*size));
      let blank=tiles.length-1, previous=-1;
      const steps=Math.min(180,8+level*8);
      // Legal moves from the solved board guarantee every puzzle is solvable.
      for(let i=0;i<steps;i++) { const options=neighbors(blank,size).filter(v=>v!==previous); const next=options[Math.floor(Math.random()*options.length)]; [tiles[blank],tiles[next]]=[tiles[next],tiles[blank]];previous=blank;blank=next; }
      if(complete(tiles)) { const next=neighbors(blank,size)[0]; [tiles[blank],tiles[next]]=[tiles[next],tiles[blank]]; }
      initial=[...tiles];
    } else tiles=[...initial];
    moves=0;started=0;elapsed=0;solved=false;
    el('timer').textContent='0:00';el('next').hidden=true;
    el('message').textContent=`Level ${level} · ${size} × ${size}${level===1?' warm-up':''}`;
    render();bestText();
  }
  el('next').addEventListener('click',()=>{level++;start();});
  el('restart').addEventListener('click',()=>start(false));
  el('reset').addEventListener('click',()=>{level=1;start();});
  el('board').addEventListener('keydown',event=>{
    const delta={ArrowUp:-size,ArrowDown:size,ArrowLeft:-1,ArrowRight:1}[event.key];
    if(delta!==undefined) {event.preventDefault();move(tiles.indexOf(0)+delta);}
  });
  setInterval(()=>{if(started&&!solved)elapsed=Math.floor((Date.now()-started)/1000);el('timer').textContent=clock(elapsed);},250);
  start();
})();
