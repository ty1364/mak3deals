(function(){
  function init(){
    document.querySelectorAll('.product-grid-regular img[loading="lazy"]').forEach(function(image){image.loading='eager';});
    var button=document.querySelector('.site-menu-toggle');
    var nav=document.getElementById('site-primary-nav');
    if(!button||!nav)return;
    button.addEventListener('click',function(){
      var open=document.body.classList.toggle('menu-open');
      button.setAttribute('aria-expanded',String(open));
      button.querySelector('.site-menu-label').textContent=open?'Close':'Menu';
      button.querySelector('.site-menu-icon').textContent=open?'×':'☰';
    });
    nav.addEventListener('click',function(event){
      if(event.target.closest('a')){
        document.body.classList.remove('menu-open');
        button.setAttribute('aria-expanded','false');
        button.querySelector('.site-menu-label').textContent='Menu';
        button.querySelector('.site-menu-icon').textContent='☰';
      }
    });
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
