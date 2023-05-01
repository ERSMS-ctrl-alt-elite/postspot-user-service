from enum import Enum


class Environment(Enum):
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    LOCAL = "local"
    DB_ONLY = "db_only"
