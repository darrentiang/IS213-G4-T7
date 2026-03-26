# defines your database schema, each class represents a table
# defines the entity/table owned by this atomic service

from app.db import db

class Offer(db.Model):
    __tablename__ = "offers"

    offer_id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, nullable=False)
    buyer_id = db.Column(db.Integer, nullable=False)
    seller_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    turn = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    def __init__(self, listing_id, buyer_id, seller_id, amount, status, turn):
        self.listing_id = listing_id
        self.buyer_id = buyer_id
        self.seller_id = seller_id
        self.amount = amount
        self.status = status
        self.turn = turn

    def json(self):
        return {
            "offerId": self.offer_id,
            "listingId": self.listing_id,
            "buyerId": self.buyer_id,
            "sellerId": self.seller_id,
            "amount": float(self.amount),
            "status": self.status,
            "turn": self.turn,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat()
        }