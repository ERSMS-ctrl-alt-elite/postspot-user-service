import configparser


class Config:
    def __init__(self):
        self._config = configparser.ConfigParser()
        self._config.read("config.ini")

    @property
    def log_level(self) -> str:
        return self._config["DEFAULT"]["log_level"]
