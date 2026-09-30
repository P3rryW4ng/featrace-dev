# STORE-001 — Member discount with preserved checkout contracts (approved v1)
This is a synthetic feature approved by the product owner. Use Python standard library only; integer cents only; no external I/O or persistence.

R-PREVIEW: add optional member=False to storefront.preview(lines). Existing callers omitting it keep exactly the current undiscounted result. For member=True apply 10% of the subtotal, floor to integer cents, capped at 2000 cents per order. Return the existing three keys subtotal_cents, discount_cents, total_cents; total=subtotal-discount. Empty preview stays all zero. Existing invalid-line validation remains. Multiple entries for the same SKU count in subtotal normally.

R-CHECKOUT: add optional member=False to Checkout.place_order(request_id, lines). Member orders charge exactly the same policy result as preview. Receipt type and export_receipt output format remain unchanged; paid_cents is the charged final amount. Repeating a successful request ID must return the same original receipt object, even if the later lines/member differ or are invalid; never charge or reserve inventory again and never replace the first receipt.

R-ATOMIC: if validation, stock or payment fails, stock, charges and receipt cache must remain as before the attempt. A declined payment may consume the simulator's decline_next flag; a later retry with the same request ID can succeed once. Account for repeated SKUs in stock validation. Empty order still raises ValueError.

R-PRESERVE: calculate_total(lines) and legacy_export.export_subtotal(lines) retain undiscounted gross totals. Never apply the member discount to legacy exports or rewrite already created receipt amounts. Default callers and existing tests must continue to work. No change to prices, receipt IDs, or payment ledger contract.

Technical implementation and test design are delegated to the Agent; do not ask for a product decision about internal helper names. Product membership input is a boolean. No GUI/API/Figma is involved.
