import os
from dotenv import load_dotenv
import configparser
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
    CONFIG_GROUP_NAME_PROPERTY = "Property"

    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_._config_ini = configparser.ConfigParser()
            class_._init_config_ini(class_)

        return class_._instance

    def _init_config_ini(self):
        self._config_ini.clear()
        self._config_ini.read("config.ini")

    def get_config_value(self, property: str):
        if property in [
            Const.CONF_PROPERTY_DEBUG_LOG,
            Const.CONF_PROPERTY_CORE_LOG,
            Const.CONF_PROPERTY_API_LOG,
            Const.CONF_PROPERTY_HANDLER_LOG,
            Const.CONF_PROPERTY_MONGODB_LOG,
            Const.CONF_PROPERTY_RESPONSER_LOG,
            Const.CONF_PROPERTY_ROBOT_LOG,
            Const.CONF_PROPERTY_HIST_SIMULATION_LOG,
        ]:
            return self._config_ini.getboolean(
                self.CONFIG_GROUP_NAME_PROPERTY, property
            )
        else:
            return self._config_ini.get(self.CONFIG_GROUP_NAME_PROPERTY, property)

    def get_env_value(self, property: str) -> str:
        env_value = os.getenv(property)
        if not env_value:
            logger.error(
                f"{self.__class__.__name__}: Property {property} isn't maintained in the environment values"
            )
        return env_value

    def get_config_values(self):
        return self._config_ini[self.CONFIG_GROUP_NAME_PROPERTY]

    def update_config_property(self, property, value) -> bool:
        logger.info(
            f"{self.__class__.__name__}: update_config_property({property}, {value})"
        )
        self._config_ini[self.CONFIG_GROUP_NAME_PROPERTY][property] = str(value)

        return self.update_config(self._config_ini[self.CONFIG_GROUP_NAME_PROPERTY])

    def update_config(self, config_payload: dict = None) -> bool:
        if config_payload:
            logger.info(f"{self.__class__.__name__}: update_config({config_payload})")
            self._config_ini[self.CONFIG_GROUP_NAME_PROPERTY] = config_payload

        with open("config.ini", "w") as configfile:
            self._config_ini.write(configfile)
        self._init_config_ini()
        return True


config = Config()
