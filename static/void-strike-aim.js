(function(){const c=document.getElementById('game');if(!c)return;c.addEventListener('pointermove',function(e){const r=c.getBoundingClientRect();mouse.x=(e.clientX-r.left)*(W/r.width);mouse.y=(e.clientY-r.top)*(H/r.height);});})();

