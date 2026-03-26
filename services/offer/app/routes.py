# defines the API endpoints (HTTP routes)

from flask import Blueprint, request, jsonify
from app.db import db
from app.models import Offer

offer_bp = Blueprint('offer', __name__)

@offer_bp.route("/offers", methods=['POST'])
def create_offer(): 
    try:
        if not request.is_json:
            return jsonify({
                "code": 400,
                "message": "Request must be JSON."
            }), 400
        data = request.get_json()

        for field in ('listingId', 'buyerId', 'sellerId', 'amount'):
            if field not in data: 
                return jsonify({
                    "code": 400,
                    "message": f"Missing required field: {field}"
                }), 400
            
        offer = Offer(
            listing_id=data['listingId'],
            buyer_id=data['buyerId'],
            seller_id=data['sellerId'],
            amount=data['amount'],
            status="PENDING",
            turn="SELLER"
        )
        db.session.add(offer)
        db.session.commit()

        return jsonify({
            "code": 201,
            "data": offer.json()
        }), 201
    
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": "An error occurred creating the offer." + str(e)
        }), 500

@offer_bp.route("/offers/<int:offer_id>", methods=['PATCH'])
def counter_offer(offer_id):
    try:
        if not request.is_json:
            return jsonify({
                "code": 400,
                "message": "Request must be JSON."
            }), 400
        data = request.get_json()

        if 'amount' not in data:
            return jsonify({
                "code": 400,
                "message": "Missing required field: amount"
            }), 400
        
        try:
            counter_amount = float(data['amount'])
        except (TypeError, ValueError):
            return jsonify({
                "code": 400,
                "message": "Invalid amount."
            }), 400
        
        if counter_amount <= 0:
            return jsonify ({
                "code": 400, 
                "message": "Amount must be more than 0."
            }), 400

        offer = db.session.scalar(db.select(Offer).filter_by(offer_id=offer_id))
        if not offer: 
            return jsonify({
                "code": 404,
                "message": f"Offer {offer_id} not found."
            }), 404 

        if offer.turn != "SELLER":
            return jsonify ({
                "code": 403,
                "message": "Not seller's turn to counter.",
                "status": offer.status,
                "turn": offer.turn
            }), 403

        offer.amount = counter_amount
        offer.status = "COUNTERED"
        offer.turn = "BUYER"
        db.session.commit()

        return jsonify({
            "code": 200,
            "data": offer.json()
        }), 200 
        
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": "An error occurred countering the offer." + str(e)
        }), 500

@offer_bp.route("/offers/<int:offer_id>/accept", methods=['POST'])
def accept_offer(offer_id):
    try:
        offer = db.session.scalar(db.select(Offer).filter_by(offer_id=offer_id))
        if not offer: 
            return jsonify({
                "code": 404,
                "message": f"Offer {offer_id} not found."
            }), 404 
        
        if (offer.status == "PENDING" and offer.turn == "SELLER") or \
        (offer.status == "COUNTERED" and offer.turn == "BUYER"):
            offer.status = "ACCEPTED"
            offer.turn = None
            db.session.commit()

            return jsonify({
                "code": 200,
                "data": offer.json()
            }), 200 
        
        return jsonify({
            "code": 400,
            "message": "Invalid state for accepting offer.",
            "status": offer.status,
            "turn": offer.turn
        }), 400
            
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": "An error occurred accepting the offer." + str(e)
        }), 500

@offer_bp.route("/offers/<int:offer_id>/reject", methods=['POST'])
def reject_offer(offer_id):
    try: 
        offer = db.session.scalar(db.select(Offer).filter_by(offer_id=offer_id))
        if not offer: 
            return jsonify({
                "code": 404,
                "message": f"Offer {offer_id} not found."
            }), 404 
        
        if offer.status == "COUNTERED" and offer.turn == "BUYER":
            offer.status = "REJECTED"
            offer.turn = None
            db.session.commit()

            return jsonify({
                "code": 200,
                "data": offer.json()
            }), 200 
        
        return jsonify({
            "code": 400,
            "message": "Invalid state for rejecting the offer.",
            "status": offer.status,
            "turn": offer.turn
        }), 400

    except Exception as e:
        return jsonify({
            "code": 500,
            "message": "An error occurred rejecting the offer." + str(e)
        }), 500 