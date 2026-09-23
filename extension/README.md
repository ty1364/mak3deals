# Mak3Deals Savings Finder

This is the first Chrome/Edge Manifest V3 extension for Mak3Deals.

## Current behavior

- User opens the extension on a shopping page.
- The extension recognizes supported stores and looks for a coupon field.
- It requests only current, verified codes from `https://mak3deals.com/api/coupons`.
- It lets the user copy a code; it does not silently change checkout forms.
- It looks for a matching verified Mak3Deals offer and provides a clearly labeled affiliate “Get deal” link.

## Load locally

1. Open `chrome://extensions` or `edge://extensions`.
2. Enable Developer mode.
3. Choose **Load unpacked**.
4. Select this `extension` folder.

Automatic code testing and broader product comparison should be added only after we have merchant-specific adapters, verified affiliate links, and clear user controls.
