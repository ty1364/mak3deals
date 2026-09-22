(function(){
  const key='mak3deals-watchlist';
  function read(){try{return JSON.parse(localStorage.getItem(key)||'[]')}catch(e){return []}}
  function write(items){localStorage.setItem(key,JSON.stringify(items))}
  function sync(){const items=read();document.querySelectorAll('.watch-btn').forEach(btn=>{const card=btn.closest('[data-deal-id]');const id=card&&card.dataset.dealId;const saved=items.some(x=>x.id===id);btn.classList.toggle('saved',saved);btn.textContent=saved?'★ Watching':'☆ Watch'})}
  function toggle(btn){const card=btn.closest('[data-deal-id]');const id=card.dataset.dealId;let items=read();if(items.some(x=>x.id===id)){items=items.filter(x=>x.id!==id)}else{items.push({id:id,title:btn.dataset.title})}write(items);sync()}
  document.addEventListener('click',e=>{if(e.target.closest('.watch-btn'))toggle(e.target.closest('.watch-btn'))});
  window.renderWatchlistPage=function(){const box=document.getElementById('watchlist-items');if(!box)return;const items=read();if(!items.length){box.innerHTML='<p class="empty-watch">Your watchlist is empty. Browse <a href="/">current offers</a> and tap Watch.</p>';return}box.innerHTML=items.map(x=>'<article class="deal-card"><span class="tag">Watched offer</span><h3>'+x.title.replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))+'</h3><p>Saved in this browser. Recheck the official source before buying.</p><button class="watch-btn saved" data-deal-id="'+x.id+'" data-title="'+x.title.replace(/"/g,'&quot;')+'">★ Watching</button></article>').join('');sync()};
  sync();
})();
