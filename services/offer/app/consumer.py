"""
AMQP Consumer for the Offer service (runs as background thread).
Listens on offer.payment_failed for payment.failed events.
When received for a FIXED listing, marks the offer as CANCELLED.
"""

import json
import time
import threading
from os import environ

from app.amqp_lib import connect
from app import amqp_setup
from app.db import db
from app.models import Offer

amqp_host = environ.get("RABBITMQ_HOST") or "localhost"
amqp_port = int(environ.get("RABBITMQ_PORT") or 5672)

# flask app reference, set by start_consumer()
_flask_app = None


def handle_payment_failed(channel, method, properties, body):
    """Called when payment.failed lands in offer.payment_failed queue."""
    message = json.loads(body)
    print(f"[payment.failed] Received: {message}")

    listing_type = message.get("listingType")
    if listing_type != "FIXED":
        print(f"[payment.failed] listingType={listing_type}, ignoring (not FIXED)")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    offer_id = message.get("offerId")
    if not offer_id:
        print("[payment.failed] No offerId in payload, skipping")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    with _flask_app.app_context():
        offer = db.session.scalar(
            db.select(Offer).filter_by(offer_id=offer_id)
        )

        if not offer:
            print(f"[payment.failed] Offer {offer_id} not found, skipping")
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        offer.status = "CANCELLED"
        offer.turn = None
        db.session.commit()
        print(f"[payment.failed] Offer {offer_id} marked CANCELLED")

    channel.basic_ack(delivery_tag=method.delivery_tag)


def _consume():
    """Background thread: connect to RabbitMQ and consume from offer.payment_failed.
    Auto-reconnects if the connection drops."""
    while True:
        try:
            connection, channel = connect(amqp_host, amqp_port)
            amqp_setup.setup(channel)

            print("Offer consumer listening on offer.payment_failed...")
            channel.basic_consume(
                queue="offer.payment_failed",
                on_message_callback=handle_payment_failed,
                auto_ack=False
            )
            channel.start_consuming()
        except Exception as e:
            print(f"Offer consumer connection lost: {e}, reconnecting in 2s...")
            time.sleep(2)


def start_consumer(flask_app):
    """Start the offer consumer in a background thread."""
    global _flask_app
    _flask_app = flask_app

    thread = threading.Thread(target=_consume, daemon=True)
    thread.start()
    print("Offer consumer thread started")
