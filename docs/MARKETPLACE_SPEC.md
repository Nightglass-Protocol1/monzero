# XMZ digital goods marketplace — specification (not implemented)

Status 2026-10-19: specification only, as the website brief requires. Nothing
here is built or deployed. It does not include escrow, custody or fund
management, and none of those may be added without a separate security, legal
and operational review.

## Principle: the marketplace never touches money

Buyers pay merchants directly, to each merchant's own wallet. The marketplace
is a catalog plus order bookkeeping. It cannot hold, release, refund or
redirect funds. Payment detection is done by each merchant's own view-only
wallet, as described in the merchant guide (`/developers/payments/`).

## Roles

- **Merchant**: lists digital products and runs their own view-only wallet and
  payment watcher.
- **Buyer**: browses, places an order, pays from their own wallet.
- **Moderator**: reviews merchant profiles and listings and handles reports.
  Needs the authenticated admin system (plan, Phase 10).

## Capabilities

| Capability | Design |
|---|---|
| Merchant profiles | Name, description, contact, public support policy. Ownership proven by signing a challenge with the merchant's wallet (as `/wallets/` already does). No KYC data stored. |
| Product listings | Title, description, price in atomic XMZ (string), delivery method (download link, licence key, manual). Reviewed before publishing. No physical goods at first. |
| Payment requests | The merchant's watcher creates a subaddress per order and returns a `monzero:` URI. The marketplace stores the subaddress, amount and expiry, never a key. |
| Order management | States: `created → awaiting_payment → paid (merchant-reported) → delivered → closed`, plus `expired` and `disputed`. "Paid" is reported by the merchant's watcher through a signed callback (HMAC, as in the merchant guide). The marketplace does not verify payments itself. |
| Delivery confirmation | The buyer confirms receipt, or the order closes automatically N days after delivery with no dispute. |
| Dispute reporting | The buyer opens a report with a reason; a moderator mediates between the parties. The only remedies are reputation effects and delisting, never moving funds. This must be said plainly at checkout. |
| Merchant reputation | Count of closed orders and disputes per merchant, plus buyer ratings tied to closed orders only. No ratings without an order. |

## Data model (sketch)

`merchants(id, display_name, view_proof, status, created_at)`,
`listings(id, merchant_id, title, price_atomic, delivery, status, reviewed_by, reviewed_at)`,
`orders(id, listing_id, buyer_token_hash, subaddress, amount_atomic, state, expires_at, created_at)`,
`order_events(order_id, state, actor, at)` (append-only),
`reports(id, order_id, reason, state, moderator, resolved_at)`,
`ratings(order_id, score, comment, at)`.

Buyers can stay anonymous: an order is tied to a random buyer token kept in
the browser, not to an account.

## Risks to resolve before building

- Legal: selling digital goods and running a marketplace carries consumer-law,
  tax and content obligations that vary by country. Get advice first.
- Content moderation: prohibited-goods policy, reporting and takedown process.
- Fraud: merchants who never deliver. Without escrow, the only defences are
  reputation, review before listing, and fast delisting. Buyers must be told.
- Dependencies: authenticated admin and moderation (Phase 10) and the merchant
  callback contract need to exist first.

## Not in scope

Escrow, multisig escrow, custodial wallets, refunds by the platform, fiat
payments, physical goods, automatic payouts.
