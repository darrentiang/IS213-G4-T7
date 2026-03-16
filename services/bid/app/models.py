# defines your database schema, each class represents a table
# defines the entity/table owned by this atomic service

from app.db import db
from datetime import datetime

class Bid(db.Model):
    __tablename__ = 'bid'
    bid_id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, nullable=False)
    buyer_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def __init__(self, listing_id, buyer_id, amount):
        self.listing_id = listing_id
        self.buyer_id = buyer_id
        self.amount = amount

    def json(self):
        return {
            "bid_id": self.bid_id,
            "listing_id": self.listing_id,
            "buyer_id": self.buyer_id,
            "amount": self.amount,
            "created_at": self.created_at.isoformat()
        }