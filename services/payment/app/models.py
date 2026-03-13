# defines your database schema, each class represents a table
# defines the entity/table owned by this atomic service

from app.db import db

class Payment(db.Model):
    payment_id = db.Column(db.Integer, primary_key=True)
    
