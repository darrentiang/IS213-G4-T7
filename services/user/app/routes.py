from flask import Blueprint, jsonify, request
from app.db import db
from app.models import User

user_bp = Blueprint('user', __name__)


@user_bp.route("/users", methods=['POST'])
def create_user():
    try:
        if not request.is_json:
            return jsonify({
                "code": 400,
                "message": "Request must be JSON."
            }), 400

        data = request.get_json()

        for field in ('email', 'name', 'stripeId'):
            if field not in data:
                return jsonify({
                    "code": 400,
                    "message": f"Missing required field: {field}"
                }), 400

        user = User(
            email=data['email'],
            name=data['name'],
            stripe_id=data['stripeId']
        )
        db.session.add(user)
        db.session.commit()

        return jsonify({
            "code": 201,
            "data": user.json()
        }), 201

    except Exception as e:
        return jsonify({
            "code": 500,
            "message": "An error occurred creating the user. " + str(e)
        }), 500


@user_bp.route("/users/<int:user_id>")
def get_user(user_id):
    user = db.session.scalar(
        db.select(User).filter_by(user_id=user_id)
    )
    if user:
        return jsonify({
            "code": 200,
            "data": user.json()
        }), 200

    return jsonify({
        "code": 404,
        "message": f"User {user_id} not found."
    }), 404
