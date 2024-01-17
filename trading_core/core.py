import os
from dotenv import load_dotenv
from datetime import datetime
import logging

from .constants import Const

load_dotenv()

logger_format = os.getenv("LOGGER_FORMAT")
if not logger_format:
    logger_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

logging.basicConfig(
    level=logging.INFO,
    format=logger_format,
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger("core")


class Config:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.__config_data = {Const.CONFIG_DEBUG_LOG: True}
        return class_._instance

    def get_config_value(self, property: str):
        if property and property in self.__config_data:
            return self.__config_data[property]
        else:
            None

    def get_env_value(self, property: str) -> str:
        env_value = os.getenv(property)
        if not env_value:
            logger.error(
                f"{self.__class__.__name__}: Property {property} isn't maintained in the environment values"
            )
        return env_value


config = Config()
