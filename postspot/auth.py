__all__ = ["OpenIDSession"]

import os
import json
import logging
import requests

from flask import session, abort, Request
from google_auth_oauthlib.flow import Flow
from google.cloud import secretmanager
from google.oauth2 import id_token
import google.auth.transport.requests
from pip._vendor import cachecontrol

from postspot.constants import Environment


logger = logging.getLogger(__name__)


PROJECT_ID = "mystic-stack-382412"


def _access_secret_version(secret_id, version_id="latest"):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"

    # Access the secret version.
    response = client.access_secret_version(name=name)

    # Return the decoded payload.
    return response.payload.data.decode("UTF-8")


class OpenIDSession:
    def __init__(self, env: Environment = Environment.PRODUCTION):
        self._flow: Flow = None
        self._google_id: str = None
        self._name: str = None
        self._email: str = None

        if env != Environment.BUILD:
            self._initialize_flow(env)

    @property
    def google_id(self) -> str:
        return self._google_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def email(self) -> str:
        return self._email

    def get_authentication_url_and_state(self) -> tuple:
        return self._flow.authorization_url()

    def authenticate(self, request: Request):
        self._fetch_credentials(request)
        self._verify_credentials()

    def _initialize_flow(self, env: Environment):
        scopes = [
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ]

        if env == Environment.LOCAL:
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
            self._flow = Flow.from_client_secrets_file(
                client_secrets_file="../client_secret.json",
                scopes=scopes,
                redirect_uri="http://localhost:5000/callback",
            )
            self._client_id = "1004315401260-cdpumuia14gvmqakrfsq7oim7hkbj6di.apps.googleusercontent.com"
        else:
            client_config = json.loads(
                _access_secret_version("GOOGLE_AUTH_CLIENT_SECRET")
            )
            self._flow = Flow.from_client_config(
                client_config=client_config,
                scopes=scopes,
                redirect_uri="https://mystic-stack-382412.lm.r.appspot.com/callback",
            )
            self._client_id = client_config["web"]["client_id"]

    def _fetch_credentials(self, request: Request):
        logger.debug(f"Fetching OAuth2 token (authorization_response={request.url})")
        self._flow.fetch_token(authorization_response=request.url)
        logger.debug("OK: OAuth2 token fetched successfully")

        if not session["state"] == request.args["state"]:
            logger.error(
                f"State does not match: {session['state']=} != {request.args['state']=}"
            )
            abort(500)  # State does not match!

    def _verify_credentials(self):
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

        self._google_id = id_info.get("sub")
        self._name = id_info.get("name")
        self._email = id_info.get("email")

        session["google_id"] = id_info.get("sub")
        session["name"] = id_info.get("name")
