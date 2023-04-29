import os
import json
import logging
import requests

from flask import Flask, session, abort, request, Request
from google_auth_oauthlib.flow import Flow
from google.cloud import secretmanager
from google.oauth2 import id_token
import google.auth.transport.requests
from pip._vendor import cachecontrol


logger = logging.getLogger(__name__)


PROJECT_ID = "mystic-stack-382412"


def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper


def __access_secret_version(secret_id, version_id="latest"):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"

    # Access the secret version.
    response = client.access_secret_version(name=name)

    # Return the decoded payload.
    return response.payload.data.decode("UTF-8")


class OAuth2Session:
    def __init__(self, is_development: bool = False):
        scopes = [
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ]

        if is_development:
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
            self._flow = Flow.from_client_secrets_file(
                client_secrets_file="../client_secret.json",
                scopes=scopes,
                redirect_uri="http://localhost:5000/callback",
            )
            self._client_id = "1004315401260-cdpumuia14gvmqakrfsq7oim7hkbj6di.apps.googleusercontent.com"
        else:
            client_config = json.loads(
                __access_secret_version("GOOGLE_AUTH_CLIENT_SECRET")
            )
            self._flow = Flow.from_client_config(
                client_config=client_config,
                scopes=scopes,
                redirect_uri="https://mystic-stack-382412.lm.r.appspot.com/callback",
            )
            self._client_id = client_config["web"]["client_id"]

    def get_authorization_url_and_state(self) -> tuple:
        return self._flow.authorization_url()

    def fetch_token(self, request: Request):
        logger.debug(f"Fetching OAuth2 token (authorization_response={request.url})")
        self._flow.fetch_token(authorization_response=request.url)
        logger.debug("OK: OAuth2 token fetched successfully")

        if not session["state"] == request.args["state"]:
            logger.error(
                f"State does not match: {session['state']=} != {request.args['state']=}"
            )
            abort(500)  # State does not match!

    def verify_token(self):
        credentials = self._flow.credentials
        request_session = requests.session()
        cached_session = cachecontrol.CacheControl(request_session)
        token_request = google.auth.transport.requests.Request(session=cached_session)

        logger.debug("Verifying OAuth2 token")
        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=self._client_id,
        )
        logger.debug("OK: OAuth2 token verified")

        session["google_id"] = id_info.get("sub")
        session["name"] = id_info.get("name")
