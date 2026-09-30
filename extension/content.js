(function () {
  if (window.top !== window.self || document.documentElement.dataset.mak3dealsAssistant) return;
  document.documentElement.dataset.mak3dealsAssistant = "loaded";

  const stores = [
    ["amazon.", "Amazon"], ["walmart.", "Walmart"], ["bestbuy.", "Best Buy"],
    ["homedepot.", "Home Depot"], ["costco.", "Costco"], ["nike.", "Nike"],
    ["macys.", "Macy's"], ["kohls.", "Kohl's"], ["chewy.", "Chewy"]
  ];
  const store = stores.find(([fragment]) => location.hostname.toLowerCase().includes(fragment));
  if (!store) return;

  const escapeHtml = value => String(value || "").replace(/[&<>\"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
  const title = (document.querySelector("h1")?.innerText || document.title || "").trim().slice(0, 180);
  const host = location.hostname;

  const style = document.createElement("style");
  style.textContent = `
    #mak3deals-assistant{position:fixed;right:20px;bottom:20px;z-index:2147483647;width:min(360px,calc(100vw - 32px));font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:#182536}
    #mak3deals-assistant *{box-sizing:border-box}
    .m3d-panel{overflow:hidden;border:1px solid #dfe7eb;border-radius:16px;background:#fff;box-shadow:0 18px 52px rgba(24,37,54,.22)}
    .m3d-head{display:flex;align-items:center;justify-content:space-between;padding:13px 15px;background:#f6fbf9;border-bottom:1px solid #dfe7eb}
    .m3d-brand{display:flex;align-items:center;gap:9px}.m3d-mark{display:grid;place-items:center;width:27px;height:27px;border-radius:8px;background:#ed7d24;color:#fff;font-weight:950;transform:rotate(-7deg)}
    .m3d-head strong{display:block;font-size:14px}.m3d-head small{display:block;color:#627286;font-size:11px}.m3d-close{border:0;background:transparent;color:#627286;font-size:20px;line-height:1;cursor:pointer}
    .m3d-body{padding:15px}.m3d-status{display:flex;gap:9px;align-items:flex-start}.m3d-dot{width:8px;height:8px;flex:0 0 8px;margin-top:6px;border-radius:50%;background:#157c72;box-shadow:0 0 0 4px #e1f2ee}.m3d-status strong{display:block;font-size:15px}.m3d-status span{display:block;margin-top:2px;color:#627286;font-size:12px}
    .m3d-actions{display:grid;grid-template-columns:1fr auto;gap:8px;margin-top:14px}.m3d-actions a{padding:9px 11px;border-radius:8px;background:#ed7d24;color:#fff;text-align:center;text-decoration:none;font-weight:850}.m3d-actions button{padding:9px 11px;border:1px solid #cfe2dc;border-radius:8px;background:#edf7f4;color:#157c72;font-weight:850;cursor:pointer}
    .m3d-offer{display:grid;gap:4px;margin-top:13px;padding:11px;border:1px solid #e5ecef;border-radius:11px}.m3d-offer strong{font-size:13px}.m3d-price{color:#157c72;font-weight:950}.m3d-muted{color:#627286;font-size:11px}
    @media(max-width:520px){#mak3deals-assistant{right:12px;bottom:12px;width:calc(100vw - 24px)}}`;
  document.documentElement.appendChild(style);

  const root = document.createElement("aside");
  root.id = "mak3deals-assistant";
  root.setAttribute("aria-label", "Mak3Deals savings assistant");
  root.innerHTML = `<div class="m3d-panel"><div class="m3d-head"><div class="m3d-brand"><span class="m3d-mark" aria-hidden="true">M</span><div><strong>Mak3Deals</strong><small>Shopping assistant</small></div></div><button class="m3d-close" type="button" aria-label="Close Mak3Deals savings assistant">×</button></div><div class="m3d-body"><div class="m3d-status"><span class="m3d-dot" aria-hidden="true"></span><div><strong>Checking ${escapeHtml(store[1])}</strong><span>Only verified savings are shown.</span></div></div></div></div>`;
  document.body.appendChild(root);
  root.querySelector(".m3d-close").addEventListener("click", () => root.remove());

  const body = root.querySelector(".m3d-body");
  const send = (type, payload) => new Promise(resolve => chrome.runtime.sendMessage({type, store: store[1], ...payload}, response => resolve(response || {})));
  Promise.all([send("find-coupons"), send("find-offers", {query: title})]).then(([couponResponse, offerResponse]) => {
    const coupons = couponResponse.ok ? (couponResponse.coupons || []) : [];
    const offers = offerResponse.ok ? (offerResponse.offers || []) : [];
    if (!coupons.length && !offers.length) {
      body.innerHTML = `<div class="m3d-status"><span class="m3d-dot" aria-hidden="true"></span><div><strong>No verified savings found yet</strong><span>We did not find a confirmed code or matching Mak3Deals offer for this page.</span></div></div><div class="m3d-actions"><a href="https://mak3deals.com/coupons?store=${encodeURIComponent(store[1])}" target="_blank" rel="noopener">Browse Mak3Deals</a><button type="button" class="m3d-dismiss">Dismiss</button></div>`;
      body.querySelector(".m3d-dismiss").addEventListener("click", () => root.remove());
      return;
    }
    const coupon = coupons[0];
    const offer = offers[0];
    body.innerHTML = `<div class="m3d-status"><span class="m3d-dot" aria-hidden="true"></span><div><strong>Mak3Deals found ${coupons.length + offers.length} way${coupons.length + offers.length === 1 ? "" : "s"} to save</strong><span>Verified options for ${escapeHtml(store[1])}.</span></div></div>${coupon ? `<div class="m3d-offer"><strong>Coupon available</strong><span class="m3d-price">${escapeHtml(coupon.coupon_code)}</span><span class="m3d-muted">${escapeHtml(coupon.title)}</span></div>` : ""}${offer ? `<div class="m3d-offer"><strong>Matching deal</strong><span>${escapeHtml(offer.title)}</span><span class="m3d-price">${escapeHtml(offer.sale_price || "See offer")}</span></div>` : ""}<div class="m3d-actions"><a href="https://mak3deals.com/coupons?store=${encodeURIComponent(store[1])}" target="_blank" rel="noopener">Open savings</a><button type="button" class="m3d-dismiss">Dismiss</button></div>`;
    body.querySelector(".m3d-dismiss").addEventListener("click", () => root.remove());
  }).catch(() => {
    body.innerHTML = `<div class="m3d-status"><span class="m3d-dot" aria-hidden="true"></span><div><strong>Mak3Deals is unavailable</strong><span>Try the extension again in a moment.</span></div></div>`;
  });
})();
