# defines the API endpoints (HTTP routes)

from os import environ
from flask import Blueprint, request, jsonify
from app.db import db
from app.models import Offer
from app.amqp_lib import connect, close, publish_message

offer_bp = Blueprint('offer', __name__)


def _amqp_publish(publish_fn):
    """Open a fresh AMQP connection, run publish_fn(channel), then close."""
    amqp_host = environ.get("RABBITMQ_HOST") or "localhost"
    amqp_port = int(environ.get("RABBITMQ_PORT") or 5672)
    connection, channel = connect(amqp_host, amqp_port)
    try:
        publish_fn(channel)
    finally:
        close(connection, channel)

@offer_bp.route("/offers")
def get_offers():
    """Get offers filtered by listingId, buyerId, or both."""
    listing_id = request.args.get("listingId", type=int)
    buyer_id = request.args.get("buyerId", type=int)

    query = db.select(Offer)
    if listing_id:
        query = query.filter_by(listing_id=listing_id)
    if buyer_id:
        query = query.filter_by(buyer_id=buyer_id)

    offers = db.session.scalars(query).all()

    return jsonify({
        "code": 200,
        "data": {"offers": [o.json() for o in offers]}
    }), 200


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

        try:
            _amqp_publish(lambda ch: publish_message(ch, "market.events", "offer.created", {
                "offerId": offer.offer_id,
                "listingId": offer.listing_id,
                "buyerId": offer.buyer_id,
                "sellerId": offer.seller_id,
                "amount": float(offer.amount)
            }))
        except Exception as amqp_err:
            print(f"Failed to publish offer.created: {amqp_err}")

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

        try:
            _amqp_publish(lambda ch: publish_message(ch, "market.events", "offer.countered", {
                "offerId": offer.offer_id,
                "listingId": offer.listing_id,
                "buyerId": offer.buyer_id,
                "sellerId": offer.seller_id,
                "amount": float(offer.amount)
            }))
        except Exception as amqp_err:
            print(f"Failed to publish offer.countered: {amqp_err}")

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

            try:
                _amqp_publish(lambda ch: publish_message(ch, "market.events", "offer.accepted", {
                    "offerId": offer.offer_id,
                    "listingId": offer.listing_id,
                    "buyerId": offer.buyer_id,
                    "sellerId": offer.seller_id,
                    "amount": float(offer.amount)
                }))
            except Exception as amqp_err:
                print(f"Failed to publish offer.accepted: {amqp_err}")

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

            try:
                _amqp_publish(lambda ch: publish_message(ch, "market.events", "offer.rejected", {
                    "offerId": offer.offer_id,
                    "listingId": offer.listing_id,
                    "buyerId": offer.buyer_id,
                    "sellerId": offer.seller_id
                }))
            except Exception as amqp_err:
                print(f"Failed to publish offer.rejected: {amqp_err}")

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