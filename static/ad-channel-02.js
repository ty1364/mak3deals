(function(){
  const slots=document.querySelectorAll('[data-ad-channel-02]');
  if(!slots.length)return;
  const inventory=[
    {id:'channel-02-house-catalog',kind:'House promotion',title:'Browse all connected products.',detail:'Search current merchant inventory with direct product links.',href:'/products',cta:'Open the catalog →'},
    {id:'channel-02-house-coupons',kind:'House promotion',title:'Check the coupon desk.',detail:'See offers only when a permitted source confirms them.',href:'/coupons',cta:'Browse coupons →'},
    {id:'channel-02-house-disclosure',kind:'House promotion',title:'Find products worth comparing.',detail:'Mak3Deals shopping links and disclosures are explained here.',href:'/affiliate-disclosure',cta:'How disclosures work →'}
  ];
  function escapeHtml(value){return String(value||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
  function render(slot,item){slot.dataset.activeCreative=item.id;slot.querySelector('.shopping-ad-channel-label').textContent=`AD CHANNEL 02 · ${item.kind.toUpperCase()}`;slot.querySelector('.shopping-ad-channel-title').textContent=item.title;slot.querySelector('.shopping-ad-channel-detail').textContent=item.detail;const cta=slot.querySelector('.shopping-ad-channel-02-cta');cta.href=item.href;cta.textContent=item.cta}
  slots.forEach(slot=>{let index=0;render(slot,inventory[index]);window.setInterval(()=>{index=(index+1)%inventory.length;render(slot,inventory[index])},9000)})
})();
