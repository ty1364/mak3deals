const API = "https://mak3deals.com/api/coupons";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "find-coupons") return;
  const url = new URL(API);
  if (message.store) url.searchParams.set("store", message.store);
  fetch(url)
    .then(response => response.ok ? response.json() : Promise.reject(new Error("Coupon service unavailable")))
    .then(data => sendResponse({ok: true, coupons: data.coupons || []}))
    .catch(error => sendResponse({ok: false, error: error.message}));
  return true;
});
