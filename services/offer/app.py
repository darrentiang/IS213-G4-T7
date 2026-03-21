# Main service entry point
from os import environ
from flask import Flask
from flask_cors import CORS
from app.db import db
from app.routes import offer_bp

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    environ.get("dbURL") or "mysql+mysqlconnector://root@localhost:3306/offer_db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 299}

db.init_app(app)
CORS(app)

app.register_blueprint(offer_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)