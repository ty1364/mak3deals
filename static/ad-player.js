(function () {
  const players = document.querySelectorAll("[data-ad-player]");
  if (!players.length) return;

  const housePlacements = [
    { id: "channel-01-house-deal-desk", provider: "House promotion · Mak3Deals", title: "Shop the verified deal desk.", detail: "Individual products, checked prices, and direct retailer links.", href: "/", cta: "Browse verified deals →", tone: "pink" },
    { id: "channel-01-house-submit", provider: "House promotion · Mak3Deals", title: "Put your business in front of shoppers.", detail: "Verified local and online offers can appear here.", href: "/submit", cta: "Submit a deal →", tone: "blue" },
    { id: "channel-01-house-disclosure", provider: "House promotion · Mak3Deals", title: "Reach shoppers who are ready to save.", detail: "Sponsored placements will be labeled clearly when available.", href: "/affiliate-disclosure", cta: "View disclosure →", tone: "gold" }
  ];

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>\"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[char]));
  }

  function offerPlacement(offer) {
    const sourceHub = offer.deal_kind === "source-hub";
    return {
      id: `channel-01-offer-${offer.id}`,
      provider: sourceHub ? `${offer.store} source link` : (offer.affiliate_url ? `${offer.store} · Authorized affiliate promotion` : `${offer.store} · Verified offer`),
      title: offer.title,
      detail: sourceHub
        ? `Open the retailer's live deal page · ${offer.offer_terms || "Retailer terms apply."}`
        : `${offer.sale_price || "See current price"} · ${offer.offer_terms || "Retailer terms apply."}`,
      image: offer.image_url,
      href: `/click/${encodeURIComponent(offer.id)}`,
      cta: sourceHub ? "Open live deals →" : "See official offer →",
      tone: "cyan"
    };
  }

  function render(player, placement) {
    const image = placement.image && /^https:\/\//i.test(placement.image)
      ? `<img class="ad-player-image" src="${escapeHtml(placement.image)}" alt="${escapeHtml(placement.title)}" loading="lazy">`
      : "";
    player.dataset.activeCreative = placement.id || placement.title;
    player.querySelector(".ad-player-screen").innerHTML = `${image}<div class="ad-player-copy ${escapeHtml(placement.tone)}"><span class="ad-player-provider">${escapeHtml(placement.provider)}</span><strong>${escapeHtml(placement.title)}</strong><span class="ad-player-detail">${escapeHtml(placement.detail)}</span><a class="ad-player-cta" href="${escapeHtml(placement.href)}">${escapeHtml(placement.cta)}</a></div>`;
  }

  const verifiedStoreFeeds = ["Walmart", "Best Buy"].map((store) =>
    fetch(`/api/offers?store=${encodeURIComponent(store)}&v=4fa3930`, { cache: "no-store", headers: { Accept: "application/json" } })
      .then((response) => response.ok ? response.json() : { offers: [] })
  );

  Promise.all(verifiedStoreFeeds)
    .then((feeds) => {
      // Source hubs are shopping links, not advertising inventory. Only a
      // future authorized offer/feed row may appear as a retailer ad here.
      const verifiedOffers = feeds.flatMap((data) => data.offers || []).filter((offer) => offer.deal_kind !== "source-hub");
      const placements = [...verifiedOffers.slice(0, 4).map(offerPlacement), ...housePlacements];
      players.forEach((player) => {
        let index = 0;
        render(player, placements[index]);
        window.setInterval(() => { index = (index + 1) % placements.length; render(player, placements[index]); }, 7000);
      });
    })
    .catch(() => players.forEach((player) => render(player, housePlacements[0])));
})();
