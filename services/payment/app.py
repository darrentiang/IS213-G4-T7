# Main service entry point
from os import environ
from flask import Flask
from flask_cors import CORS
from app.db import db
from app.routes import payment_bp

#Create the Flask app
app = Flask(__name__) 

app.config["SQLALCHEMY_DATABASE_URI"] = (
     environ.get("dbURL") or "mysql+mysqlconnector://root@localhost:3306/payment_db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 299}

CORS(app)

#connect the database to app
db.init_app(app)

#plug in the routes 
app.register_blueprint(payment_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)