import logging
from abc import ABC, abstractmethod
from typing import Iterable, List

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
    ):
        self.google_id = google_id
        self.name = name
        self.email = email
        self.account_status = account_status

    @staticmethod
    def from_dict(source):
        return User(
            source.get("google_id"),
            source.get("name"),
            source.get("email"),
            AccountStatus(source.get("account_status")),
        )

    def to_dict(self) -> dict:
        return {
            "google_id": self.google_id,
            "name": self.name,
            "email": self.email,
            "account_status": self.account_status.value,
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
        follower_ref = self._db.collection("users").document(follower_google_id)
        followee_ref = self._db.collection("users").document(followee_google_id)
        transaction = self._db.transaction()

        @firestore.transactional
        def check_users_exist_and_follow(transaction, follower_ref, followee_ref):
            follower_doc = follower_ref.get(transaction=transaction)
            if not follower_doc.exists:
                raise UserNotFoundError(follower_google_id)

            followee_doc = followee_ref.get(transaction=transaction)
            if not followee_doc.exists:
                raise UserNotFoundError(followee_google_id)

            transaction.set(
                followee_ref.collection("followers").document(follower_google_id),
                {"exists": True},
            )

            transaction.set(
                follower_ref.collection("followees").document(followee_google_id),
                {"exists": True},
            )

        check_users_exist_and_follow(transaction, follower_ref, followee_ref)

    def unfollow_user(self, follower_google_id: str, followee_google_id):
        follower_ref = self._db.collection("users").document(follower_google_id)
        followee_ref = self._db.collection("users").document(followee_google_id)
        transaction = self._db.transaction()

        @firestore.transactional
        def delete_follow(transaction, follower_ref, followee_ref):
            transaction.delete(
                follower_ref.collection("followers").document(followee_google_id)
            )
            transaction.delete(
                followee_ref.collection("followees").document(follower_google_id)
            )

        delete_follow(transaction, follower_ref, followee_ref)

    def _get_users_names_and_id(self, users: Iterable):
        if not users:
            return []
        query = self._db.collection("users").where('google_id', "in", users).stream()
        return {"user": [User.from_dict(user_doc.to_dict()).to_dict() for user_doc in query]}

    def read_user_followers(self, user_google_id: str):
        followers = (
            self._db.collection("users")
            .document(user_google_id)
            .collection("followers")
            .list_documents()
        )
        return self._get_users_names_and_id([follower.id for follower in followers])
         
    def read_user_followees(self, user_google_id: str):
        followees = (
            self._db.collection("users")
            .document(user_google_id)
            .collection("followees")
            .list_documents()
        )
        return self._get_users_names_and_id([followee.id for followee in followees])
