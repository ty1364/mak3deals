const status = document.querySelector("#status");
const results = document.querySelector("#results");

function render(coupons) {
  results.hidden = false;
  if (!coupons.length) {
    results.innerHTML = '<p class="muted">No verified coupon codes are available for this store yet. We will not show unverified codes.</p>';
    return;
  }
  results.innerHTML = coupons.map((coupon, index) => `
    <article class="coupon"><strong>${escapeHtml(coupon.title)}</strong>
      <code>${escapeHtml(coupon.coupon_code)}</code>
      <button data-index="${index}">Copy code</button>
      <p class="muted">Checked ${escapeHtml(coupon.checked_on || "recently")} · Ends ${escapeHtml(coupon.expires_on)}</p>
    </article>`).join("");
  results.querySelectorAll("button").forEach(button => button.addEventListener("click", async () => {
    await navigator.clipboard.writeText(coupons[button.dataset.index].coupon_code);
    button.textContent = "Copied";
    setTimeout(() => { button.textContent = "Copy code"; }, 1200);
  }));
}

function renderOffers(offers) {
  if (!offers.length) return '<p class="muted">No matching verified Mak3Deals offer yet. We will not recommend an unrelated product.</p>';
  return '<h3>Mak3Deals matches</h3>' + offers.map(offer => `
    <article class="offer">${offer.image_url && /^https:\/\//i.test(offer.image_url) ? `<img class="offer-image" src="${escapeHtml(offer.image_url)}" alt="${escapeHtml(offer.title)}" loading="lazy">` : ''}<strong>${escapeHtml(offer.title)}</strong>
      <span class="offer-price">${escapeHtml(offer.sale_price || "See offer")}</span>
      ${offer.regular_price ? `<span class="muted"> regularly ${escapeHtml(offer.regular_price)}</span>` : ''}
      <p class="muted">Checked ${escapeHtml(offer.checked_on || "recently")} · Ends ${escapeHtml(offer.expires_on)}</p>
      <a href="${offer.product_key ? `https://mak3deals.com/compare/${encodeURIComponent(offer.product_key)}` : `https://mak3deals.com/click/${encodeURIComponent(offer.id)}`}" target="_blank">${offer.product_key ? 'Compare stores →' : 'Get deal →'}</a>
    </article>`).join('');
}

function escapeHtml(value) { return String(value || "").replace(/[&<>\"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char])); }

chrome.tabs.query({active: true, currentWindow: true}, tabs => {
  const tab = tabs[0];
  if (!tab || !tab.id || !/^https?:/.test(tab.url || "")) {
    status.textContent = "Open a supported shopping page first.";
    return;
  }
  chrome.scripting.executeScript({target: {tabId: tab.id}, func: () => {
    const stores = [["amazon.", "Amazon"], ["walmart.", "Walmart"], ["bestbuy.", "Best Buy"], ["homedepot.", "Home Depot"], ["costco.", "Costco"], ["nike.", "Nike"], ["macys.", "Macy's"], ["kohls.", "Kohl's"], ["chewy.", "Chewy"]];
    const host = location.hostname.toLowerCase();
    const match = stores.find(([fragment]) => host.includes(fragment));
    const fields = [...document.querySelectorAll("input")].filter(input => /coupon|promo|discount|voucher|offer code/i.test(`${input.name} ${input.id} ${input.placeholder} ${input.getAttribute("aria-label") || ""}`));
    const title = document.querySelector("h1")?.innerText?.trim() || document.title || "";
    return {store: match ? match[1] : "", title: title.slice(0, 180), supported: Boolean(match), checkoutLike: fields.length > 0};
  }})
    .then(results => {
      const details = results[0]?.result || {};
      if (!details.supported) {
        status.textContent = "This store is not supported yet.";
        return;
      }
      status.textContent = details.checkoutLike ? `Verified codes for ${details.store}` : `${details.store} savings`;
      chrome.runtime.sendMessage({type: "find-coupons", store: details.store}, response => {
        if (chrome.runtime.lastError || !response?.ok) { status.textContent = "Savings service is temporarily unavailable."; return; }
        render(response.coupons);
        chrome.runtime.sendMessage({type: "find-offers", store: details.store, query: details.title}, offerResponse => {
          if (offerResponse?.ok) results.insertAdjacentHTML('afterbegin', renderOffers(offerResponse.offers));
        });
      });
    })
    .catch(() => { status.textContent = "This page does not allow savings detection."; });
});
