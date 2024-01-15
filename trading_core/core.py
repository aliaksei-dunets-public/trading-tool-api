import os
from dotenv import load_dotenv
from datetime import datetime
import logging

# from logging.handlers import TimedRotatingFileHandler

from .constants import Const

load_dotenv()

# Set up logging
log_file_prefix = f"{os.getcwd()}/static/logs/"
log_file_suffix = ".log"
date_format = "%Y-%m-%d"
current_date = datetime.utcnow().strftime(date_format)
log_file_name = log_file_prefix + current_date + log_file_suffix

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        # TimedRotatingFileHandler(log_file_name, when='midnight', backupCount=7),
        logging.StreamHandler()
    ],
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
