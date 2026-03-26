"""
DLQ Consumer for the Listing service (runs as background thread).
Listens on market.dlq.start for auction.start messages (Timer 1).
When Timer 1 fires: set listing ACTIVE, publish listing.active,
and set Timer 2 (auction.close) to market.timers.close.
"""

import json
import threading
import pika
from os import environ
from datetime import datetime

from app.amqp_lib import connect, publish_message
from app import amqp_setup
from app.db import db
from app.models import Listing

amqp_host = environ.get("RABBITMQ_HOST") or "localhost"
amqp_port = int(environ.get("RABBITMQ_PORT") or 5672)

# flask app reference, set by start_consumer()
_flask_app = None


def handle_auction_start(channel, method, properties, body):
    """Called when auction.start TTL expires and lands in market.dlq."""
    message = json.loads(body)
    print(f"Received from DLQ: {message}")

    msg_type = message.get("type")

    if msg_type == "auction.start":
        listing_id = message["listingId"]

        with _flask_app.app_context():
            listing = db.session.scalar(
                db.select(Listing).filter_by(listing_id=listing_id)
            )

            if not listing:
                print(f"Listing {listing_id} not found, skipping")
                return

            if listing.status != 'SCHEDULED':
                print(f"Listing {listing_id} is {listing.status}, not SCHEDULED. Skipping")
                return

            # set listing to ACTIVE
            listing.status = 'ACTIVE'
            db.session.commit()
            print(f"Listing {listing_id} is now ACTIVE")

            # publish listing.active to market.events
            publish_message(channel, "market.events", "listing.active", {
                "listingId": listing.listing_id,
                "sellerId": listing.seller_id
            })

            # set Timer 2: auction.close with TTL until end_time
            ttl_ms = max(int((listing.end_time - datetime.now()).total_seconds() * 1000), 0)

            publish_message(
                channel, "", "market.timers.close",
                {"listingId": listing.listing_id, "type": "auction.close"},
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    expiration=str(ttl_ms)
                )
            )
            print(f"Timer 2 set: auction.close for listing {listing_id} in {ttl_ms}ms")

    else:
        print(f"Unknown message type in DLQ: {msg_type}, skipping")


def _consume():
    """Background thread: connect to RabbitMQ and consume from market.dlq."""
    connection, channel = connect(amqp_host, amqp_port)
    amqp_setup.setup(channel)

    print("Consuming from market.dlq.start...")
    channel.basic_consume(
        queue="market.dlq.start",
        on_message_callback=handle_auction_start,
        auto_ack=True
    )
    channel.start_consuming()


def start_consumer(flask_app):
    """Start the DLQ consumer in a background thread."""
    global _flask_app
    _flask_app = flask_app

    thread = threading.Thread(target=_consume, daemon=True)
    thread.start()
    print("DLQ consumer thread started")
