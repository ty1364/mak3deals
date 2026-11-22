(function () {
  const form = document.getElementById("price-check-form");
  const results = document.getElementById("price-check-results");
  if (!form || !results) return;

  const money = (value) => new Intl.NumberFormat(undefined, {
    style: "currency", currency: "USD"
  }).format(value);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const entries = ["a", "b"].map((key) => {
      const value = (name) => Number(form.elements[`${name}-${key}`].value);
      const price = value("price");
      const units = value("units");
      const fees = value("fees");
      const coupon = value("coupon");
      if (![price, units, fees, coupon].every(Number.isFinite) || price < 0 || units <= 0 || fees < 0 || coupon < 0) {
        return null;
      }
      const appliedCoupon = Math.min(price, coupon);
      return {
        label: form.elements[`label-${key}`].value.trim() || `Option ${key.toUpperCase()}`,
        total: Math.max(0, price - appliedCoupon) + fees,
        perUnit: (Math.max(0, price - appliedCoupon) + fees) / units,
      };
    });

    if (entries.some((entry) => !entry)) {
      results.textContent = "Enter a package price, a positive unit count, and non-negative fees and coupon amounts.";
      return;
    }

    const [a, b] = entries;
    const winner = a.perUnit === b.perUnit
      ? "Both options have the same estimated price per unit."
      : `${a.perUnit < b.perUnit ? a.label : b.label} has the lower estimated price per unit.`;
    results.replaceChildren();
    const lines = [
      `${a.label}: ${money(a.total)} before tax · ${money(a.perUnit)} per unit`,
      `${b.label}: ${money(b.total)} before tax · ${money(b.perUnit)} per unit`,
      winner,
    ];
    lines.forEach((line, index) => {
      const paragraph = document.createElement("p");
      if (index === 2) {
        const strong = document.createElement("strong");
        strong.textContent = line;
        paragraph.append(strong);
      } else {
        paragraph.textContent = line;
      }
      results.append(paragraph);
    });
  });
})();
