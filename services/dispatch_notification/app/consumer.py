# Dispatch Notification consumer.
# Listens on RabbitMQ queues and reacts to events by calling other services via HTTP to send email notifications.
"""
FLOW FOR bid.placed:
  1. Receive bid.placed message from notif.bid queue
  2. Check if prevHighestBuyerId is null
       → null means this is the first bid on this listing, nobody to notify → stop
       → not null means someone just got outbid → continue
  3. Call User service to get the outbid buyer's email
  4. Call Notification service (Outsystems) to send "You've been outbid!" email
"""

import json
import time
import hashlib
import requests
from datetime import datetime, timezone, timedelta
from os import environ

SGT = timezone(timedelta(hours=8))

def to_sgt(utc_str):
    """Convert ISO UTC datetime string to SGT formatted string."""
    try:
        dt = datetime.fromisoformat(utc_str).replace(tzinfo=timezone.utc)
        return dt.astimezone(SGT).strftime("%d %b %Y, %I:%M %p SGT")
    except Exception:
        return utc_str
from app.amqp_lib import connect
from app import amqp_setup

USER_SERVICE_URL = environ.get("USER_SERVICE_URL", "http://user:5004")
LISTING_SERVICE_URL = environ.get("LISTING_SERVICE_URL", "http://listing:5001")
NOTIFICATION_URL = environ.get(
    "NOTIFICATION_SERVICE_URL",
    "https://personal-1hkpzqtq.outsystemscloud.com/NotificationService/rest/NotificationApi/notifications"
)

amqp_host = environ.get("RABBITMQ_HOST", "localhost")
amqp_port = int(environ.get("RABBITMQ_PORT", 5672))

MAX_RETRIES = 3
# tracks retry count per message, keyed by hash of message body
# delivery_tag changes on every requeue so we use body hash as a stable identifier
_retry_counts = {}


def _get_listing_title(listing_id, fallback=None):
    """Fetch listing title from Listing service; returns fallback on failure."""
    try:
        resp = requests.get(f"{LISTING_SERVICE_URL}/listings/{listing_id}")
        resp.raise_for_status()
        return resp.json().get("data", {}).get("title") or fallback or f"listing #{listing_id}"
    except Exception:
        return fallback or f"listing #{listing_id}"


def _retry_or_discard(channel, method, body, label):
    """
    On notification failure: requeue up to MAX_RETRIES times, then discard.
    Returns True if requeued, False if discarded.
    """
    msg_id = hashlib.md5(body).hexdigest()
    attempt = _retry_counts.get(msg_id, 0) + 1
    _retry_counts[msg_id] = attempt

    if attempt < MAX_RETRIES:
        print(f"[{label}] Attempt {attempt}/{MAX_RETRIES} failed, requeuing...")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        return True
    else:
        print(f"[{label}] All {MAX_RETRIES} attempts failed, discarding message.")
        del _retry_counts[msg_id]
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return False


def handle_bid_placed(channel, method, properties, body):
    print(f"[bid.placed] Received: {body}")
    message = json.loads(body)

    prev_highest_buyer_id = message.get("prevHighestBuyerId")

    # if no previous highest bidder, this is the first bid — nothing to do
    if prev_highest_buyer_id is None:
        print("[bid.placed] First bid on this listing, no one to notify. Skipping.")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    # buyer outbid themselves — no need to notify
    buyer_id = message.get("buyerId")
    if buyer_id is not None and buyer_id == prev_highest_buyer_id:
        print(f"[bid.placed] Buyer {buyer_id} outbid themselves. Skipping notification.")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    listing_id = message.get("listingId")
    amount = message.get("amount")

    # get the outbid buyer's email from User service
    try:
        user_response = requests.get(f"{USER_SERVICE_URL}/users/{prev_highest_buyer_id}")
        user_response.raise_for_status()
        user_data = user_response.json().get("data", {})
        email = user_data.get("email")
    except Exception as e:
        print(f"[bid.placed] Failed to get user {prev_highest_buyer_id} from User service: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    if not email:
        print(f"[bid.placed] No email found for user {prev_highest_buyer_id}. Skipping.")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    # send the outbid notification via Notification service
    try:
        notif_response = requests.post(
            NOTIFICATION_URL,
            json={
                "recipientEmail": email,
                "subject": "You've been outbid!",
                "body": f"Someone placed a higher bid of ${amount:.2f} on '{_get_listing_title(listing_id)}'. Place a new bid to stay in the lead!"
            }
        )
        notif_response.raise_for_status()
        print(f"[bid.placed] Outbid notification sent to {email}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[bid.placed] Failed to send notification to {email}: {e}")
        _retry_or_discard(channel, method, body, "bid.placed")


def handle_listing_event(channel, method, properties, body):
    """
    Called when a message arrives in notif.listing.
    Handles both listing.scheduled and listing.active events —
    we check method.routing_key to know which one it is.
    """
    routing_key = method.routing_key
    print(f"[{routing_key}] Received: {body}")
    message = json.loads(body)

    seller_id = message.get("sellerId")
    listing_id = message.get("listingId")

    # Get seller email from User service
    try:
        user_response = requests.get(f"{USER_SERVICE_URL}/users/{seller_id}")
        user_response.raise_for_status()
        email = user_response.json().get("data", {}).get("email")
    except Exception as e:
        print(f"[{routing_key}] Failed to get user {seller_id}: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    if not email:
        print(f"[{routing_key}] No email for user {seller_id}. Skipping.")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    # Build the email content based on which event fired
    if routing_key == "listing.scheduled":
        # Also fetch listing details to get start_time for the email
        try:
            listing_response = requests.get(f"{LISTING_SERVICE_URL}/listings/{listing_id}")
            listing_response.raise_for_status()
            listing = listing_response.json().get("data", {})
            start_time = to_sgt(listing.get("startTime", "")) or "the scheduled time"
            listing_title = listing.get("title") or f"listing #{listing_id}"
        except Exception as e:
            print(f"[listing.scheduled] Failed to get listing {listing_id}: {e}")
            start_time = "the scheduled time"
            listing_title = f"listing #{listing_id}"

        subject = "Your auction has been scheduled!"
        body_text = f"Your auction '{listing_title}' is scheduled to go live at {start_time}."

    elif routing_key == "listing.active":
        listing_title = _get_listing_title(listing_id)
        subject = "Your auction is now LIVE!"
        body_text = f"Your auction '{listing_title}' is now active. Buyers can start placing bids!"

    else:
        print(f"[{routing_key}] Unhandled listing event. Skipping.")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    # Send email via Notification service
    try:
        notif_response = requests.post(
            NOTIFICATION_URL,
            json={"recipientEmail": email, "subject": subject, "body": body_text}
        )
        notif_response.raise_for_status()
        print(f"[{routing_key}] Notification sent to {email}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[{routing_key}] Failed to send notification: {e}")
        _retry_or_discard(channel, method, body, routing_key)


def handle_auction_no_eligible_bidders(channel, method, properties, body):
    """US2 D2 Steps 11-13: Notify seller that no bidders could pay."""
    print(f"[auction.no_eligible_bidders] Received: {body}")
    message = json.loads(body)

    seller_id = message.get("sellerId")
    listing_id = message.get("listingId")

    try:
        user_response = requests.get(f"{USER_SERVICE_URL}/users/{seller_id}")
        user_response.raise_for_status()
        email = user_response.json().get("data", {}).get("email")
    except Exception as e:
        print(f"[auction.no_eligible_bidders] Failed to get user {seller_id}: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    if not email:
        print(f"[auction.no_eligible_bidders] No email for user {seller_id}. Skipping.")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        notif_response = requests.post(
            NOTIFICATION_URL,
            json={
                "recipientEmail": email,
                "subject": "Auction ended — no eligible bidders",
                "body": f"Your auction '{_get_listing_title(listing_id)}' has ended, but no bidders could complete payment. The listing has been marked as unsold."
            }
        )
        notif_response.raise_for_status()
        print(f"[auction.no_eligible_bidders] Notification sent to {email}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[auction.no_eligible_bidders] Failed to send notification: {e}")
        _retry_or_discard(channel, method, body, "auction.no_eligible_bidders")


def handle_payment_event(channel, method, properties, body):
    """
    US3 D3 steps 7a/7b: payment.success or payment.failed.
    Fetch buyer + seller emails, send notification to both.
    """
    routing_key = method.routing_key
    print(f"[{routing_key}] Received: {body}")
    message = json.loads(body)

    listing_id = message.get("listingId")
    buyer_id = message.get("buyerId")

    # get seller_id from listing
    try:
        listing_resp = requests.get(f"{LISTING_SERVICE_URL}/listings/{listing_id}")
        listing_resp.raise_for_status()
        listing_data = listing_resp.json().get("data", {})
        seller_id = listing_data.get("sellerId")
        listing_title = listing_data.get("title") or f"listing #{listing_id}"
    except Exception as e:
        print(f"[{routing_key}] Failed to get listing {listing_id}: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    # fetch both buyer and seller emails
    emails = {}
    for role, uid in [("buyer", buyer_id), ("seller", seller_id)]:
        try:
            resp = requests.get(f"{USER_SERVICE_URL}/users/{uid}")
            resp.raise_for_status()
            emails[role] = resp.json().get("data", {}).get("email")
        except Exception as e:
            print(f"[{routing_key}] Failed to get {role} (user {uid}): {e}")

    if not emails:
        print(f"[{routing_key}] No emails found. Skipping.")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    # build email content based on success or failure
    if routing_key == "payment.success":
        amount = message.get("amount", 0)
        subject = "Payment confirmed!"
        body_text = f"Payment of ${amount:.2f} for '{listing_title}' was successful. Transaction complete!"
    else:
        subject = "Payment failed"
        body_text = f"Payment for '{listing_title}' has failed. Please contact support if you believe this is an error."

    # send to each recipient
    for role, email in emails.items():
        if not email:
            continue
        try:
            notif_resp = requests.post(
                NOTIFICATION_URL,
                json={"recipientEmail": email, "subject": subject, "body": body_text}
            )
            notif_resp.raise_for_status()
            print(f"[{routing_key}] Notification sent to {role} ({email})")
        except Exception as e:
            print(f"[{routing_key}] Failed to send notification to {role} ({email}): {e}")

    channel.basic_ack(delivery_tag=method.delivery_tag)


def handle_offer_event(channel, method, properties, body):
    """
    Handles offer.created, offer.countered, offer.accepted, offer.rejected.
    Queue: notif.offer, binding key: offer.*
    """
    routing_key = method.routing_key
    print(f"[{routing_key}] Received: {body}")
    message = json.loads(body)

    listing_id = message.get("listingId")
    buyer_id = message.get("buyerId")
    seller_id = message.get("sellerId")
    amount = message.get("amount")
    listing_title = _get_listing_title(listing_id)

    def get_email(user_id):
        resp = requests.get(f"{USER_SERVICE_URL}/users/{user_id}")
        resp.raise_for_status()
        return resp.json().get("data", {}).get("email")

    if routing_key == "offer.created":
        # Notify seller: "You received an offer of $X"
        try:
            email = get_email(seller_id)
        except Exception as e:
            print(f"[{routing_key}] Failed to get seller {seller_id}: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        recipients = [("seller", email)]
        subject = f"You received an offer of ${amount:.2f}"
        body_text = f"A buyer has made an offer of ${amount:.2f} on your listing '{listing_title}'. Log in to accept, counter, or reject."

    elif routing_key == "offer.countered":
        # Notify buyer: "Seller countered at $X"
        try:
            email = get_email(buyer_id)
        except Exception as e:
            print(f"[{routing_key}] Failed to get buyer {buyer_id}: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        recipients = [("buyer", email)]
        subject = f"Seller countered at ${amount:.2f}"
        body_text = f"The seller has countered your offer on '{listing_title}' with ${amount:.2f}. Log in to accept or reject."

    elif routing_key == "offer.accepted":
        # Notify buyer: "Your offer has been accepted!"
        try:
            email = get_email(buyer_id)
        except Exception as e:
            print(f"[{routing_key}] Failed to get buyer {buyer_id}: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        recipients = [("buyer", email)]
        subject = "Your offer has been accepted!"
        body_text = f"Your offer of ${amount:.2f} on '{listing_title}' has been accepted. Payment will be processed shortly."

    elif routing_key == "offer.rejected":
        # Notify seller: "Buyer rejected your counter"
        try:
            email = get_email(seller_id)
        except Exception as e:
            print(f"[{routing_key}] Failed to get seller {seller_id}: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return
        recipients = [("seller", email)]
        subject = "Buyer rejected your counter offer"
        body_text = f"The buyer has rejected your counter offer on '{listing_title}'. The offer has been closed."

    else:
        print(f"[{routing_key}] Unhandled offer event. Skipping.")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    for role, email in recipients:
        if not email:
            print(f"[{routing_key}] No email for {role}. Skipping.")
            continue
        try:
            notif_resp = requests.post(
                NOTIFICATION_URL,
                json={"recipientEmail": email, "subject": subject, "body": body_text}
            )
            notif_resp.raise_for_status()
            print(f"[{routing_key}] Notification sent to {role} ({email})")
        except Exception as e:
            print(f"[{routing_key}] Failed to send notification to {role} ({email}): {e}")
            _retry_or_discard(channel, method, body, routing_key)
            return

    channel.basic_ack(delivery_tag=method.delivery_tag)


def start():
    """
    Connect to RabbitMQ, declare queues, and start consuming.
    Auto-reconnects if the connection drops.
    """
    while True:
        try:
            connection, channel = connect(amqp_host, amqp_port)
            amqp_setup.setup(channel)

            channel.basic_consume(
                queue="notif.bid",
                on_message_callback=handle_bid_placed,
                auto_ack=False
            )

            channel.basic_consume(
                queue="notif.listing",
                on_message_callback=handle_listing_event,
                auto_ack=False
            )

            channel.basic_consume(
                queue="notif.auction",
                on_message_callback=handle_auction_no_eligible_bidders,
                auto_ack=False
            )

            channel.basic_consume(
                queue="notif.payment",
                on_message_callback=handle_payment_event,
                auto_ack=False
            )

            channel.basic_consume(
                queue="notif.offer",
                on_message_callback=handle_offer_event,
                auto_ack=False
            )

            print("Dispatch Notification is listening. Waiting for messages...")
            channel.start_consuming()
        except Exception as e:
            print(f"Consumer connection lost: {e}, reconnecting in 2s...")
            time.sleep(2)
