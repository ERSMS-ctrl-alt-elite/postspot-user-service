import os

from flask import Flask, redirect, request, make_response, jsonify

import os
import json
import logging
import requests

from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
import google.auth.transport.requests
from pip._vendor import cachecontrol

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
client_config = json.loads(os.environ["GOOGLE_AUTH_CLIENT_SECRET"])
scopes = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]
flow = Flow.from_client_config(
    client_config=client_config,
    scopes=scopes,
    redirect_uri="http://localhost:5000/callback",
)

app = Flask("PostSpot User Service")
app.secret_key = "PostSpot123"


@app.route("/")
def index():
    return redirect(flow.authorization_url()[0])


@app.route("/callback")
def callback():
    client_id = (
        "1004315401260-cdpumuia14gvmqakrfsq7oim7hkbj6di.apps.googleusercontent.com"
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)
    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=client_id,
    )
    return make_response(jsonify({"token": flow.credentials.id_token}))


if __name__ == "__main__":
    app.run(port=5000)
