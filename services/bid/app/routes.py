# defines the API endpoints (HTTP routes)

from flask import Blueprint, request, jsonify
from app.db import db
from app.models import Bid

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

    if bids:
        return jsonify({
            "code": 200,
            "data": {"bids": [bid.json() for bid in bids]}
        }), 200

    return jsonify({"code": 404, "message": message}), 404


@bid_bp.route("/bids", methods=['POST'])
def create_bid():
    data = request.get_json()
    
    if not data or 'listing_id' not in data or 'buyer_id' not in data or 'amount' not in data:
        return jsonify({"code": 400, "message": "Missing required fields."}), 400
    
    # Before creating the new bid, query the current highest
    prev_highest = db.session.scalar(
        db.select(Bid)
        .filter_by(listing_id=data['listing_id'])
        .order_by(Bid.amount.desc())
        .limit(1)
    )
    prev_highest_buyer_id = prev_highest.buyer_id if prev_highest else None

    bid = Bid(
        listing_id=data['listing_id'],
        buyer_id=data['buyer_id'],
        amount=data['amount']
    )

    try:
        if not request.is_json:
            return jsonify({"code": 400, "message": "Request must be JSON."}), 400

        data = request.get_json()

        for field in ('listing_id', 'buyer_id', 'amount'):
            if field not in data:
                return jsonify({"code": 400, "message": f"Missing required field: {field}"}), 400

        bid = Bid(
            listing_id=data['listing_id'],
            buyer_id=data['buyer_id'],
            amount=data['amount']
        )
        db.session.add(bid)
        db.session.commit()

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
