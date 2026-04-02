#!/bin/bash
# BidBoard — Kong setup script
# Registers all Services, Routes, and Plugins via the Admin API.
# Run this ONCE after `docker-compose up -d`, when Kong is healthy.
#
# Usage:
#   ./kong/setup-kong.sh
#   ./kong/setup-kong.sh http://your-azure-vm-ip:8001   (override admin URL)

set -e

ADMIN="${1:-http://localhost:8001}"

# ── Wait for Kong ────────────────────────────────────────────────────────────
echo "Waiting for Kong Admin API at $ADMIN ..."
until curl -sf "$ADMIN/status" > /dev/null 2>&1; do
  sleep 3
done
echo "Kong is ready."
echo ""

# ── Helpers ──────────────────────────────────────────────────────────────────
upsert_service() {
  local name=$1 upstream_url=$2
  curl -sf -o /dev/null -X PUT "$ADMIN/services/$name" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$upstream_url\"}"
  echo "[service] $name  →  $upstream_url"
}

add_route() {
  # add_route <service-name> <route-name> <path> [method,method,...]
  local service=$1 route_name=$2 path=$3
  shift 3
  local methods=("$@")   # remaining args are HTTP methods

  local payload="{\"name\": \"$route_name\", \"paths\": [\"$path\"], \"strip_path\": false"

  if [ ${#methods[@]} -gt 0 ]; then
    local methods_json
    methods_json=$(printf '"%s",' "${methods[@]}")
    methods_json="[${methods_json%,}]"
    payload="$payload, \"methods\": $methods_json"
  fi

  payload="$payload}"

  # Use PUT so re-running this script is idempotent
  curl -sf -o /dev/null -X PUT "$ADMIN/services/$service/routes/$route_name" \
    -H "Content-Type: application/json" \
    -d "$payload"
  echo "  [route] ${methods[*]:-ANY}  $path"
}

add_plugin_global() {
  local name=$1 config=$2
  curl -sf -o /dev/null -X POST "$ADMIN/plugins" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$name\", \"config\": $config}"
  echo "[plugin] $name (global)"
}

add_plugin_route() {
  local route_name=$1 plugin_name=$2 config=$3
  local route_id
  route_id=$(curl -sf "$ADMIN/routes/$route_name" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
  curl -sf -o /dev/null -X POST "$ADMIN/routes/$route_id/plugins" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$plugin_name\", \"config\": $config}"
  echo "[plugin] $plugin_name on route $route_name"
}

# ═══════════════════════════════════════════════════════════════════════════════
echo "── Registering Services ──────────────────────────────────────────────────"

upsert_service "listing-svc"  "http://listing:5001"
upsert_service "bid-svc"      "http://bid:5002"
upsert_service "offer-svc"    "http://offer:5003"
upsert_service "user-svc"     "http://user:5004"
upsert_service "payment-svc"  "http://payment:5005"

# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "── Registering Routes ────────────────────────────────────────────────────"

# ── Listing Service (port 5001) ───────────────────────────────────────────────
# GET  /listings          → get all listings
# POST /listings          → create listing
# GET  /listings/{id}     → get one listing
# PATCH /listings/{id}/status → update status
add_route listing-svc  listing-get-all     "/listings"  "GET"
add_route listing-svc  listing-create      "/listings"  "POST"
add_route listing-svc  listing-by-id       "/listings/" "GET" "PATCH"

# ── Bid Service (port 5002) ───────────────────────────────────────────────────
# GET  /bids              → get all bids (optional ?listingId=)
# POST /bids              → place a bid  [rate limited]
# GET  /bids/highest/{id} → highest bid for a listing
# POST /auctions/{id}/close → get ranked bids (internal, used by close-auction)
add_route bid-svc  bids-get-all      "/bids"             "GET"
add_route bid-svc  bids-place        "/bids"             "POST"
add_route bid-svc  bids-highest      "/bids/highest/"    "GET"
add_route bid-svc  auctions-close    "/auctions/"        "POST"

# ── Offer Service (port 5003) ─────────────────────────────────────────────────
# GET  /offers            → get offers (optional ?listingId= ?buyerId=)
# POST /offers            → create offer
# PATCH /offers/{id}      → counter offer
# POST /offers/{id}/accept → accept offer
# POST /offers/{id}/reject → reject offer
add_route offer-svc  offers-get-all  "/offers"   "GET"
add_route offer-svc  offers-create   "/offers"   "POST"
add_route offer-svc  offers-by-id    "/offers/"  "PATCH" "POST"

# ── User Service (port 5004) ──────────────────────────────────────────────────
# POST /users             → create user
# GET  /users/{id}        → get user by id
add_route user-svc  users-create  "/users"   "POST"
add_route user-svc  users-by-id   "/users/"  "GET"

# ── Payment Service (port 5005) ───────────────────────────────────────────────
# POST /payments/charge   → charge payment
add_route payment-svc  payments-charge  "/payments/"  "POST"

# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "── Registering Plugins ───────────────────────────────────────────────────"

# CORS — global, required because browser at :8080 calls Kong at :8000
# (cross-origin: different port = different origin)
add_plugin_global "cors" '{
  "origins": ["*"],
  "methods": ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
  "headers": ["Content-Type", "Authorization"],
  "max_age": 3600
}'

# Rate limiting on POST /bids (BTL feature)
# 10 requests per minute per IP
add_plugin_route "bids-place" "rate-limiting" '{
  "minute": 10,
  "policy": "local"
}'

# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "── Verification ──────────────────────────────────────────────────────────"
echo "Services registered:"
curl -sf "$ADMIN/services" | python3 -c "
import sys, json
data = json.load(sys.stdin)['data']
for s in data:
    print(f\"  {s['name']:20s} → {s['host']}:{s['port']}\")
"

echo ""
echo "Routes registered:"
curl -sf "$ADMIN/routes" | python3 -c "
import sys, json
data = json.load(sys.stdin)['data']
for r in sorted(data, key=lambda x: x['name']):
    methods = ','.join(r.get('methods') or ['ANY'])
    paths = ','.join(r.get('paths') or [])
    print(f\"  {r['name']:25s}  {methods:20s}  {paths}\")
"

echo ""
echo "Kong setup complete."
echo ""
echo "Test it:"
echo "  curl http://localhost:8000/listings"
echo "  curl http://localhost:8000/users/1"
