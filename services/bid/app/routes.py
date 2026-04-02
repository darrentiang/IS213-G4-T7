# defines the API endpoints (HTTP routes)

from flask import Blueprint, request, jsonify
from os import environ
from app.db import db
from app.models import Bid
from app.amqp_lib import connect, publish_message
from app import amqp_setup

amqp_host = environ.get("RABBITMQ_HOST", "localhost")
amqp_port = int(environ.get("RABBITMQ_PORT", 5672))

# creates a "mini app" just for bid routes
bid_bp = Blueprint('bid', __name__)

# get all bids or all bids of a specific listing
@bid_bp.route("/bids", methods=['GET'])
def get_bids():
    listing_id = request.args.get('listingId')

    if listing_id:
        # /bids?listingId=
        bids = db.session.scalars(db.select(Bid).filter_by(listing_id=listing_id)).all()
        message = "No bids found for this listing."
    else:
        # /bids
        bids = db.session.scalars(db.select(Bid)).all()
        message = "No bids found."

    return jsonify({
        "code": 200,
        "data": {"bids": [bid.json() for bid in bids]}
    }), 200


@bid_bp.route("/bids", methods=['POST'])
def create_bid():
    try:
        if not request.is_json:
            return jsonify({"code": 400, "message": "Request must be JSON."}), 400

        data = request.get_json()

        for field in ('listingId', 'buyerId', 'amount'):
            if field not in data:
                return jsonify({"code": 400, "message": f"Missing required field: {field}"}), 400

        # Before creating the new bid, query the current highest
        prev_highest = db.session.scalar(
            db.select(Bid)
            .filter_by(listing_id=data['listingId'])
            .order_by(Bid.amount.desc()) # type: ignore
            .limit(1)
        )
        prev_highest_buyer_id = prev_highest.buyer_id if prev_highest else None

        bid = Bid(
            listing_id=data['listingId'],
            buyer_id=data['buyerId'],
            amount=data['amount']
        )
        db.session.add(bid)
        db.session.commit()

        # Publish bid.placed to market.events exchange.
        # We open a fresh connection for each publish because Flask handles
        # requests concurrently and pika connections are not thread-safe.
        connection, channel = connect(amqp_host, amqp_port)
        amqp_setup.setup(channel) # ensure queues exist
        publish_message(channel, "market.events", "bid.placed", {
            "listingId": bid.listing_id,
            "bidId": bid.bid_id,
            "buyerId": bid.buyer_id,
            "amount": float(bid.amount),
            "prevHighestBuyerId": prev_highest_buyer_id
        })
        connection.close()

        return jsonify({"code": 201, "data": bid.json()}), 201

    except Exception as e:
        return jsonify({
            "code": 500,
            "message": "An error occurred creating the bid. " + str(e)
        }), 500


@bid_bp.route("/bids/highest/<int:listing_id>")
def get_highest_bid(listing_id):
    bid = db.session.scalar(
        db.select(Bid)
        .filter_by(listing_id=listing_id)
        .order_by(Bid.amount.desc()) # type: ignore
    )

    if bid:
        return jsonify({"code": 200, "data": bid.json()}), 200

    return jsonify({"code": 404, "message": "No bids found for this listing."}), 404


@bid_bp.route("/bids/listing/<int:listing_id>", methods=['DELETE'])
def delete_bids_by_listing(listing_id):
    bids = db.session.scalars(db.select(Bid).filter_by(listing_id=listing_id)).all()
    for bid in bids:
        db.session.delete(bid)
    db.session.commit()
    return jsonify({"code": 200, "message": f"Deleted {len(bids)} bid(s) for listing {listing_id}."}), 200


@bid_bp.route("/auctions/<int:listing_id>/close", methods=['POST'])
def get_ranked_bids(listing_id):
    bids = db.session.scalars(
        db.select(Bid)
        .filter_by(listing_id=listing_id)
        .order_by(Bid.amount.desc()) # type: ignore
    ).all()

    if bids:
        return jsonify({
            "code": 200,
            "data": {"bids": [bid.json() for bid in bids]}
        }), 200

    return jsonify({"code": 404, "message": "No bids found for this listing."}), 404
