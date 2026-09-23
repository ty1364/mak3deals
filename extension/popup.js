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

function escapeHtml(value) { return String(value || "").replace(/[&<>\"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char])); }

chrome.tabs.query({active: true, currentWindow: true}, tabs => {
  const tab = tabs[0];
  if (!tab || !tab.id || !/^https?:/.test(tab.url || "")) {
    status.textContent = "Open a supported shopping page first.";
    return;
  }
  chrome.scripting.executeScript({target: {tabId: tab.id}, func: () => {
    const stores = [["amazon.", "Amazon"], ["walmart.", "Walmart"], ["target.", "Target"], ["bestbuy.", "Best Buy"], ["homedepot.", "Home Depot"], ["costco.", "Costco"], ["nike.", "Nike"], ["macys.", "Macy's"], ["kohls.", "Kohl's"], ["chewy.", "Chewy"]];
    const host = location.hostname.toLowerCase();
    const match = stores.find(([fragment]) => host.includes(fragment));
    const fields = [...document.querySelectorAll("input")].filter(input => /coupon|promo|discount|voucher|offer code/i.test(`${input.name} ${input.id} ${input.placeholder} ${input.getAttribute("aria-label") || ""}`));
    return {store: match ? match[1] : "", supported: Boolean(match), checkoutLike: fields.length > 0};
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
      });
    })
    .catch(() => { status.textContent = "This page does not allow savings detection."; });
});
