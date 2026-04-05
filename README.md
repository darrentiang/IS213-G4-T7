# BidBoard — Peer-to-Peer Marketplace

IS213 Enterprise Solution Development | Section G4, Team 7

## Video Demo Link

https://youtu.be/a23008k1u0Y

## Prerequisites

- Docker Desktop installed and running
- Git
- deck CLI (optional, for KONG configuration): https://github.com/kong/deck/releases

## Quick Start

### 1. Clone the repository

```
git clone https://github.com/darrentiang/IS213-G4-T7.git
cd IS213-G4-T7
```

### 2. Create the .env file

Create a `.env` file in the project root with the following:

```
STRIPE_SECRET_KEY=<stripe_secret_key>
```

This file is gitignored and must be created manually. The Stripe secret key is required for the Payment Service to charge buyers via Stripe PaymentIntents API.

### 3. Start all services

For local development (builds from source):

```
docker compose -f docker-compose-dev.yml up --build -d
```

Wait for all containers to be healthy. This may take 1 to 2 minutes on first build.

### 4. Configure KONG API Gateway

After all containers are running, sync the KONG configuration:

```
deck gateway sync kong/kong.yaml --kong-addr http://localhost:8001
```

Alternatively, if deck is not installed:

```
bash kong/setup.sh
```

KONG runs in DB mode with PostgreSQL. Configuration persists across container restarts. You only need to re-run the sync after a `docker compose down -v` (which wipes volumes).

### 5. Access the application

| Component | URL |
|-----------|-----|
| Seller UI | http://localhost:8080/seller/ |
| Buyer UI | http://localhost:8080/buyer/ |
| KONG API Gateway | http://localhost:8000 |
| RabbitMQ Management | http://localhost:15672 (guest / guest) |
| Grafana Dashboard | http://localhost:3100 (admin / admin) |

### Pre-seeded Users

| User | Role | Stripe Behavior |
|------|------|-----------------|
| Alice Tan (user 1) | Seller | Not charged |
| Bob Lim (user 2) | Buyer | Payment always succeeds |
| Charlie Ng (user 3) | Buyer | Payment always fails on charge |

## Stopping and Resetting

Stop containers (preserves data):
```
docker compose -f docker-compose-dev.yml down
```

Stop and wipe all data (databases, RabbitMQ, KONG config):
```
docker compose -f docker-compose-dev.yml down -v
```

After a volume wipe, rebuild and re-run KONG setup:
```
docker compose -f docker-compose-dev.yml up --build -d
deck gateway sync kong/kong.yaml --kong-addr http://localhost:8001
```

## Architecture Overview

### Atomic Services (Flask + MySQL)

| Service | Port | Database |
|---------|------|----------|
| User | 5004 | user_db |
| Listing | 5001 | listing_db |
| Bid | 5002 | bid_db |
| Offer | 5003 | offer_db |
| Payment | 5005 | payment_db |
| Notification | External (OutSystems) | None |

### Composite Services (no database)

| Service | Port | Pattern |
|---------|------|---------|
| Close Auction | 5006 | AMQP consumer, orchestration |
| Process Payment | 5007 | AMQP consumer, choreography trigger |
| Dispatch Notification | 5008 | AMQP consumer, event-based notifications |

### Infrastructure

| Component | Port | Purpose |
|-----------|------|---------|
| KONG API Gateway | 8000, 8001, 8002 | Request routing, rate limiting |
| RabbitMQ | 5672, 15672 | Message broker, topic exchange, DLQ/TTL timers |
| nginx | 8080 | Static frontend serving |
| WebSocket Server | 6000 | Real-time bid updates |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3100 (dev), 13000 (prod) | API traffic monitoring |

### External Services

| Service | Purpose |
|---------|---------|
| Stripe | Payment processing (sandbox, PaymentIntents API) |
| SendGrid | Transactional email via OutSystems Notification Service |

## Project Structure

```
IS213-G4-T7/
  services/
    user/                  # User Service
    listing/               # Listing Service (DLQ timers, payment consumer)
    bid/                   # Bid Service
    offer/                 # Offer Service (payment.failed consumer)
    payment/               # Payment Service (Stripe wrapper)
    close_auction/         # Close Auction composite
    process_payment/       # Process Payment composite
    dispatch_notification/ # Dispatch Notification composite
    ws_server/             # WebSocket Server
  frontend/
    buyer/                 # Buyer UI pages
    seller/                # Seller UI pages
    shared/                # Shared CSS, JS, config
    nginx/                 # nginx configuration
  kong/
    kong.yaml              # KONG declarative configuration (used by deck)
    setup.sh               # KONG Admin API setup script (alternative to deck)
    prometheus.yml         # Prometheus scrape configuration
  docker-compose.yml       # Production (pulls from Docker Hub)
  docker-compose-dev.yml   # Local development (builds from source)
  .env                     # Stripe secret key (gitignored, create manually)
```