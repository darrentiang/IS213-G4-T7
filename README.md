# BidBoard — Project Context
# IS213-G4-T7

## What This Is

This is a group project (6 people) for IS213 Enterprise Solution Development at SMU. The project is worth 35% of the grade. We build an enterprise solution using microservices architecture following SOA principles.

## Key Dates
- Week 9: Informal proposal presentation (done, feedback received and incorporated)
- Week 13: Final presentation (15 min) + demo + Q&A + report submission

## What Gets Graded
- Presentation with demo: 25 marks
- Report: 10 marks
- Technical depth, design justification, demo quality, Q&A answers
- Beyond the Labs (BTL) implementations must be justified for the scenario

---

## The Application

**BidBoard** is a peer-to-peer marketplace with two purchase modes:

1. **Timed Auction** — Seller creates a scheduled auction with start and end times. Buyers bid during the auction window. When the timer expires, the system automatically charges the highest bidder. If their payment fails, it cascades to the next bidder.

2. **Fixed-Price with Negotiation** — Seller lists an item at a fixed price. Buyer makes an offer. Seller can accept or counter. Buyer can accept or reject the counter. Once both agree, payment is triggered automatically.

No escrow, no confirm receipt, no disputes. Payment is a direct charge via Stripe. Final status is SOLD.

---

## Architecture Rules (from course + professor feedback)

1. **Atomic services cannot call other atomic services.** They must not be aware of each other. Communication between atomics goes through composite services or via AMQP events through RabbitMQ.

2. **Each microservice has exclusive access to its own database.** No foreign key relationships across services. If Service A needs data from Service B, it makes an API call, not a SQL JOIN.

3. **Composite services have no database.** They only coordinate atomic services via HTTP calls and/or AMQP events.

4. **Naming convention:** Atomic services = nouns (Listing, Bid, User). Composite services = verbs (Close Auction, Process Payment, Dispatch Notification).

5. **Box naming on diagrams:** Drop "Service" from box labels. Legend explains types. E.g., yellow box labeled "Listing" with legend saying "<< Atomic >> = Atomic Service".

6. **One composite = one process.** Each composite service should do exactly one thing.

7. **RabbitMQ market.events uses Topic Exchange.** Supports wildcard binding keys for flexible routing. Label it "Topic Exchange" on all diagrams.

8. **Show routing keys and binding keys on diagrams.** Routing key on publish arrows, binding key [BKEY] on consume arrows. Queue names shown on consume arrows.

9. **OutSystems requirement:** Must build and expose at least 1 atomic service on OutSystems. We chose Notification Service.

10. **Payment Service always publishes its own events.** In both US2 and US3, Payment calls Stripe, returns HTTP result to caller, AND publishes payment.success/failed to RabbitMQ. Consistent behavior regardless of which composite called it.

---

## Diagram Flows (Verified)

### US1: Seller Creates Auction Listing

**Pattern:** Event-driven state machine (DLQ/TTL timers)

**Boxes:** Seller Web UI, KONG API Gateway, Listing, market.timers, market.dlq, market.events (Topic Exchange), Dispatch Notification, User, Notification

**Part 1: Seller Creates Listing**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 1 | Seller Web UI → KONG → Listing | HTTP | POST /listings {sellerId, title, description, imageUrl, startingPrice, startTime, endTime} |
| 2 | Listing → listing_db | — | Save listing with status = SCHEDULED |
| 3 | Listing → market.timers | AMQP | Publish auction.start {listingId} with TTL = time until startTime (TIMER 1) |
| 4 | Listing → market.events | AMQP | Publish listing.scheduled {listingId, sellerId}, Routing Key: listing.scheduled |
| 5 | Listing → KONG → Seller Web UI | HTTP | Return 201 Created |

**Steps 6-8 happen in background. Seller does NOT wait.**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 6 | market.events → Dispatch Notification | AMQP | Consume listing.scheduled, [BKEY] listing.*, Queue: notif.listing |
| 7 | Dispatch Notification → User | HTTP | GET /users/{sellerId} → returns seller email |
| 8 | Dispatch Notification → Notification | HTTP | POST /notifications → email seller "Auction scheduled for [startTime]!" |

**DLQ mechanism (not a step):** market.timers configured with x-dead-letter-exchange → market.dlq. TTL expires, message auto-routed. No consumer between queues. Built-in RabbitMQ behavior.

**Part 2: Timer 1 Fires (Auction Goes Live)**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 9 | market.dlq → Listing | AMQP | Consume auction.start {listingId} from DLQ |
| 10 | Listing → listing_db | — | Update listing status → ACTIVE |
| 11 | Listing → market.timers | AMQP | Publish auction.close {listingId} with TTL = endTime - startTime (TIMER 2) |
| 12 | Listing → market.events | AMQP | Publish listing.active {listingId, sellerId}, Routing Key: listing.active |

**Steps 13-15 happen in background.**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 13 | market.events → Dispatch Notification | AMQP | Consume listing.active, [BKEY] listing.*, Queue: notif.listing |
| 14 | Dispatch Notification → User | HTTP | GET /users/{sellerId} → returns seller email |
| 15 | Dispatch Notification → Notification | HTTP | POST /notifications → email seller "Your auction is now LIVE!" |

**End:** US1 ends here. Timer 2 is ticking. US2 Diagram 2 begins when auction.close fires from the DLQ.

---

### US2 Diagram 1: Buyer Places a Bid

**Pattern:** Event-driven with WebSocket (BTL) + KONG rate limiting (BTL)

**Boxes:** Buyer Web UI, KONG API Gateway (rate limiting: POST /bids), Bid, market.events (Topic Exchange), WebSocket Channel (Real-Time Update), Dispatch Notification, User, Notification (OutSystems)

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 1 | Buyer Web UI → KONG → Bid | HTTP | POST /bids {listingId, buyerId, amount}. KONG rate limited (e.g. 5 bids/min per user) |
| 2 | Bid → KONG → Buyer Web UI | HTTP | Return 201 Created |
| 3 | Bid → market.events | AMQP | Publish bid.placed {listingId, bidId, buyerId, amount, prevHighestBuyerId}, Routing Key: bid.placed |

**Background: WebSocket (not numbered)**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| BG | market.events → WebSocket Channel → Buyer Web UI | AMQP→WS | Consume bid.placed, push new highest bid to all connected viewers. [BKEY] bid.placed, Queue: ws.bid_updates |

**Background: Outbid Notification**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 4 | market.events → Dispatch Notification | AMQP | Consume bid.placed, [BKEY] bid.placed, Queue: notif.bid |
| 5 | Dispatch Notification | — | Check if prevHighestBuyerId is null. If null (first bid) → stop, no one to notify |
| 6 | Dispatch Notification → User | HTTP | GET /users/{prevHighestBuyerId} → returns outbid buyer email |
| 7 | Dispatch Notification → Notification | HTTP | POST /notifications → email "You've been outbid!" |

**End:** Diagram 1 ends here. Can repeat many times. US2 Diagram 2 begins when auction.close fires from DLQ (Timer 2 from US1).

---

### US2 Diagram 2: Close Auction (Orchestration)

**Pattern:** Orchestration + Saga (cascade loop)

**Boxes:** market.timers, market.dlq, Close Auction, Listing, Bid, User, Payment, Stripe, market.events (Topic Exchange), Dispatch Notification, Notification

**DLQ annotation (not a step):** market.timers → market.dlq via x-dead-letter-exchange. TTL expires, auto-routed.

**Main flow (black arrows):**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 1 | market.dlq → Close Auction | AMQP | Consume auction.close {listingId} from DLQ |
| 2 | Close Auction → Listing | HTTP | PATCH /listings/{id}/status → CLOSED_PENDING_PAYMENT |
| 3 | Close Auction → Bid | HTTP | POST /auctions/{id}/close → returns rankedBids[] |

**Payment cascade loop (red arrows, repeats for each bidder highest-first):**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 4 | Close Auction → User | HTTP | GET /users/{buyerId} → returns stripe_id |
| 5 | Close Auction → Payment | HTTP | POST /payments/charge {listingId, buyerId, amount, stripeId, listingType: "AUCTION"} |
| 6 | Payment → Stripe | HTTP | Charge via Stripe → returns result |
| 7 | Payment → Close Auction | HTTP | Returns result (success/failed) — for cascade loop decision |
| 8 | Payment → market.events | AMQP | Publish payment.success OR payment.failed, Routing Key: payment.success / payment.failed |

**Loop logic:** If step 7 returned FAILED → back to step 4 with next bidder from rankedBids[]. If SUCCESS → loop breaks.

**Post-payment subscriber reactions (shared with US3 D3):** Payment events go into market.events. Listing reacts to payment.success (marks SOLD). Dispatch Notification sends emails. See US3 Diagram 3 for the subscriber flow — it's identical for both scenarios.

**Edge case: All bidders fail (blue arrows):**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 9 | Close Auction → Listing | HTTP | PATCH /listings/{id}/status → FAILED_NO_ELIGIBLE_BIDDER |
| 10 | Close Auction → market.events | AMQP | Publish auction.no_eligible_bidders {listingId, sellerId}, Routing Key: auction.no_eligible_bidders |
| 11 | market.events → Dispatch Notification | AMQP | Consume auction.no_eligible_bidders, [BKEY] auction.no_eligible_bidders, Queue: notif.auction |
| 12 | Dispatch Notification → User | HTTP | GET /users/{sellerId} → get seller email |
| 13 | Dispatch Notification → Notification | HTTP | POST /notifications "No eligible bidders" |

---

### US3 Diagram 1: Offer Creation & Direct Acceptance

**Pattern:** Choreography

**Boxes:** Buyer Web UI, Seller Web UI, KONG API Gateway, Listing, Offer, market.events (Topic Exchange), Dispatch Notification, User, Notification

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 1 | Buyer Web UI → KONG → Listing | HTTP | GET /listings (browse listings) |
| 2 | Buyer Web UI → KONG → Offer | HTTP | POST /offers {listingId, buyerId, sellerId, amount} |
| 3 | Offer → market.events | AMQP | Publish offer.created {offerId, listingId, buyerId, sellerId, amount}, Routing Key: offer.created |
| 4 | market.events → Dispatch Notification | AMQP | Consume offer.created, [BKEY] offer.*, Queue: notif.offer |
| 5 | Dispatch Notification → User | HTTP | GET /users/{sellerId} → get seller email |
| 6 | Dispatch Notification → Notification | HTTP | POST /notifications → email seller "You received an offer of $X" |
| 7 | Seller Web UI → KONG → Offer | HTTP | POST /offers/{id}/accept |
| 8 | Offer → market.events | AMQP | Publish offer.accepted {offerId, listingId, buyerId, sellerId, amount}, Routing Key: offer.accepted |
| 9 | market.events → Dispatch Notification | AMQP | Consume offer.accepted, [BKEY] offer.*, Queue: notif.offer |
| 10 | Dispatch Notification → User | HTTP | GET /users/{buyerId} → get buyer email |
| 11 | Dispatch Notification → Notification | HTTP | POST /notifications → email buyer "Your offer has been accepted!" |

**End:** Payment flow for offer.accepted is in Diagram 3.

---

### US3 Diagram 2: Counter Offer & Negotiation

**Pattern:** Choreography

**Starting point:** Offer exists with status PENDING (from Diagram 1)

**Boxes:** Seller Web UI, Buyer Web UI, KONG API Gateway, Offer, market.events (Topic Exchange), Dispatch Notification, User, Notification

**Counter offer flow (black arrows):**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 1 | Seller Web UI → KONG → Offer | HTTP | PATCH /offers/{id} {amount: counterAmount} |
| 2 | Offer → market.events | AMQP | Publish offer.countered {offerId, listingId, buyerId, sellerId, amount}, Routing Key: offer.countered |
| 3 | market.events → Dispatch Notification | AMQP | Consume offer.countered, [BKEY] offer.*, Queue: notif.offer |
| 4 | Dispatch Notification → User | HTTP | GET /users/{buyerId} → get buyer email |
| 5 | Dispatch Notification → Notification | HTTP | POST /notifications → email buyer "Seller countered at $X" |

**Accept branch (green arrows):**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 6a | Buyer Web UI → KONG → Offer | HTTP | POST /offers/{id}/accept |
| 7a | Offer → market.events | AMQP | Publish offer.accepted {offerId, listingId, buyerId, sellerId, amount}, Routing Key: offer.accepted |
| 8a | market.events → Dispatch Notification | AMQP | Consume offer.accepted, [BKEY] offer.*, Queue: notif.offer |
| 9a | Dispatch Notification → User | HTTP | GET /users/{sellerId} → get seller email |
| 10a | Dispatch Notification → Notification | HTTP | POST /notifications → email seller "Buyer accepted your counter!" |

**Reject branch (red arrows):**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 6b | Buyer Web UI → KONG → Offer | HTTP | POST /offers/{id}/reject |
| 7b | Offer → market.events | AMQP | Publish offer.rejected {offerId, listingId, buyerId, sellerId}, Routing Key: offer.rejected |
| 8b | market.events → Dispatch Notification | AMQP | Consume offer.rejected, [BKEY] offer.*, Queue: notif.offer |
| 9b | Dispatch Notification → User | HTTP | GET /users/{sellerId} → get seller email |
| 10b | Dispatch Notification → Notification | HTTP | POST /notifications → email seller "Buyer rejected your counter" |

**End:** Payment flow for offer.accepted is in Diagram 3. Flow ends here for offer.rejected.

---

### US3 Diagram 3: Payment Choreography

**Pattern:** Choreography — this is the showcase diagram for the choreography pattern

**Starting point:** offer.accepted is already in RabbitMQ (from Diagram 1 or Diagram 2)

**Boxes:** Process Payment, User, Payment, Stripe, market.events (Topic Exchange), Listing, Offer, Dispatch Notification, Notification

**Core payment flow (black arrows):**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 1 | market.events → Process Payment | AMQP | Consume offer.accepted, [BKEY] offer.accepted, Queue: process_payment.offer_accepted |
| 2 | Process Payment → User | HTTP | GET /users/{buyerId} → returns stripe_id |
| 3 | Process Payment → Payment | HTTP | POST /payments/charge {listingId, buyerId, amount, stripeId, listingType: "FIXED"} |
| 4 | Payment → Stripe | HTTP | Charge via Stripe → returns result |
| 5a | Payment → market.events | AMQP | Publish payment.success {listingId, buyerId, amount, listingType, offerId}, Routing Key: payment.success |
| 5b | Payment → market.events | AMQP | Publish payment.failed {listingId, buyerId, listingType, offerId}, Routing Key: payment.failed |

**Success path (green arrows) — services react in parallel, no coordinator:**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 6a | market.events → Listing | AMQP | Consume payment.success, [BKEY] payment.success, Queue: listing.payment → set status SOLD |
| 7a | market.events → Dispatch Notification | AMQP | Consume payment.success (in parallel with 6a), [BKEY] payment.*, Queue: notif.payment |
| 8a | Dispatch Notification → User | HTTP | GET /users/{buyerId + sellerId} → get emails |
| 9a | Dispatch Notification → Notification | HTTP | POST /notifications → email both "Payment confirmed! Transaction complete" |

**Failure path (red arrows) — services react in parallel, no coordinator:**

| Step | From → To | Protocol | Description |
|------|-----------|----------|-------------|
| 6b | market.events → Offer | AMQP | Consume payment.failed, [BKEY] payment.failed, Queue: offer.payment_failed → set status CANCELLED |
| 7b | market.events → Dispatch Notification | AMQP | Consume payment.failed (in parallel with 6b), [BKEY] payment.*, Queue: notif.payment |
| 8b | Dispatch Notification → User | HTTP | GET /users/{buyerId + sellerId} → get emails |
| 9b | Dispatch Notification → Notification | HTTP | POST /notifications → email both "Payment failed, offer cancelled" |

**Key point:** After step 5, nobody coordinates. Listing, Offer, and Dispatch Notification all react independently to payment events. This is choreography. This same post-payment flow applies to US2 as well (Listing marks SOLD on payment.success, Dispatch Notification sends emails).

---

## All Services

### Atomic Services (Flask + MySQL)

| Service | Port | Database | Used In |
|---------|------|----------|---------|
| User | 5004 | user_db | US1, US2, US3 — provides email and stripe_id |
| Listing | 5001 | listing_db | US1, US2, US3 — listings, status management, DLQ timers, reacts to payment.success |
| Bid | 5002 | bid_db | US2 — bids on auction listings |
| Offer | 5003 | offer_db | US3 — negotiation lifecycle, reacts to payment.failed |
| Payment | 5005 | payment_db | US2, US3 — Stripe charges, always publishes payment events |
| Notification (OutSystems) | — | — | US1, US2, US3 — receives HTTP from Dispatch Notification, sends emails |

### Composite Services (Flask, no database)

| Service | Port | Used In | One Job |
|---------|------|---------|---------|
| Close Auction | 5006 | US2 | Orchestrate auction close + payment cascade loop |
| Process Payment | 5007 | US3 | Consume offer.accepted, call User for stripe_id, call Payment to charge |
| Dispatch Notification | 5008 | US1, US2, US3 | Subscribe to events, look up email from User, call Notification to send |

### Infrastructure

| Component | Purpose |
|-----------|---------|
| KONG API Gateway | Routing + rate limiting on POST /bids (BTL) |
| RabbitMQ | Topic exchange (market.events) + DLQ/TTL timers (market.timers/dlq) (BTL) |
| Docker + Docker Compose | Containerization, runs locally |
| Stripe | External payment API (test mode) |
| WebSocket Channel | Separate from Bid, subscribes to bid.placed, pushes real-time updates to browsers (BTL) |

---

## Database Schemas

### user_db → users
| Column | Type | Notes |
|--------|------|-------|
| user_id | INT | PK, auto-increment |
| email | VARCHAR(255) | |
| name | VARCHAR(255) | |
| stripe_id | VARCHAR(255) | Stripe customer ID |
| created_at | TIMESTAMP | |

### listing_db → listings
| Column | Type | Notes |
|--------|------|-------|
| listing_id | INT | PK, auto-increment |
| seller_id | INT | References user by value (no FK) |
| title | VARCHAR(255) | |
| description | TEXT | |
| image_url | VARCHAR(500) | |
| listing_type | VARCHAR(20) | AUCTION or FIXED |
| start_price | DECIMAL(10,2) | |
| start_time | DATETIME | Auction only, nullable |
| end_time | DATETIME | Auction only, nullable |
| status | VARCHAR(50) | SCHEDULED, ACTIVE, CLOSED_PENDING_PAYMENT, SOLD, FAILED_NO_ELIGIBLE_BIDDER |
| winning_buyer_id | INT | Nullable, set on auction close |
| created_at | TIMESTAMP | |

### bid_db → bids
| Column | Type | Notes |
|--------|------|-------|
| bid_id | INT | PK, auto-increment |
| listing_id | INT | |
| buyer_id | INT | |
| amount | DECIMAL(10,2) | |
| created_at | TIMESTAMP | |

### offer_db → offers
| Column | Type | Notes |
|--------|------|-------|
| offer_id | INT | PK, auto-increment |
| listing_id | INT | |
| buyer_id | INT | |
| seller_id | INT | |
| amount | DECIMAL(10,2) | Current price, updated on counter |
| status | VARCHAR(20) | PENDING, COUNTERED, ACCEPTED, REJECTED, CANCELLED |
| turn | VARCHAR(10) | SELLER or BUYER |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### payment_db → payments
| Column | Type | Notes |
|--------|------|-------|
| payment_id | INT | PK, auto-increment |
| listing_id | INT | |
| buyer_id | INT | |
| amount | DECIMAL(10,2) | |
| stripe_charge_id | VARCHAR(255) | From Stripe |
| idempotency_key | VARCHAR(255) | Prevent double charges |
| status | VARCHAR(20) | SUCCESS or FAILED |
| created_at | TIMESTAMP | |

---

## API Endpoints

### User (port 5004)
| Method | Path | Description |
|--------|------|-------------|
| POST | /users | Create user |
| GET | /users/{userId} | Get user details (email, name, stripe_id) |

### Listing (port 5001)
| Method | Path | Description |
|--------|------|-------------|
| POST | /listings | Create listing. AUCTION → SCHEDULED + Timer 1. FIXED → ACTIVE |
| GET | /listings | Browse all listings |
| GET | /listings/{id} | Get listing details |
| PATCH | /listings/{id}/status | Update listing status |

AMQP publishes: listing.scheduled, listing.active (to market.events). auction.start, auction.close (to market.timers with TTL).
AMQP consumes: auction.start from market.dlq. payment.success from market.events ([BKEY] payment.success, Queue: listing.payment) → marks SOLD.

### Bid (port 5002)
| Method | Path | Description |
|--------|------|-------------|
| POST | /bids | Place a bid |
| GET | /bids?listingId={id} | Get all bids for listing |
| GET | /bids/highest/{listingId} | Get current highest bid |
| POST | /auctions/{id}/close | Get ranked bids sorted DESC |

AMQP publishes: bid.placed (to market.events).

### Offer (port 5003)
| Method | Path | Description |
|--------|------|-------------|
| POST | /offers | Make an offer |
| PATCH | /offers/{id} | Counter an offer (seller) |
| POST | /offers/{id}/accept | Accept offer or counter |
| POST | /offers/{id}/reject | Reject counter (buyer only) |

AMQP publishes: offer.created, offer.countered, offer.accepted, offer.rejected (all to market.events).
AMQP consumes: payment.failed from market.events ([BKEY] payment.failed, Queue: offer.payment_failed) → marks offer CANCELLED (only when listingType=FIXED).

### Payment (port 5005)
| Method | Path | Description |
|--------|------|-------------|
| POST | /payments/charge | Charge via Stripe. Returns HTTP result to caller AND publishes to RabbitMQ |

AMQP publishes: payment.success, payment.failed (to market.events). Payloads always include listingType field for downstream filtering.

### Notification / OutSystems
| Method | Path | Description |
|--------|------|-------------|
| POST | /notifications | Send email notification. Receives {recipientEmail, subject, body} |

---

## RabbitMQ Architecture

### Exchanges
| Exchange | Type | Purpose |
|----------|------|---------|
| market.events | Topic | All business events with routing keys |
| (default) | Direct | DLQ routing from market.timers → market.dlq |

### DLQ/TTL Timer Mechanism
market.timers queue configured with x-dead-letter-exchange pointing to market.dlq. Messages published with per-message TTL sit in market.timers (no consumers). When TTL expires, RabbitMQ automatically routes them to market.dlq. No consumer between queues. Built-in RabbitMQ behavior.

### Event Payloads
| Event | Routing Key | Payload |
|-------|-------------|---------|
| listing.scheduled | listing.scheduled | {listingId, sellerId} |
| listing.active | listing.active | {listingId, sellerId} |
| bid.placed | bid.placed | {listingId, bidId, buyerId, amount, prevHighestBuyerId} |
| offer.created | offer.created | {offerId, listingId, buyerId, sellerId, amount} |
| offer.countered | offer.countered | {offerId, listingId, buyerId, sellerId, amount} |
| offer.accepted | offer.accepted | {offerId, listingId, buyerId, sellerId, amount} |
| offer.rejected | offer.rejected | {offerId, listingId, buyerId, sellerId} |
| payment.success | payment.success | {listingId, buyerId, amount, listingType, offerId} |
| payment.failed | payment.failed | {listingId, buyerId, listingType, offerId} |
| auction.no_eligible_bidders | auction.no_eligible_bidders | {listingId, sellerId} |
| auction.start | — (direct to market.timers) | {listingId, type: "auction.start"} |
| auction.close | — (direct to market.timers) | {listingId, type: "auction.close"} |

### Queues and Bindings
| Queue | Bound To | [BKEY] | Consumer |
|-------|----------|--------|----------|
| market.timers | — (direct publish) | — | None (TTL holding, x-dead-letter-exchange → market.dlq) |
| market.dlq | — (dead-letter target) | — | Listing (auction.start), Close Auction (auction.close) |
| notif.listing | market.events | listing.* | Dispatch Notification |
| notif.bid | market.events | bid.placed | Dispatch Notification |
| notif.offer | market.events | offer.* | Dispatch Notification |
| notif.payment | market.events | payment.* | Dispatch Notification |
| notif.auction | market.events | auction.no_eligible_bidders | Dispatch Notification |
| ws.bid_updates | market.events | bid.placed | WebSocket Channel |
| process_payment.offer_accepted | market.events | offer.accepted | Process Payment |
| listing.payment | market.events | payment.success | Listing (marks SOLD) |
| offer.payment_failed | market.events | payment.failed | Offer (marks CANCELLED) |

---

## Listing Statuses
| Status | Meaning | Set By |
|--------|---------|--------|
| SCHEDULED | Auction created, waiting for startTime | Listing (on creation) |
| ACTIVE | Live, accepting bids/offers | Listing (Timer 1 DLQ fire) |
| CLOSED_PENDING_PAYMENT | Auction ended, payment cascade in progress | Close Auction (HTTP) |
| SOLD | Payment succeeded | Listing (reacts to payment.success via AMQP) |
| FAILED_NO_ELIGIBLE_BIDDER | All bidders' payments failed | Close Auction (HTTP) |

---

## Beyond the Labs (BTL)

| BTL | Where | Justification |
|-----|-------|---------------|
| DLQ/TTL Timers | US1 | Two chained timers for auction start and close. Repurposes DLQ from error handling to precision timing. Event-driven (no polling), decoupled from service code. Server-side triggers needed for backend actions even when no user is online |
| WebSocket | US2 D1 | Real-time bid updates pushed to all viewers via separate WebSocket Channel. Critical for fair bidding in final seconds. Persistent push instead of polling |
| KONG Rate Limiting | US2 D1 | Rate limits POST /bids to prevent bot sniping. Gateway-level enforcement (e.g. 5 bids/min per user) |

---

## Tech Stack
| Component | Technology |
|-----------|-----------|
| Atomic Services | Python Flask + MySQL |
| Composite Services | Python Flask (no DB) |
| OutSystems Service | Notification |
| Message Broker | RabbitMQ |
| API Gateway | KONG |
| External API | Stripe (test mode) |
| Frontend | HTML, CSS, Bootstrap |
| Containerization | Docker + Docker Compose (runs locally) |

---

## Service Reuse (required by project)
- **Listing:** all 3 scenarios (create in US1, CLOSED_PENDING_PAYMENT/FAILED in US2, SOLD via payment.success in US2+US3)
- **User:** all 3 scenarios (email lookups via Dispatch Notification, stripe_id lookups via Close Auction and Process Payment)
- **Payment:** US2 and US3 (called by Close Auction in US2, called by Process Payment in US3. Always publishes payment events)
- **Notification (OutSystems):** all 3 scenarios (called by Dispatch Notification via HTTP)
- **Dispatch Notification:** all 3 scenarios (subscribes to 10 event types, enriches with email from User, calls Notification)
