# defines the API endpoints (HTTP routes)

import pika
from datetime import datetime
from flask import Blueprint, request, jsonify
from app.db import db
from app.models import Listing
from app.amqp_lib import publish_message

listing_bp = Blueprint('listing', __name__)


@listing_bp.route("/listings", methods=['POST'])
def create_listing():
    try:
        if not request.is_json:
            return jsonify({"code": 400, "message": "Request must be JSON."}), 400

        data = request.get_json()

        for field in ('seller_id', 'title', 'listing_type', 'start_price'):
            if field not in data:
                return jsonify({"code": 400, "message": f"Missing required field: {field}"}), 400

        listing_type = data['listing_type'].upper()

        if listing_type not in ('AUCTION', 'FIXED'):
            return jsonify({"code": 400, "message": "listing_type must be AUCTION or FIXED."}), 400

        # AUCTION requires start_time and end_time
        if listing_type == 'AUCTION':
            if 'start_time' not in data or 'end_time' not in data:
                return jsonify({
                    "code": 400,
                    "message": "AUCTION listings require start_time and end_time."
                }), 400
            status = 'SCHEDULED'
        else:
            status = 'ACTIVE'

        listing = Listing(
            seller_id=data['seller_id'],
            title=data['title'],
            description=data.get('description'),
            image_url=data.get('image_url'),
            listing_type=listing_type,
            start_price=data['start_price'],
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            status=status
        )
        db.session.add(listing)
        db.session.commit()

        # if AUCTION, publish events to RabbitMQ
        if listing_type == 'AUCTION':
            from flask import current_app
            channel = current_app.config.get('AMQP_CHANNEL')
            print(f"AMQP channel: {channel}")
            if not channel:
                print("WARNING: No AMQP channel available, skipping publish")

            # publish listing.scheduled to market.events
            publish_message(channel, "market.events", "listing.scheduled", {
                "listingId": listing.listing_id,
                "sellerId": listing.seller_id
            })

            # calculate TTL in milliseconds (time until start_time)
            start_dt = datetime.fromisoformat(data['start_time'])
            ttl_ms = max(int((start_dt - datetime.now()).total_seconds() * 1000), 0)

            # publish auction.start to market.timers with TTL
            publish_message(
                channel, "", "market.timers",
                {"listingId": listing.listing_id, "type": "auction.start"},
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    expiration=str(ttl_ms)
                )
            )
            print(f"Timer 1 set: auction.start for listing {listing.listing_id} in {ttl_ms}ms")

        return jsonify({"code": 201, "data": listing.json()}), 201

    except Exception as e:
        return jsonify({
            "code": 500,
            "message": "An error occurred creating the listing. " + str(e)
        }), 500


@listing_bp.route("/listings")
def get_all_listings():
    listings = db.session.scalars(db.select(Listing)).all()

    if listings:
        return jsonify({
            "code": 200,
            "data": {"listings": [l.json() for l in listings]}
        }), 200

    return jsonify({"code": 404, "message": "No listings found."}), 404


@listing_bp.route("/listings/<int:listing_id>")
def get_listing(listing_id):
    listing = db.session.scalar(
        db.select(Listing).filter_by(listing_id=listing_id)
    )

    if listing:
        return jsonify({"code": 200, "data": listing.json()}), 200

    return jsonify({"code": 404, "message": f"Listing {listing_id} not found."}), 404


@listing_bp.route("/listings/<int:listing_id>/status", methods=['PATCH'])
def update_listing_status(listing_id):
    try:
        if not request.is_json:
            return jsonify({"code": 400, "message": "Request must be JSON."}), 400

        data = request.get_json()

        if 'status' not in data:
            return jsonify({"code": 400, "message": "Missing required field: status"}), 400

        listing = db.session.scalar(
            db.select(Listing).filter_by(listing_id=listing_id)
        )

        if not listing:
            return jsonify({"code": 404, "message": f"Listing {listing_id} not found."}), 404

        valid_statuses = (
            'SCHEDULED', 'ACTIVE', 'CLOSED_PENDING_PAYMENT',
            'SOLD', 'FAILED_NO_ELIGIBLE_BIDDER'
        )
        new_status = data['status'].upper()

        if new_status not in valid_statuses:
            return jsonify({
                "code": 400,
                "message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }), 400

        listing.status = new_status

        # set winning_buyer_id if provided (used during auction close)
        if 'winning_buyer_id' in data:
            listing.winning_buyer_id = data['winning_buyer_id']

        db.session.commit()

        return jsonify({"code": 200, "data": listing.json()}), 200

    except Exception as e:
        return jsonify({
            "code": 500,
            "message": "An error occurred updating the listing. " + str(e)
        }), 500
