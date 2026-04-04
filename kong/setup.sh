#!/bin/bash
# Kong Admin API setup script
# Run after docker compose up when Kong DB is fresh (e.g. after docker compose down -v)
# Usage: bash kong/setup.sh

KONG_ADMIN="http://localhost:8001"

echo "Waiting for Kong Admin API..."
until curl -s "$KONG_ADMIN/status" > /dev/null 2>&1; do
    sleep 2
done
echo "Kong Admin API is ready."

# ── Services ──
echo "Creating services..."
curl -s -X POST "$KONG_ADMIN/services" -d "name=listing" -d "url=http://listing:5001/listings" > /dev/null
curl -s -X POST "$KONG_ADMIN/services" -d "name=bid" -d "url=http://bid:5002/bids" > /dev/null
curl -s -X POST "$KONG_ADMIN/services" -d "name=offer" -d "url=http://offer:5003/offers" > /dev/null
curl -s -X POST "$KONG_ADMIN/services" -d "name=payment" -d "url=http://payment:5005/payments" > /dev/null
curl -s -X POST "$KONG_ADMIN/services" -d "name=user" -d "url=http://user:5004/users" > /dev/null
curl -s -X POST "$KONG_ADMIN/services" -d "name=ws-server" -d "url=http://ws-server:6000/" > /dev/null

# ── Routes ──
echo "Creating routes..."
curl -s -X POST "$KONG_ADMIN/services/listing/routes" -d "name=listing" -d "paths[]=/listings" -d "strip_path=true" > /dev/null
curl -s -X POST "$KONG_ADMIN/services/bid/routes" -d "name=bid-write" -d "paths[]=/bids" -d "methods[]=POST" -d "methods[]=OPTIONS" -d "strip_path=true" > /dev/null
curl -s -X POST "$KONG_ADMIN/services/bid/routes" -d "name=bid-read" -d "paths[]=/bids" -d "methods[]=GET" -d "methods[]=OPTIONS" -d "strip_path=true" > /dev/null
curl -s -X POST "$KONG_ADMIN/services/bid/routes" -d "name=ranked_bids" -d "paths[]=/auctions" -d "strip_path=true" > /dev/null
curl -s -X POST "$KONG_ADMIN/services/offer/routes" -d "name=offer" -d "paths[]=/offers" -d "strip_path=true" > /dev/null
curl -s -X POST "$KONG_ADMIN/services/payment/routes" -d "name=payment" -d "paths[]=/payments" -d "strip_path=true" > /dev/null
curl -s -X POST "$KONG_ADMIN/services/user/routes" -d "name=user" -d "paths[]=/users" -d "strip_path=true" > /dev/null
curl -s -X POST "$KONG_ADMIN/services/ws-server/routes" -d "name=ws-bids" -d "paths[]=/ws" -d "strip_path=true" -d "protocols[]=http" -d "protocols[]=https" -d "protocols[]=ws" -d "protocols[]=wss" > /dev/null

# ── Rate limiting on POST /bids only ──
echo "Enabling rate limiting on bid-write route..."
curl -s -X POST "$KONG_ADMIN/routes/bid-write/plugins" \
    -d "name=rate-limiting" \
    -d "config.minute=10" \
    -d "config.limit_by=header" \
    -d "config.header_name=X-Buyer-Id" \
    -d "config.policy=local" \
    -d "config.fault_tolerant=true" \
    -d "config.error_code=429" \
    -d "config.error_message=API rate limit exceeded" > /dev/null

# ── Global CORS plugin ──
echo "Enabling global CORS plugin..."
curl -s -X POST "$KONG_ADMIN/plugins" \
    -d "name=cors" \
    -d "config.origins[]=*" \
    -d "config.methods[]=GET" \
    -d "config.methods[]=POST" \
    -d "config.methods[]=PUT" \
    -d "config.methods[]=PATCH" \
    -d "config.methods[]=DELETE" \
    -d "config.methods[]=OPTIONS" \
    -d "config.headers[]=Content-Type" \
    -d "config.headers[]=Accept" \
    -d "config.headers[]=Authorization" \
    -d "config.credentials=false" \
    -d "config.preflight_continue=false" > /dev/null

echo "Kong setup complete."
echo "Verify: curl http://localhost:8000/listings"
