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
        return jsonify(
            {
                "code": 200, 
                "data": {
                    "bids": [bid.json() for bid in bids]
                    }
            }
        )
    
    return jsonify(
        {
            "code": 404, 
            "message": message
        }
    ), 404

@bid_bp.route("/bids", methods=['POST'])
def create_bid():
    data = request.get_json()
    
    if not data or 'listing_id' not in data or 'buyer_id' not in data or 'amount' not in data:
        return jsonify({"code": 400, "message": "Missing required fields."}), 400
    
    bid = Bid(
        listing_id=data['listing_id'],
        buyer_id=data['buyer_id'],
        amount=data['amount']
    )

    try:
        db.session.add(bid)
        db.session.commit()
    except:
        return jsonify(
            {
                "code": 500, 
                "message": "An error occurred creating the bid."
            }
        ), 500

    return jsonify(
        {
            "code": 201, 
            "data": bid.json()
        }
    ), 201

@bid_bp.route("/bids/highest/<int:listing_id>", methods=['GET'])
def get_highest_bid(listing_id):
    bid = db.session.scalar(
        db.select(Bid)
        .filter_by(listing_id=listing_id)
        .order_by(Bid.amount.desc())
        .limit(1)
    )

    if bid:
        return jsonify({"code": 200, "data": bid.json()})
    
    return jsonify({"code": 404, "message": "No bids found for this listing."}), 404

