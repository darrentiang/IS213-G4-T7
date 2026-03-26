# defines your database schema, each class represents a table
# defines the entity/table owned by this atomic service

from app.db import db

class Payment(db.Model):

    __tablename__ = "payment"

    payment_id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    listing_id = db.Column(db.Integer, nullable=False)
    buyer_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(10,2), nullable=False)
    stripe_charge_id = db.Column(db.String(255), nullable=True)
    idempotency_key = db.Column(db.String(255), nullable=False,unique = True) 
    status = db.Column(db.String(20), nullable=False) # SUCCESS or FAILED
    created_at = db.Column(db.DateTime,nullable=False, server_default=db.func.now())
    
    def __init__(self, listing_id, buyer_id, amount, idempotency_key, status, stripe_charge_id=None):
        self.listing_id      = listing_id
        self.buyer_id        = buyer_id
        self.amount          = amount
        self.idempotency_key = idempotency_key
        self.status          = status
        self.stripe_charge_id = stripe_charge_id 

    def json(self):
        return {
            "paymentId": self.payment_id,
            "listingId": self.listing_id,
            "buyerId": self.buyer_id,
            "amount": float(self.amount),
            "stripeChargeId": self.stripe_charge_id,
            "idempotencyKey": self.idempotency_key,
            "status": self.status,
            "createdAt": self.created_at.isoformat()
        }