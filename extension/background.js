const API = "https://mak3deals.com/api/coupons";
const OFFERS_API = "https://mak3deals.com/api/offers";

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

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "find-offers") return;
  const url = new URL(OFFERS_API);
  if (message.store) url.searchParams.set("store", message.store);
  if (message.query) url.searchParams.set("q", message.query);
  fetch(url)
    .then(response => response.ok ? response.json() : Promise.reject(new Error("Offer service unavailable")))
    .then(data => sendResponse({ok: true, offers: data.offers || []}))
    .catch(error => sendResponse({ok: false, error: error.message}));
  return true;
});
