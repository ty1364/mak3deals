"""Practical, original shopping guides for Mak3Deals readers.

The guides focus on decisions shoppers can reproduce themselves. They do not
claim retailer relationships, personal testing, or savings that Mak3Deals has
not observed.
"""

GUIDES = [
    {
        "slug": "compare-the-final-price",
        "title": "Compare the price you will actually pay",
        "dek": "A sale sticker is only a starting point. Compare the same item, the same quantity, and the costs and conditions that reach checkout.",
        "category": "Price comparison",
        "sections": [
            ("Match the item before comparing prices", "Start with the manufacturer and model number, then match size, count, color, condition, included accessories, and seller. A marketplace listing for a similar-looking product may be a different model or a different seller. For groceries and household supplies, compare the same net weight or number of usable units. If the package sizes differ, write down both sizes before comparing the sticker prices."),
            ("Build the out-the-door comparison", "For each option, write down the item price, delivery or pickup charge, service fees, and any discount you can actually use. Subtract a coupon only after checking its minimum spend, eligible item, account requirement, and expiration. Taxes depend on the shopper's location and usually are not included in a displayed price, so compare tax treatment consistently. A free-shipping threshold is useful only if the extra items are things you already planned to buy."),
            ("Normalize different package sizes", "When quantities differ, divide the relevant total by the same unit: dollars per ounce, pound, load, diaper, or item. Keep the unit visible in your notes. For a multi-pack with a fixed delivery fee, include the fee before dividing; otherwise a small package can look artificially cheap. Unit price is a comparison aid, not a reason to buy more than you can use."),
            ("Compare conditions, not just totals", "Check whether the lower price requires a loyalty account, a digital coupon, store pickup, a subscription, a trade-in, or a particular payment method. Record the seller and condition too: new, open-box, refurbished, or third-party marketplace. Compare return windows and warranty coverage when they differ. A lower price with a condition you would not accept is not the better option for you."),
            ("Use the worksheet below", "Enter the package price, one-time delivery and service charges, coupon amount applied to that item, and the number of comparable units in the package. The worksheet reports an estimated pre-tax total and price per unit. It does not fetch retailer prices, check coupon eligibility, estimate taxes, or guarantee inventory; confirm those details on the retailer's checkout page."),
        ],
        "show_price_tool": True,
    },
    {
        "slug": "how-to-use-coupon-codes",
        "title": "Use printable, digital, and checkout coupons with fewer surprises",
        "dek": "A coupon is useful when you can identify its source, qualify for its terms, and see the savings applied before payment.",
        "category": "Coupons",
        "sections": [
            ("Identify what kind of coupon you have", "A promo code is typed into a retailer's checkout. A digital store coupon is usually clipped or activated in the retailer's account or app. A printable manufacturer coupon is printed from the manufacturer's or an authorized coupon provider's page and presented under its stated redemption terms. A weekly-ad price may require no code at all. These offers are not interchangeable, so follow the redemption path named by the source."),
            ("Check the complete terms before adding items", "Look for the eligible brand, size, flavor, model, minimum spend, quantity limit, customer type, store region, and end date. Check whether the offer excludes sale items or third-party sellers. A headline such as '$5 off' may apply only to a qualifying bundle or a specific order threshold. If the offer is account-targeted, do not assume another shopper will see it."),
            ("Treat clipping and printing as separate steps", "For a digital offer, sign in to the correct retailer account and confirm the coupon is clipped or activated before checkout. For a printable coupon, use the source's own print control and read its print and redemption limits; avoid copies whose origin or terms are unclear. Save the offer page or note the date you checked it so you can revisit the same terms if the register or checkout rejects it."),
            ("Test the cart before paying", "Enter a code only in the retailer's coupon field, then inspect the order summary. Confirm which items received the discount, whether shipping changed, and whether another promotion was removed. If the discount does not appear, remove the code and review its eligibility rather than assuming the retailer will correct the total later. Never submit an order just to test a coupon."),
            ("Use Mak3Deals as a starting point, not a guarantee", "A code or promotion can change after it is checked, and retailers control redemption. Mak3Deals should show the source, last-checked date, known terms, and end date when those details are available. A printable coupon, digital offer, and code should each link to the page where a shopper can review or redeem it. If no current code is available, that is better information than an invented one."),
        ],
    },
    {
        "slug": "grocery-savings-without-waste",
        "title": "Compare grocery offers without buying food you will waste",
        "dek": "A lower unit price can help, but only when the quantity, expiration, storage, and meals fit your household.",
        "category": "Groceries",
        "sections": [
            ("Compare the same unit", "Grocery packages often differ in net weight, count, or serving size. Divide the price by ounces, pounds, loads, or individual pieces and compare the same unit. For produce sold by weight, estimate the amount you will actually use; for packaged goods, check net weight rather than the package dimensions. A promotion for a larger size is not automatically cheaper per unit."),
            ("Calculate multi-buy promotions carefully", "For 'two for' offers, check whether buying two is required or whether each item receives the advertised price. For buy-one-get-one offers, confirm the eligible products, whether the lower-priced item is discounted, and whether the offer is limited by account or store. Divide the amount you will pay by the quantity you will take home, not by the maximum quantity printed in the ad."),
            ("Include digital-coupon steps", "A store loyalty price may appear automatically, while a digital coupon may require a signed-in account and an explicit clip action. Check the participating store, purchase limit, and whether the coupon stacks with the shelf promotion. At checkout, verify the discount appears on the receipt before treating it as part of the final price."),
            ("Plan quantity around use and storage", "Before buying a larger pack, check the use-by date, freezer or pantry space, and how many portions your household can realistically use. Perishable food that is discarded has no savings value. A smaller package at a slightly higher unit price can be the sensible choice when it prevents waste or fits the meal plan."),
            ("Keep local offers local", "Weekly ads and digital prices can depend on the selected store or region. Check the store named on the retailer page, the offer's validity dates, and whether the item is available for the trip you plan to make. A price observed for one store should not be presented as a nationwide price without evidence that it applies nationwide."),
        ],
    },
    {
        "slug": "how-mak3deals-checks-offers",
        "title": "How a Mak3Deals offer is sourced and kept current",
        "dek": "A practical explanation of what belongs on a product card, what belongs on a retailer link-out, and when an offer should come down.",
        "category": "Mak3Deals process",
        "sections": [
            ("Product inventory and editorial picks are different", "A product-feed card represents an individual item supplied through an authorized source. It can show a product photo, current price, merchant, availability, direct tracked destination where authorized, and the time the source was checked. A retailer's general sale page is not an individual product deal. An editorial pick instead summarizes a promotion and sends the reader to the retailer to review the current offer."),
            ("Show a discount only when its basis is supported", "A numerical savings claim needs a current price and a supported comparison price or explicit offer terms from a source that permits the use. The arithmetic should be calculated from those values, not typed in as marketing copy. If a product has a current price but no supported comparison price, it can be listed as a regular-price product without a crossed-out price or sale badge."),
            ("Make the date and conditions useful", "A reader needs to know when an offer was checked and, when the source states one, its end date. Store region, membership, coupon clipping, quantity limits, and eligible products belong near the offer when they affect redemption. 'Good through' should reflect the retailer's stated date; it should not be inferred from an ad cycle or left blank when the offer is known to expire."),
            ("Use only assets the source allows", "Product images and descriptions are not automatically free to republish because they appear on a public retailer page. Use images and product fields only when the feed, API, or written terms grant that use. When those rights are not available, use an original short summary and a link to the retailer rather than copying its photo or catalog description."),
            ("Recheck, retire, and correct", "A source timestamp records when a check happened; it is not a promise that a price will remain. An expired offer should be retired, and a failed refresh should not erase a previously valid catalog record unless the source provides a reliable reason to remove it. Readers should be able to report a stale price or broken destination so an editor can recheck the source and correct or remove the listing."),
            ("Disclose the relationship accurately", "A link is an affiliate link only when an approved tracking relationship is actually attached. Paid advertisements, affiliate links, and Mak3Deals house messages are different things and should be labeled accordingly. Retailers control final price, inventory, shipping, coupon acceptance, and checkout terms."),
        ],
    },
]

GUIDE_BY_SLUG = {guide["slug"]: guide for guide in GUIDES}
GUIDE_REDIRECTS = {
    "spot-a-real-deal": "compare-the-final-price",
    "electronics-price-check": "compare-the-final-price",
    "home-improvement-deal-check": "compare-the-final-price",
    "shipping-can-change-the-deal": "compare-the-final-price",
    "membership-and-subscription-traps": "how-to-use-coupon-codes",
    "local-deal-submissions": "how-mak3deals-checks-offers",
}
