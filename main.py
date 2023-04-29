import logging

from flask import Flask, session, redirect, request

from postspot.config import Config
from postspot.auth import OAuth2Session, login_is_required

# ---------------------------------------------------------------------------- #
#                                   App init                                   #
# ---------------------------------------------------------------------------- #

config = Config()

logging.basicConfig(
    level=config.log_level, format="%(relativeCreated)6d %(threadName)s %(message)s"
)

app = Flask("Google Login App")
app.secret_key = "CodeSpecialist.com"

oauth2_session = OAuth2Session(is_development=app.debug)

# ---------------------------------------------------------------------------- #
#                                   Endpoints                                  #
# ---------------------------------------------------------------------------- #


@app.route("/login")
def login():
    authorization_url, state = oauth2_session.get_authorization_url_and_state()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    oauth2_session.fetch_token(request)
    oauth2_session.verify_token()
    return redirect("/protected_area")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/")
def index():
    return "Hello World <a href='/login'><button>Login</button></a>"


@app.route("/protected_area")
@login_is_required
def protected_area():
    return (
        f"Hello {session['name']}! <br/> <a href='/logout'><button>Logout</button></a>"
    )


if __name__ == "__main__":
    app.run(debug=True)
