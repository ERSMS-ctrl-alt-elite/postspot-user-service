import os
import logging
import requests
import re

from google.oauth2 import id_token
from google.auth import exceptions
import google.auth.transport.requests
from pip._vendor import cachecontrol

from postspot.constants import AUTH_HEADER_NAME


logger = logging.getLogger(__name__)


def decode_openid_token(token) -> tuple:
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    logger.debug(f"{request_session=} {cached_session=} {token_request=}")

    try:
        id_info = id_token.verify_oauth2_token(
            id_token=token, request=token_request, audience=os.environ["CLIENT_ID"]
        )
    except exceptions.GoogleAuthError as e:
        id_info = id_token.verify_firebase_token(
            id_token=token, request=token_request, audience="postspot-prod"
        )

    logger.debug(f"{id_info=}")

    google_id = id_info.get("sub")
    name = id_info.get("name")
    email = id_info.get("email")
    token_issue_t = id_info.get("iat")
    token_expired_t = id_info.get("exp")

    return (google_id, name, email, token_issue_t, token_expired_t)


def get_token(request: requests.Request) -> str | None:
    token = None
    auth_header = request.headers.get(AUTH_HEADER_NAME)
    if re.fullmatch('Bearer\s.*', auth_header):
        token = auth_header.split()[1]
    return token
