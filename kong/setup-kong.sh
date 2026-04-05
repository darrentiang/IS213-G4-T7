#!/bin/bash
# BidBoard — Kong setup script
# Registers all Services, Routes, and Plugins via the Admin API.
# Run this ONCE after `docker-compose up -d`, when Kong is healthy.
# Uses idempotent PUT where possible so re-running is safe.
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

upsert_service "listing"    "http://listing:5001"
upsert_service "bid"        "http://bid:5002"
upsert_service "offer"      "http://offer:5003"
upsert_service "user"       "http://user:5004"
upsert_service "payment"    "http://payment:5005"
upsert_service "ws-server"  "http://ws-server:6000"

# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "── Registering Routes ────────────────────────────────────────────────────"

# ── Listing Service ───────────────────────────────────────────────────────────
add_route listing  listing  "/listings"

# ── Bid Service ───────────────────────────────────────────────────────────────
# Split by method: rate limiting only applies to bid-write
add_route bid  bid-write    "/bids"      "POST" "DELETE" "OPTIONS"
add_route bid  bid-read     "/bids"      "GET" "OPTIONS"
add_route bid  ranked_bids  "/auctions"

# ── Offer Service ─────────────────────────────────────────────────────────────
add_route offer  offer  "/offers"

# ── User Service ──────────────────────────────────────────────────────────────
add_route user  user  "/users"

# ── Payment Service ───────────────────────────────────────────────────────────
add_route payment  payment  "/payments"

# ── WebSocket Server ──────────────────────────────────────────────────────────
add_route ws-server  ws-bids  "/ws"

# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "── Registering Plugins ───────────────────────────────────────────────────"

# CORS — global
add_plugin_global "cors" '{
  "origins": ["*"],
  "methods": ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
  "headers": ["Content-Type", "Accept", "Authorization", "X-Buyer-Id"],
  "credentials": false,
  "preflight_continue": false
}'

# Rate limiting on bid-write route (POST/DELETE /bids)
# 3 requests per minute per buyer (identified by X-Buyer-Id header)
add_plugin_route "bid-write" "rate-limiting" '{
  "minute": 3,
  "limit_by": "header",
  "header_name": "X-Buyer-Id",
  "policy": "local",
  "fault_tolerant": true,
  "error_code": 429,
  "error_message": "API rate limit exceeded"
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
