# Commerce roadmap

## Boundary for this milestone

The public site is a read-only catalog. It does not create customer accounts, identify devices, accept money, reserve stock, calculate shipping, create orders or send messages. Product records contain optional commerce-shaped fields only so the future system can evolve without rewriting the marketing layer.

## Proposed domains

### Product configurator

`/configure/[product]` should consume a versioned catalog service and enforce server-side compatibility rules for storage, memory, display variants and accessories. A configuration must produce a signed or server-resolved SKU reference; prices must never be trusted from the browser.

### Cart

`/cart` should store opaque product/configuration identifiers and quantities. The server recalculates availability, price, tax inputs and shipping eligibility on every material transition. Anonymous carts can later be associated with an account without duplicating orders.

### Checkout and payments

`/checkout` should use hosted or tokenized payment collection from a selected provider. The application must never store raw card data. Payment and checkout creation require idempotency keys; provider webhooks require signature verification, replay protection and an append-only processing log. The provider remains an architectural choice until commercial and regional requirements are known.

### Account and orders

`/account` should use a dedicated authentication boundary with secure session management, verified email changes and recovery policy. `/orders/[id]` must authorize every read against the owning customer or support role. Public device accounts and local device administrator accounts should remain separate identities unless a future security design explicitly links them.

### Fulfillment and shipment tracking

Order state should be a server-owned state machine with immutable transition history. Fulfillment adapters should translate internal line items into warehouse requests, reconcile partial shipments and expose only customer-safe tracking data. Carrier webhooks need the same verification, idempotency and observability standards as payments.

### Transactional email

Email should consume domain events such as order accepted, payment failed, shipment created and delivery exception. Templates require versioning, localization, privacy review and a delivery audit trail. Marketing consent must remain independent from transactional delivery.

## Data and operational requirements

- authoritative server-side pricing and tax inputs;
- inventory reservation with expiry and concurrency handling;
- explicit currency and locale handling;
- webhook signature verification and replay defense;
- idempotent checkout, payment, order and fulfillment operations;
- no raw payment-card storage;
- least-privilege service credentials and secret rotation;
- structured audit events and privacy-aware observability;
- clear cancellation, return, warranty and support policies before launch;
- accessibility testing for configuration and checkout flows.

## Suggested delivery order

1. Finalize SKU/configuration rules and catalog ownership.
2. Build a non-purchasing configurator with saved configuration URLs.
3. Add server-side cart and inventory validation.
4. Select payment, tax and fulfillment integrations through a requirements review.
5. Implement checkout and webhook-driven order creation.
6. Add account, order history, shipment state and transactional email.
7. Complete security, accessibility, legal and operational launch reviews.
