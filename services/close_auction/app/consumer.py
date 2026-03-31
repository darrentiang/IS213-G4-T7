"""
Close Auction consumer — US2 Diagram 2.
Consumes auction.close from market.dlq.close, then orchestrates:
  1. PATCH Listing → CLOSED_PENDING_PAYMENT
  2. POST Bid → get ranked bids
  3. Loop bidders highest-first: GET User for stripeId → POST Payment charge
     - SUCCESS → break
     - FAILED → try next bidder
  4. All fail → PATCH Listing → FAILED_NO_ELIGIBLE_BIDDER
     + publish auction.no_eligible_bidders
"""

import json
import time
import requests
from os import environ

from app.amqp_lib import connect, publish_message
from app import amqp_setup

LISTING_SERVICE_URL = environ.get("LISTING_SERVICE_URL", "http://listing:5001")
BID_SERVICE_URL = environ.get("BID_SERVICE_URL", "http://bid:5002")
USER_SERVICE_URL = environ.get("USER_SERVICE_URL", "http://user:5004")
PAYMENT_SERVICE_URL = environ.get("PAYMENT_SERVICE_URL", "http://payment:5005")

amqp_host = environ.get("RABBITMQ_HOST", "localhost")
amqp_port = int(environ.get("RABBITMQ_PORT", 5672))


def handle_auction_close(channel, method, properties, body):
    """Called when auction.close TTL expires and lands in market.dlq.close."""
    message = json.loads(body)
    listing_id = message.get("listingId")
    print(f"[auction.close] Received: listing {listing_id}")

    # Step 2: PATCH listing → CLOSED_PENDING_PAYMENT
    try:
        resp = requests.patch(
            f"{LISTING_SERVICE_URL}/listings/{listing_id}/status",
            json={"status": "CLOSED_PENDING_PAYMENT"}
        )
        resp.raise_for_status()
        listing_data = resp.json().get("data", {})
        seller_id = listing_data.get("sellerId")
        print(f"[auction.close] Listing {listing_id} → CLOSED_PENDING_PAYMENT")
    except Exception as e:
        print(f"[auction.close] Failed to update listing {listing_id}: {e}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    # Step 3: POST /auctions/{id}/close → ranked bids
    try:
        resp = requests.post(f"{BID_SERVICE_URL}/auctions/{listing_id}/close")
        resp.raise_for_status()
        ranked_bids = resp.json().get("data", {}).get("bids", [])
        print(f"[auction.close] Got {len(ranked_bids)} ranked bids")
    except Exception as e:
        print(f"[auction.close] Failed to get ranked bids: {e}")
        # No bids or bid service error — mark as failed
        _mark_failed(listing_id, seller_id, channel)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    if not ranked_bids:
        print(f"[auction.close] No bids for listing {listing_id}")
        _mark_failed(listing_id, seller_id, channel)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    # Steps 4-7: Payment cascade loop — try each bidder highest-first
    payment_succeeded = False

    for i, bid in enumerate(ranked_bids):
        buyer_id = bid.get("buyerId")
        amount = bid.get("amount")
        print(f"[auction.close] Trying bidder {i+1}/{len(ranked_bids)}: user {buyer_id}, ${amount}")

        # Step 4: GET user → stripeId
        try:
            resp = requests.get(f"{USER_SERVICE_URL}/users/{buyer_id}")
            resp.raise_for_status()
            user_data = resp.json().get("data", {})
            stripe_id = user_data.get("stripeId")
        except Exception as e:
            print(f"[auction.close] Failed to get user {buyer_id}: {e}")
            continue

        if not stripe_id:
            print(f"[auction.close] No stripeId for user {buyer_id}, skipping")
            continue

        # Step 5: POST payment charge
        try:
            resp = requests.post(
                f"{PAYMENT_SERVICE_URL}/payments/charge",
                json={
                    "listingId": listing_id,
                    "buyerId": buyer_id,
                    "amount": amount,
                    "stripeId": stripe_id,
                    "listingType": "AUCTION",
                    "idempotencyKey": f"auction_{listing_id}_{buyer_id}"
                }
            )
            resp.raise_for_status()
            payment_data = resp.json().get("data", {})
            payment_status = payment_data.get("status")
        except Exception as e:
            print(f"[auction.close] Payment call failed for user {buyer_id}: {e}")
            continue

        # Step 7: Check result
        if payment_status == "SUCCESS":
            print(f"[auction.close] Payment SUCCESS for user {buyer_id}")
            # listing.sold consumer handles marking SOLD + winningBuyerId
            # via the payment.success AMQP event — no PATCH needed here
            payment_succeeded = True
            break
        else:
            print(f"[auction.close] Payment FAILED for user {buyer_id}, trying next bidder")

    # Step 9-10: All bidders failed
    if not payment_succeeded:
        _mark_failed(listing_id, seller_id, channel)

    channel.basic_ack(delivery_tag=method.delivery_tag)
    print(f"[auction.close] Done processing listing {listing_id}")


def _mark_failed(listing_id, seller_id, channel):
    """Mark listing as FAILED_NO_ELIGIBLE_BIDDER and publish event."""
    # Step 9: PATCH listing → FAILED_NO_ELIGIBLE_BIDDER
    try:
        requests.patch(
            f"{LISTING_SERVICE_URL}/listings/{listing_id}/status",
            json={"status": "FAILED_NO_ELIGIBLE_BIDDER"}
        )
        print(f"[auction.close] Listing {listing_id} → FAILED_NO_ELIGIBLE_BIDDER")
    except Exception as e:
        print(f"[auction.close] Failed to mark listing as failed: {e}")

    # Step 10: Publish auction.no_eligible_bidders
    try:
        publish_message(channel, "market.events", "auction.no_eligible_bidders", {
            "listingId": listing_id,
            "sellerId": seller_id
        })
    except Exception as e:
        print(f"[auction.close] Failed to publish no_eligible_bidders: {e}")


def start():
    """Connect to RabbitMQ and start consuming from market.dlq.close.
    Auto-reconnects if the connection drops."""
    while True:
        try:
            connection, channel = connect(amqp_host, amqp_port)
            amqp_setup.setup(channel)

            print("Close Auction is listening on market.dlq.close. Waiting for messages...")
            channel.basic_consume(
                queue="market.dlq.close",
                on_message_callback=handle_auction_close,
                auto_ack=False
            )
            channel.start_consuming()
        except Exception as e:
            print(f"Consumer connection lost: {e}, reconnecting in 2s...")
            time.sleep(2)
