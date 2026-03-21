#!/usr/bin/env python3
from os import environ
from flask import Flask
from flask_cors import CORS
from app.db import db
from app.routes import listing_bp
from app.amqp_lib import connect
from app import amqp_setup
from app.consumer import start_consumer

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    environ.get("dbURL") or "mysql+mysqlconnector://root:root@localhost:3306/listing_db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 299}

db.init_app(app)
CORS(app)

app.register_blueprint(listing_bp)

# connect to RabbitMQ and set up exchanges/queues
amqp_host = environ.get("RABBITMQ_HOST") or "localhost"
amqp_port = int(environ.get("RABBITMQ_PORT") or 5672)

connection, channel = connect(amqp_host, amqp_port)
amqp_setup.setup(channel)

# store channel in app config so routes can publish
app.config['AMQP_CHANNEL'] = channel

# start DLQ consumer in background thread
start_consumer(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
