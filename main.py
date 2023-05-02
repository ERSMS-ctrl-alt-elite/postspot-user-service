import os
import logging
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, session, redirect, request, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import jwt

from postspot.config import Config
from postspot.auth import OpenIDSession
from postspot.constants import Environment

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

db = SQLAlchemy(app)
migrate = Migrate(app, db)

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
            logger.debug(token)
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            logger.debug(data)
            current_user = User.query.filter_by(google_id=data["google_id"]).first()
        except Exception as e:
            logger.error(f"Invalid token: {e}")
            return jsonify({"message": "Invalid token"}), 401

        return function(current_user, *args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------- #
#                                    Models                                    #
# ---------------------------------------------------------------------------- #


class User(db.Model):
    google_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(70), unique=True)


# ---------------------------------------------------------------------------- #
#                                   Endpoints                                  #
# ---------------------------------------------------------------------------- #


@app.route("/signup")
def signup():
    authentication_url, state = openid_session.get_authentication_url_and_state()
    session["state"] = state
    session["signup"] = True
    return redirect(authentication_url)


@app.route("/login")
def login():
    authentication_url, state = openid_session.get_authentication_url_and_state()
    session["state"] = state
    return redirect(authentication_url)


@app.route("/callback")
def callback():
    openid_session.authenticate(request)

    if "signup" in session:
        user = User.query.get(openid_session.google_id)
        if user:
            logger.error(
                f"User {openid_session.name} (google_id={openid_session.google_id})"
                " already signed up"
            )
            return f"User {openid_session.name} already signed up", 422

        user = User(
            google_id=openid_session.google_id,
            name=openid_session.name,
            email=openid_session.email,
        )
        db.session.add(user)
        db.session.commit()
        session.pop("signup")
    else:
        user = User.query.get(openid_session.google_id)
        if not user:
            logger.error(
                f"User {openid_session.name} (google_id={openid_session.google_id}) not"
                " signed up"
            )
            return f"User {openid_session.name} not signed up", 422

    token = jwt.encode(
        {
            "google_id": openid_session.google_id,
            "name": openid_session.name,
            "exp": datetime.utcnow() + timedelta(minutes=30),
        },
        app.config["SECRET_KEY"],
    )

    return make_response(jsonify({"token": token}))


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


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
