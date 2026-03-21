# tells Python that app/ is a module (package)

from os import environ
from flask import Flask
from flask_cors import CORS
from app.db import db
from app.routes import bid_bp

def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = (
        environ.get("dbURL") or "mysql+mysqlconnector://root:root@localhost:3306/bid")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 299}

    db.init_app(app)
    CORS(app)
    app.register_blueprint(bid_bp)

    return app