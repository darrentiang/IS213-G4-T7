# defines the API endpoints (HTTP routes)

from app.db import db
from app.models import Payment
from flask import Blueprint, jsonify, request
import stripe


payment_bp = Blueprint('payment',__name__)
#need set stripe.api_key in env file

@payment_bp.route("/payments/charge",methods=["POST"])
def charge_payment():
    """
    Charge a buyer via Stripe.
 
    Expected body:
    {
        "listingId":   int,
        "buyerId":     int,
        "amount":      float,       -- in dollars e.g. 49.99
        "stripeId":    str,         -- stripe_customer_id from User Service
        "listingType": str,         -- "AUCTION" or "FIXED"
        "offerId":     int | null   -- only for FIXED listings 
    }
    """

    try:
        if not request.is_json:
            return jsonify({
                "code": 400,
                "message": "Request must be JSON."
            }), 400
        
        data =request.get_json()

        for field in ('listingId', 'buyerId', 'amount','stripeId','listingType','idempotencyKey'):
            if field not in data:
                return jsonify({
                    "code": 400,
                    "message": f"Missing required field: {field}"
                }), 400
            
        listing_id   = data.get("listingId")
        buyer_id     = data.get("buyerId")
        amount       = data.get("amount")
        stripe_id    = data.get("stripeId")
        listing_type = data.get("listingType")
        idempotency_key = data.get("idempotencyKey")
        # offer_id     = data.get("offerId")   # optional, only for FIXED listings

        #check if payment has been charged successfully to prevent charging the same buyer for the same listing twice
        existing_payment = Payment.query.filter_by(
            idempotency_key = idempotency_key
        ).first()

        if existing_payment:
            return jsonify({
                "code": 200,
                "message": "Payment already processed.",
                "data": existing_payment.json()
            }), 200
        
        #charge via stripe
        amount_in_cents = int(float(amount)*100)
        try:
            customer = stripe.Customer.retrieve(stripe_id)
            payment_method_id = customer.invoice_settings.default_payment_method

            stripe_charge = stripe.PaymentIntent.create(
            amount   = amount_in_cents,
            currency = "sgd",
            customer = stripe_id,
            payment_method = payment_method_id,  
            confirm  = True,
            automatic_payment_methods = {
               "enabled":         True,
               "allow_redirects": "never" # server side charge, no browser redirect
            },
            metadata = {
               "listing_id":   listing_id,
               "buyer_id":     buyer_id,
               "listing_type": listing_type,
           },
            idempotency_key = idempotency_key   # stripe also deduplicates on this key
            )

            #  success - save record in db
            payment_record = Payment(
            listing_id       = listing_id,
            buyer_id         = buyer_id,
            amount           = amount,
            stripe_charge_id = stripe_charge["id"],
            idempotency_key  = idempotency_key,
            status           = "SUCCESS"
            )
            db.session.add(payment_record)
            db.session.commit()
 
            return jsonify({
                "code": 200,
                "message": "Payment has been made successfully.",
                "data": payment_record.json()
            }), 200

        except stripe.error.CardError as e :
        # failed - save status as failed in db
            payment_record = Payment(
            listing_id      = listing_id,
            buyer_id        = buyer_id,
            amount          = amount,
            idempotency_key = idempotency_key,
            status          = "FAILED"
            )
            db.session.add(payment_record)
            db.session.commit()

            return jsonify({
                "code": 200,
                "status": "FAILED",
                "message": e.user_message or str(e),
                "data": payment_record.json()
            }), 200

    except Exception as e:
        return jsonify(
                {
                    "code": 500,
                    "message": "An error occurred prcessing payment." + str(e)
                }
            ),500