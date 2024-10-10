import os
import configparser
import pytest
from unittest import mock
import logging

from trading_core.core import Config, logger
from trading_core.constants import Const


@pytest.fixture
def mock_env():
    with mock.patch.dict(
        os.environ, {"LOGGER_FORMAT": "%(message)s", "SOME_ENV_VAR": "value"}
    ):
        yield


@pytest.fixture
def mock_config_ini():
    mock_config = configparser.ConfigParser()
    mock_config[Config.CONFIG_GROUP_NAME_PROPERTY] = {
        Const.CONF_PROPERTY_DEBUG_LOG: "True",
        Const.CONF_PROPERTY_CORE_LOG: "False",
        "some_other_property": "some_value",
    }
    with mock.patch("trading_core.core.Config._init_config_ini", return_value=None):
        with mock.patch("trading_core.core.Config._config_ini", mock_config):
            yield mock_config


def test_singleton_instance():
    config1 = Config()
    config2 = Config()
    assert config1 is config2  # Test that only one instance exists (singleton)


def test_get_config_value_boolean(mock_config_ini):
    config = Config()
    # Test for boolean config value
    assert config.get_config_value(Const.CONF_PROPERTY_DEBUG_LOG) is True
    assert config.get_config_value(Const.CONF_PROPERTY_CORE_LOG) is False


def test_get_config_value_string(mock_config_ini):
    config = Config()
    # Test for string config value
    assert config.get_config_value("some_other_property") == "some_value"


def test_get_env_value_exists(mock_env):
    config = Config()
    # Test when env var exists
    assert config.get_env_value("SOME_ENV_VAR") == "value"


def test_get_env_value_missing(mock_env, caplog):
    config = Config()
    # Test when env var does not exist and it should log an error
    with caplog.at_level(logging.ERROR):
        assert config.get_env_value("NON_EXISTENT_VAR") is None
        assert (
            "Property NON_EXISTENT_VAR isn't maintained in the environment values"
            in caplog.text
        )


def test_get_config_values(mock_config_ini):
    config = Config()
    # Test retrieval of all config values
    config_values = config.get_config_values()
    assert Const.CONF_PROPERTY_DEBUG_LOG in config_values
    assert config_values[Const.CONF_PROPERTY_DEBUG_LOG] == "True"


def test_update_config_property(mock_config_ini, caplog):
    config = Config()
    # Test updating a config property
    with caplog.at_level(logging.INFO):
        result = config.update_config_property("some_other_property", "new_value")
        assert result is True
        assert "update_config_property(some_other_property, new_value)" in caplog.text
        assert (
            mock_config_ini[Config.CONFIG_GROUP_NAME_PROPERTY]["some_other_property"]
            == "new_value"
        )


def test_update_config(mock_config_ini, caplog):
    config = Config()
    # Test updating the entire config
    new_config = {
        Const.CONF_PROPERTY_DEBUG_LOG: "False",
        Const.CONF_PROPERTY_CORE_LOG: "True",
    }
    with caplog.at_level(logging.INFO):
        result = config.update_config(new_config)
        assert result is True
        assert (
            "update_config({'DEBUG_LOG': 'False', 'CORE_LOG': 'True'})" in caplog.text
        )
        assert config.get_config_value(Const.CONF_PROPERTY_DEBUG_LOG) == False
        assert config.get_config_value(Const.CONF_PROPERTY_CORE_LOG) == True

    # Restore config file to default values
    config.update_config(
        {
            Const.CONF_PROPERTY_DEBUG_LOG: True,
            Const.CONF_PROPERTY_CORE_LOG: True,
            Const.CONF_PROPERTY_API_LOG: True,
            Const.CONF_PROPERTY_HANDLER_LOG: True,
            Const.CONF_PROPERTY_MONGODB_LOG: True,
            Const.CONF_PROPERTY_RESPONSER_LOG: True,
            Const.CONF_PROPERTY_ROBOT_LOG: True,
            Const.CONF_PROPERTY_HIST_SIMULATION_LOG: False,
            "hs_trader_id": "658dab8b3b0719ad3f9b53dd",
        }
    )


def test_update_config_file(mock_config_ini):
    config = Config()
    # Mock file writing
    with mock.patch("builtins.open", mock.mock_open()):
        result = config.update_config(
            mock_config_ini[Config.CONFIG_GROUP_NAME_PROPERTY]
        )
        assert result is True  # Ensure file writing occurs correctly
