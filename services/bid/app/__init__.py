# tells Python that app/ is a module (package)

from flask import Flask
from app.db import db
from app.routes import bid_bp

def create_app():
    app = Flask(__name__)
    
    # connect to the database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:root@localhost:3308/bid'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    app.register_blueprint(bid_bp)

    return app