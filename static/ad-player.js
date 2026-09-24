(function () {
  const players = document.querySelectorAll("[data-ad-player]");
  if (!players.length) return;

  const housePlacements = [
    { provider: "Mak3Deals house promo", title: "Take a shopping break.", detail: "Play Void Strike and chase the monthly high score.", href: "/game", cta: "Play now →", tone: "pink" },
    { provider: "Direct sponsor placement", title: "Put your business in front of shoppers.", detail: "Verified local and online offers can appear here.", href: "/submit", cta: "Submit a deal →", tone: "blue" },
    { provider: "Google AdSense slot", title: "Google ads are coming.", detail: "This placement is ready for AdSense approval and ad-unit setup.", href: "/affiliate-disclosure", cta: "View disclosure →", tone: "gold" }
  ];

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>\"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[char]));
  }

  function offerPlacement(offer) {
    return {
      provider: `${offer.store} verified offer`,
      title: offer.title,
      detail: `${offer.sale_price || "See current price"} · ${offer.offer_terms || "Retailer terms apply."}`,
      image: offer.image_url,
      href: `/click/${encodeURIComponent(offer.id)}`,
      cta: "See official offer →",
      tone: "cyan"
    };
  }

  function render(player, placement) {
    const image = placement.image && /^https:\/\//i.test(placement.image)
      ? `<img class="ad-player-image" src="${escapeHtml(placement.image)}" alt="${escapeHtml(placement.title)}" loading="lazy">`
      : "";
    player.querySelector(".ad-player-screen").innerHTML = `${image}<div class="ad-player-copy ${escapeHtml(placement.tone)}"><span class="ad-player-provider">${escapeHtml(placement.provider)}</span><strong>${escapeHtml(placement.title)}</strong><span class="ad-player-detail">${escapeHtml(placement.detail)}</span><a class="ad-player-cta" href="${escapeHtml(placement.href)}">${escapeHtml(placement.cta)}</a></div>`;
  }

  fetch("/api/offers?store=Walmart", { headers: { Accept: "application/json" } })
    .then((response) => response.ok ? response.json() : { offers: [] })
    .then((data) => {
      const placements = [...(data.offers || []).slice(0, 1).map(offerPlacement), ...housePlacements];
      players.forEach((player) => {
        let index = 0;
        render(player, placements[index]);
        window.setInterval(() => { index = (index + 1) % placements.length; render(player, placements[index]); }, 7000);
      });
    })
    .catch(() => players.forEach((player) => render(player, housePlacements[0])));
})();
