from app.db import db


class Bid(db.Model):
    __tablename__ = 'bids'

    bid_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    listing_id = db.Column(db.Integer, nullable=False)
    buyer_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.now()
    )

    def __init__(self, listing_id, buyer_id, amount):
        self.listing_id = listing_id
        self.buyer_id = buyer_id
        self.amount = amount

    def json(self):
        return {
            "bidId": self.bid_id,
            "listingId": self.listing_id,
            "buyerId": self.buyer_id,
            "amount": float(self.amount),
            "createdAt": self.created_at.isoformat()
        }
