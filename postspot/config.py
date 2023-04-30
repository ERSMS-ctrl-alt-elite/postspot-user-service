import configparser

from postspot.constants import Environment


class Config:
    def __init__(self, env: Environment):
        self._env = env
        self._config = configparser.ConfigParser()
        self._config.read("config.ini")

    @property
    def log_level(self) -> str:
        return self._config["DEFAULT"]["log_level"]

    @property
    def database_uri(self) -> str:
        if self._env == Environment.LOCAL:
            return "sqlite:///Database.db"
        return "mysql+pymysql://root:mvYHY`61kfCtB892@/mysql?unix_socket=/cloudsql/mystic-stack-382412:europe-central2:test-instance"
