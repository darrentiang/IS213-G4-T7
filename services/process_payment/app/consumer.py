"""
Process Payment consumer — US3 Diagram 3.
Consumes offer.accepted from market.events, then orchestrates:
  1. GET User → stripeId
  2. POST Payment → charge via Stripe
Payment service handles publishing payment.success/failed.
"""

import json
import time
import requests
from os import environ

from app.amqp_lib import connect
from app import amqp_setup

USER_SERVICE_URL = environ.get("USER_SERVICE_URL", "http://user:5004")
PAYMENT_SERVICE_URL = environ.get("PAYMENT_SERVICE_URL", "http://payment:5005")

amqp_host = environ.get("RABBITMQ_HOST", "localhost")
amqp_port = int(environ.get("RABBITMQ_PORT", 5672))


def handle_offer_accepted(channel, method, properties, body):
    """Called when offer.accepted arrives in process_payment.offer_accepted."""
    message = json.loads(body)
    print(f"[offer.accepted] Received: {message}")

    offer_id = message.get("offerId")
    listing_id = message.get("listingId")
    buyer_id = message.get("buyerId")
    seller_id = message.get("sellerId")
    amount = message.get("amount")

    # Step 1: GET user → stripeId
    try:
        resp = requests.get(f"{USER_SERVICE_URL}/users/{buyer_id}")
        resp.raise_for_status()
        user_data = resp.json().get("data", {})
        stripe_id = user_data.get("stripeId")
    except Exception as e:
        print(f"[offer.accepted] Failed to get user {buyer_id}: {e}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    if not stripe_id:
        print(f"[offer.accepted] No stripeId for user {buyer_id}, skipping")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    # Step 2: POST payment charge
    idempotency_key = f"offer_{offer_id}_{buyer_id}_{int(time.time())}"
    try:
        resp = requests.post(
            f"{PAYMENT_SERVICE_URL}/payments/charge",
            json={
                "listingId": listing_id,
                "buyerId": buyer_id,
                "amount": amount,
                "stripeId": stripe_id,
                "listingType": "FIXED",
                "idempotencyKey": idempotency_key,
                "offerId": offer_id
            }
        )
        resp.raise_for_status()
        payment_data = resp.json().get("data", {})
        payment_status = payment_data.get("status")
        print(f"[offer.accepted] Payment {payment_status} for offer {offer_id}")
    except Exception as e:
        print(f"[offer.accepted] Payment call failed: {e}")

    channel.basic_ack(delivery_tag=method.delivery_tag)
    print(f"[offer.accepted] Done processing offer {offer_id}")


def start():
    """Connect to RabbitMQ and start consuming from process_payment.offer_accepted.
    Auto-reconnects if the connection drops."""
    while True:
        try:
            connection, channel = connect(amqp_host, amqp_port)
            amqp_setup.setup(channel)

            print("Process Payment is listening on process_payment.offer_accepted. Waiting for messages...")
            channel.basic_consume(
                queue="process_payment.offer_accepted",
                on_message_callback=handle_offer_accepted,
                auto_ack=False
            )
            channel.start_consuming()
        except Exception as e:
            print(f"Consumer connection lost: {e}, reconnecting in 2s...")
            time.sleep(2)
