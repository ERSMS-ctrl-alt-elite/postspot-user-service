import logging
from abc import ABC, abstractmethod
from typing import List

from google.cloud import firestore

from postspot.constants import AccountStatus


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------- #
#                                   Interface                                  #
# ---------------------------------------------------------------------------- #


class UserNotFoundError(Exception):
    def __init__(self, google_id: str):
        super().__init__(f"User with google_id={google_id} not found")


class User:
    def __init__(
        self,
        google_id: str = None,
        name: str = None,
        email: str = None,
        account_status: AccountStatus = None,
        followees = []
    ):
        self.google_id = google_id
        self.name = name
        self.email = email
        self.account_status = account_status
        self.followees = followees

    @staticmethod
    def from_dict(source):
        return User(
            source.get("google_id"),
            source.get("name"),
            source.get("email"),
            AccountStatus(source.get("account_status")),
            source.get("followees")
        )

    def to_dict(self) -> dict:
        return {
            "google_id": self.google_id,
            "name": self.name,
            "email": self.email,
            "account_status": self.account_status.value,
            "followees": self.followees,
        }

    def __repr__(self):
        return f"""User(
    google_id={self.google_id},
    name={self.name},
    email={self.email},
    account_status={self.account_status.value},
)
"""


class DataGateway(ABC):
    @abstractmethod
    def add_user(self, google_id: str, name: str, email: str):
        pass

    @abstractmethod
    def read_user(self, google_id: str) -> User:
        pass

    @abstractmethod
    def user_exists(self, google_id: str) -> bool:
        pass

    @abstractmethod
    def follow_user(self, follower_google_id: str, followee_google_id):
        pass

    @abstractmethod
    def unfollow_user(self, follower_google_id: str, followee_google_id):
        pass


# ---------------------------------------------------------------------------- #
#                                   Firestore                                  #
# ---------------------------------------------------------------------------- #


class FirestoreGateway(DataGateway):
    def __init__(self):
        self._db = firestore.Client()

    def add_user(
        self, google_id: str, name: str, email: str, account_status: AccountStatus
    ):
        logger.debug(f"Adding user with {google_id=} {name=} {email=}")
        doc_ref = self._db.collection("users").document(google_id)
        doc_ref.set(User(google_id, name, email, account_status).to_dict())
        logger.debug("User added")

    def read_user(self, google_id: str) -> User:
        logger.debug(f"Reading user {google_id}")
        doc_ref = self._db.collection("users").document(google_id)
        doc = doc_ref.get()

        if doc.exists:
            logger.debug("User found")
            return User.from_dict(doc.to_dict())

        raise UserNotFoundError(google_id)

    def user_exists(self, google_id: str) -> bool:
        doc_ref = self._db.collection("users").document(google_id)
        doc = doc_ref.get()
        return doc.exists

    def follow_user(self, follower_google_id: str, followee_google_id):
        doc_ref = self._db.collection("users").document(follower_google_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise UserNotFoundError(follower_google_id)
        
        user = User.from_dict(doc.to_dict())
        followees_set = set(user.followees)
        followees_set.add(followee_google_id)
        user.followees = followees_set
        doc_ref.set(user.to_dict())


    def unfollow_user(self, follower_google_id: str, followee_google_id):
        doc_ref = self._db.collection("users").document(follower_google_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise UserNotFoundError(follower_google_id)
        
        user = User.from_dict(doc.to_dict())
        user.followees.remove(followee_google_id)
        doc_ref.set(user.to_dict())
