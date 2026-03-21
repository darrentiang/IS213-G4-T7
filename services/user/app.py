#!/usr/bin/env python3
from os import environ
from flask import Flask
from flask_cors import CORS
from app.db import db
from app.routes import user_bp

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    environ.get("dbURL") or "mysql+mysqlconnector://root:root@localhost:3306/user_db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 299}

db.init_app(app)
CORS(app)

app.register_blueprint(user_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)
