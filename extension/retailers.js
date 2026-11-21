// Keep the supported-retailer registry in one place for the popup and page assistant.
const MAK3DEALS_RETAILERS = [
  { fragment: "amazon.", name: "Amazon" },
  { fragment: "walmart.", name: "Walmart" },
  { fragment: "bestbuy.", name: "Best Buy" },
  { fragment: "homedepot.", name: "Home Depot" },
  { fragment: "costco.", name: "Costco" },
  { fragment: "nike.", name: "Nike" },
  { fragment: "macys.", name: "Macy's" },
  { fragment: "kohls.", name: "Kohl's" },
  { fragment: "chewy.", name: "Chewy" }
];

function mak3dealsRetailerForHost(hostname) {
  const host = String(hostname || "").toLowerCase();
  return MAK3DEALS_RETAILERS.find(retailer => host.includes(retailer.fragment)) || null;
}
