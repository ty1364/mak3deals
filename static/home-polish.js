(() => {
  const labelMap = new Map([
    ['MAK3DEALS SHOPPING DESK', 'Mak3Deals shopping'],
    ['SHOP BY CATEGORY', 'Browse by category'],
    ['REAL-TIME SAVINGS', 'Verified deals'],
    ['COMPARE BEFORE YOU BUY', 'Shop the catalog'],
    ['EDITORIAL SAVINGS WATCH', 'Retailer picks'],
    ['CODES AND OFFERS', 'Coupons & offers'],
    ['FREE DAILY CHALLENGE', 'Daily word challenge'],
  ]);

  function softenLabels() {
    document.querySelectorAll('.shopping-home .eyebrow, .shopping-home .shopping-ad-channel-label').forEach((node) => {
      const replacement = labelMap.get(node.textContent.trim());
      if (replacement) node.textContent = replacement;
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', softenLabels, { once: true });
  else softenLabels();
})();
