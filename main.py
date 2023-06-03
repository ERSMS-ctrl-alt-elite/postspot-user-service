import os
import logging
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, session, redirect, request, make_response, jsonify
import jwt

from postspot.data_gateway import FirestoreGateway, User
from postspot.config import Config
from postspot.auth import OpenIDSession
from postspot.constants import Environment, AccountStatus

# ---------------------------------------------------------------------------- #
#                                   App init                                   #
# ---------------------------------------------------------------------------- #

env = Environment(os.environ["ENV"]) if "ENV" in os.environ else Environment.PRODUCTION

config = Config(env)

logging.basicConfig(
    level=config.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

logger.info(f"Running application in {env.value} environment")
app = Flask("PostSpot User Service")
app.secret_key = "PostSpot123"
app.config["SQLALCHEMY_DATABASE_URI"] = config.database_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

data_gateway = FirestoreGateway()

openid_session = OpenIDSession(env=env)


def token_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            bearer = request.headers.get("Authorization")
            token = bearer.split()[1]

        if not token:
            return jsonify({"message": "Token not provided"}), 401

        try:
            openid_session.from_token(token)

            token_issued_at_datetime = datetime.fromtimestamp(
                openid_session.token_issued_at_time
            )
            token_exp_datetime = datetime.fromtimestamp(
                openid_session.token_expiry_time
            )
            logger.debug(
                "Token issued at"
                f" {token_issued_at_datetime} ({openid_session.token_issued_at_time})"
            )
            logger.debug(
                "Token expires at"
                f" {token_exp_datetime} ({openid_session.token_expiry_time})"
            )

            current_user = data_gateway.read_user(openid_session.google_id)
        except Exception as e:
            logger.error(f"Invalid token: {e}")
            return jsonify({"message": "Invalid token"}), 401

        return function(current_user, *args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------- #
#                                   Endpoints                                  #
# ---------------------------------------------------------------------------- #


@app.route("/signup")
def signup():
    authentication_url, state = openid_session.get_authentication_url_and_state()
    session["state"] = state
    session["signup"] = True
    return redirect(authentication_url)


@app.route("/credentials", methods=["GET"])
def login():
    authentication_url, state = openid_session.get_authentication_url_and_state()
    session["state"] = state
    return redirect(authentication_url)


@app.route("/callback")
def callback():
    openid_session.authenticate(request)

    if "signup" in session:
        if data_gateway.user_exists(openid_session.google_id):
            logger.error(
                f"User {openid_session.name} (google_id={openid_session.google_id})"
                " already signed up"
            )
            return f"User {openid_session.name} already signed up", 422

        data_gateway.add_user(
            google_id=openid_session.google_id,
            name=openid_session.name,
            email=openid_session.email,
            account_status=AccountStatus.OPEN,
        )
        session.pop("signup")
    else:
        if not data_gateway.user_exists(openid_session.google_id):
            logger.error(
                f"User {openid_session.name} (google_id={openid_session.google_id}) not"
                " signed up"
            )
            return f"User {openid_session.name} not signed up", 422

    logger.debug(f"creds={openid_session._flow.credentials}")
    logger.debug(f"access_token={openid_session._flow.credentials.token}")

    return make_response(jsonify({"token": openid_session._flow.credentials.id_token}))


@app.route("/")
def index():
    if "signup" in session:
        session.pop("signup")
    return (
        "Hello World <br> <a href='/signup'><button>Sign up</button></a> <br> <a"
        " href='/login'><button>Login</button></a>"
    )


@app.route("/protected_area")
@token_required
def protected_area(current_user: User):
    return (
        f"Hello {current_user.name}! <br/> <a"
        " href='/logout'><button>Logout</button></a>"
    )


if __name__ == "__main__":
    debug = env != Environment.PRODUCTION
    app.run(debug=debug)
