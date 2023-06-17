import os
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify
from flask_swagger_ui import get_swaggerui_blueprint

from postspot.data_gateway import FirestoreGateway, User
from postspot.config import Config
from postspot.auth import decode_openid_token
from postspot.constants import Environment, AccountStatus

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
        token = None

        if "Authorization" in request.headers:
            bearer = request.headers.get("Authorization")
            token = bearer.split()[1]

        if not token:
            return jsonify({"message": "Token not provided"}), 401

        try:
            (
                google_id,
                name,
                email,
                token_issued_t,
                token_expired_t,
            ) = decode_openid_token(token)

            token_issued_at_datetime = datetime.fromtimestamp(token_issued_t)
            token_exp_datetime = datetime.fromtimestamp(token_expired_t)
            logger.debug(
                f"Token issued at {token_issued_at_datetime} ({token_issued_t})"
            )
            logger.debug(f"Token expires at {token_exp_datetime} ({token_expired_t})")

            try:
                current_user = data_gateway.read_user(google_id)
            except Exception as e:
                logger.error(f"User not signed up: {e}")
                return jsonify({"message": "Invalid token or user not signed up"}), 401
        except Exception as e:
            logger.error(f"Invalid token: {e}")
            return jsonify({"message": "Invalid token or user not signed up"}), 401

        return function(current_user, *args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------- #
#                                   Endpoints                                  #
# ---------------------------------------------------------------------------- #


@app.route("/")
def index():
    return "Hello from PostSpot's user service"


@app.route("/signup", methods=["POST"])
def signup():
    token = None

    if "Authorization" in request.headers:
        bearer = request.headers.get("Authorization")
        token = bearer.split()[1]

    if not token:
        return jsonify({"message": "Token not provided"}), 401

    logger.debug(f"{token=}")

    google_id, name, email, token_issued_t, token_expired_t = decode_openid_token(token)

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


@app.route("/protected_area", methods=["GET"])
@user_signed_up
def protected_area(current_user: User):
    return f"Hello {current_user.name}!"


@app.route("/debug/firestore/add", methods=["POST"])
def debug_firestore_add():
    data_gateway.add_user("123", "TestUser", "test@gmail.com", AccountStatus.OPEN)
    return "TestUser added", 201


@app.route("/debug/firestore/get", methods=["GET"])
def debug_firestore_get():
    return str(data_gateway.read_user("123"))


@app.route("/test_endpoint1")
def test_endpoint1():
    return "Hello from test endpoint 1"


# TODO @user_signed_up
@app.route("/api/v1/users/<follower_google_id>/followees", methods=["POST", "GET"])
def follow_user(follower_google_id):
    if request.method == "POST":
        if "google_id" in request.json:
            followee_google_id = request.json["google_id"]
            # TODO add user verification
            data_gateway.follow_user(follower_google_id, followee_google_id)
        else:
            return "body must contain google_id", 400
    return data_gateway.read_user(follower_google_id).followees


# TODO @user_signed_up
@app.route("/api/v1/users/<follower_google_id>/followees/<followee_google_id>", methods=["DELETE"])
def delete_followee(follower_google_id, followee_google_id):
    # TODO verify follower_google_id with openid token
    data_gateway.unfollow_user(follower_google_id, followee_google_id)
    return "User unfollowed", 204


if __name__ == "__main__":
    debug = env != Environment.PRODUCTION
    app.run(debug=debug, port=8080)
