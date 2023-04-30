import os
import logging

from flask import Flask, session, redirect, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from postspot.config import Config
from postspot.auth import OpenIDSession
from postspot.constants import Environment

# ---------------------------------------------------------------------------- #
#                                   App init                                   #
# ---------------------------------------------------------------------------- #

env = Environment(os.environ["ENV"]) if "ENV" in os.environ else Environment.PRODUCTION

config = Config(env)

logging.basicConfig(
    level=config.log_level, format="%(relativeCreated)6d %(threadName)s %(message)s"
)
logger = logging.getLogger(__name__)

logger.info(f"Running application in {env} environment")
app = Flask("PostSpot User Service")
app.secret_key = "PostSpot123"
app.config["SQLALCHEMY_DATABASE_URI"] = config.database_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True

db = SQLAlchemy(app)
migrate = Migrate(app, db)

openid_session = OpenIDSession(env=env)


def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper


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

    return redirect("/protected_area")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/")
def index():
    return (
        "Hello World <br> <a href='/signup'><button>Sign up</button></a> <br> <a"
        " href='/login'><button>Login</button></a>"
    )


@app.route("/protected_area")
@login_is_required
def protected_area():
    return (
        f"Hello {session['name']}! <br/> <a href='/logout'><button>Logout</button></a>"
    )


if __name__ == "__main__":
    debug = env != Environment.PRODUCTION
    app.run(debug=debug)
