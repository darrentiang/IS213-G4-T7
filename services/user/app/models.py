from app.db import db


class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    stripe_id = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime, nullable=False, server_default=db.func.now()
    )

    def __init__(self, email, name, stripe_id):
        self.email = email
        self.name = name
        self.stripe_id = stripe_id

    def json(self):
        return {
            "userId": self.user_id,
            "email": self.email,
            "name": self.name,
            "stripeId": self.stripe_id,
            "createdAt": self.created_at.isoformat()
        }
