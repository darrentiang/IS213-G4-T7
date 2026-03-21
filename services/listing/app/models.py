from app.db import db


class Listing(db.Model):
    __tablename__ = 'listings'

    listing_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    seller_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    listing_type = db.Column(db.String(20), nullable=False)
    start_price = db.Column(db.Numeric(10, 2), nullable=False)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False, server_default='ACTIVE')
    winning_buyer_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.now()
    )

    def __init__(self, seller_id, title, description, image_url,
                 listing_type, start_price, start_time=None, end_time=None,
                 status='ACTIVE'):
        self.seller_id = seller_id
        self.title = title
        self.description = description
        self.image_url = image_url
        self.listing_type = listing_type
        self.start_price = start_price
        self.start_time = start_time
        self.end_time = end_time
        self.status = status

    def json(self):
        return {
            "listing_id": self.listing_id,
            "seller_id": self.seller_id,
            "title": self.title,
            "description": self.description,
            "image_url": self.image_url,
            "listing_type": self.listing_type,
            "start_price": float(self.start_price),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "winning_buyer_id": self.winning_buyer_id,
            "created_at": self.created_at.isoformat()
        }
