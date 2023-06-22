import os
import logging
from datetime import datetime
from functools import wraps
import re

from flask import Flask, request, jsonify
from flask_swagger_ui import get_swaggerui_blueprint
from google.auth import exceptions

from postspot.data_gateway import FirestoreGateway, User, UserNotFoundError
from postspot.config import Config
from postspot.auth import decode_openid_token, get_token
from postspot.constants import Environment, AccountStatus, AUTH_HEADER_NAME

# ---------------------------------------------------------------------------- #
#                                   App init                                   #
# ---------------------------------------------------------------------------- #

env = Environment(os.environ["ENV"]) if "ENV" in os.environ else Environment.PRODUCTION

config = Config(env)

# ----------------------------- Configure logging ---------------------------- #
logging.basicConfig(
    level=config.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------- Create an app ------------------------------ #
logger.info(f"Running application in {env.value} environment")
app = Flask("PostSpot User Service")
app.secret_key = "PostSpot123"

# -------------------------- Create database gateway ------------------------- #
data_gateway = FirestoreGateway()

# --------------------------- Configure Swagger UI --------------------------- #
SWAGGER_URL = "/swagger"
API_URL = "/static/swagger.json"
SWAGGERUI_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL, API_URL, config={"app_name": "Seans-Python-Flask-REST-Boilerplate"}
)
app.register_blueprint(SWAGGERUI_BLUEPRINT, url_prefix=SWAGGER_URL)


def user_signed_up(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if AUTH_HEADER_NAME not in request.headers:
            return jsonify({"message": "Token not provided"}), 401
        
        token = get_token(request)
        if not token:
            return jsonify({"message": "Invalid token"}), 401

        try:
            (
                google_id,
                name,
                email,
                token_issued_t,
                token_expired_t,
            ) = decode_openid_token(token)
        except exceptions.GoogleAuthError as e:
            logger.error(f"Invalid token - issuer invalid: {e}")
            return jsonify({"message": "Invalid token or user not signed up"}), 401
        except ValueError as e:
            logger.error(f"Invalid token: {e}")
            return jsonify({"message": "Invalid token or user not signed up"}), 401

        token_issued_at_datetime = datetime.fromtimestamp(token_issued_t)
        token_exp_datetime = datetime.fromtimestamp(token_expired_t)
        logger.debug(
            f"Token issued at {token_issued_at_datetime} ({token_issued_t})"
        )
        logger.debug(f"Token expires at {token_exp_datetime} ({token_expired_t})")

        if data_gateway.user_exists(google_id):
            current_user = data_gateway.read_user(google_id)
        else:
            logger.error(f"User not signed up: {e}")
            return jsonify({"message": "Invalid token or user not signed up"}), 401
        
        return function(current_user, *args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------- #
#                                   Endpoints                                  #
# ---------------------------------------------------------------------------- #


@app.route("/v1/")
def index():
    return "Hello from PostSpot's user service"


@app.route("/v1/users", methods=["POST"])
def signup():
    if AUTH_HEADER_NAME not in request.headers:
        return jsonify({"message": "Token not provided"}), 401
    
    token = get_token(request)
    if not token:
        return jsonify({"message": "Invalid token"}), 401

    logger.debug(f"{token=}")

    try:
        (
            google_id,
            name,
            email,
            token_issued_t,
            token_expired_t,
        ) = decode_openid_token(token)
    except exceptions.GoogleAuthError as e:
        logger.error(f"Invalid token - issuer invalid: {e}")
        return jsonify({"message": "Invalid token or user not signed up"}), 401
    except ValueError as e:
        logger.error(f"Invalid token: {e}")
        return jsonify({"message": "Invalid token or user not signed up"}), 401

    if data_gateway.user_exists(google_id):
        logger.error(f"User {name} (google_id={google_id}) already signed up")
        return f"User {name} already signed up", 422

    data_gateway.add_user(
        google_id=google_id,
        name=name,
        email=email,
        account_status=AccountStatus.OPEN,
    )

    return f"User {name} created", 201


@app.route("/v1/users/<user_google_id>", methods=["GET"])
def get_user(user_google_id):
    try:
        return data_gateway.read_user(user_google_id).to_dict(), 200
    except UserNotFoundError as e:
        return "User not found", 404


@app.route("/v1/protected_area", methods=["GET"])
@user_signed_up
def protected_area(current_user: User):
    return f"Hello {current_user.name}!"


@app.route("/v1/debug/firestore/add", methods=["POST"])
def debug_firestore_add():
    data_gateway.add_user("magdalut", "Name magdalut", "magdalut@gmail.com", AccountStatus.OPEN)
    return "TestUser added", 201


@app.route("/v1/debug/firestore/get", methods=["GET"])
def debug_firestore_get():
    return str(data_gateway.read_user("123"))


@app.route("/v1/test_endpoint1")
def test_endpoint1():
    return "Hello from test endpoint 1"


@app.route("/v1/users/<followee_google_id>/followers", methods=["POST"])
@user_signed_up
def follow_user(current_user: User, followee_google_id: str):
    follower_google_id = current_user.google_id

    if follower_google_id == followee_google_id:
        return "cannot follow yourself", 400
    data_gateway.follow_user(follower_google_id, followee_google_id)
    return "User followed", 200


@app.route("/v1/users/<followee_google_id>/followers", methods=["GET"])
def get_followers(followee_google_id):
    return data_gateway.read_user_followers(followee_google_id)


@app.route("/v1/users/<follower_google_id>/followees", methods=["GET"])
def get_followees(follower_google_id):
    return data_gateway.read_user_followees(follower_google_id)


@app.route(
    "/v1/users/<followee_google_id>/followers",
    methods=["DELETE"],
)
@user_signed_up
def delete_followee(current_user, followee_google_id):
    follower_google_id = current_user.google_id
    data_gateway.unfollow_user(follower_google_id, followee_google_id)
    return "User unfollowed", 200


if __name__ == "__main__":
    debug = env != Environment.PRODUCTION
    app.run(debug=debug, port=8080)
