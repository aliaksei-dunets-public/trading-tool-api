import pandas_ta as ta
import pandas as pd

from .constants import Const
from .core import logger, config, Const
from .common import (
    IndicatorType,
    IndicatorParamModel,
    HistoryDataParamModel,
    HistoryDataModel,
)
from .handler import buffer_runtime_handler


class IndicatorBase:
    """The base class for all technical indicators."""

    def __init__(self):
        """Initialize the indicator with an empty code and name."""
        self._code: IndicatorType = ""
        self._name = ""

    def get_code(self) -> str:
        """Return the code of the indicator."""
        return self._code

    def get_name(self) -> str:
        """Return the name of the indicator."""
        return self._name

    def get_indicator(self, param: IndicatorParamModel) -> HistoryDataModel:
        """
        Get the indicator for a specific symbol, interval, and time period.
        """
        history_data_param = HistoryDataParamModel(**param.model_dump())

        return buffer_runtime_handler.get_history_data_handler(
            trader_id=param.trader_id
        ).get_history_data(history_data_param)

    def get_indicator_by_history_data(
        self, history_data_mdl: HistoryDataModel
    ) -> pd.DataFrame:
        """
        Get the indicator for a specific historical data object.
        """
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"{self.__class__.__name__}: get_indicator_by_history_data({history_data_mdl.print_model()})"
            )

        return history_data_mdl.data


class Indicator_CCI(IndicatorBase):
    """A class for the Commodity Channel Index (CCI) technical indicator."""

    def __init__(self, length: int):
        """
        Initialize the CCI indicator with a specific length.
        """
        # Initialize the base class
        IndicatorBase.__init__(self)
        # Set the code and name of the indicator
        self._code = IndicatorType.CCI.name
        self._name = "Commodity Channel Index"

        # Set the length of the indicator (number of periods)
        self.__length = int(length)

    def get_length(self) -> int:
        """Return the length of the CCI indicator."""
        return self.__length

    def get_indicator(self, param: IndicatorParamModel) -> pd.DataFrame:
        """
        Get the CCI indicator for a specific symbol, interval, and time period.
        """
        # Calculate the default limit to ensure there is enough data to calculate the indicator
        default_length = self.__length + 2

        # If the given limit is less than the default limit, use the default limit instead
        param.limit += default_length

        # Get the historical data for the given symbol and interval up to the given limit
        history_data_mdl = super().get_indicator(param)

        # Calculate the indicator based on the historical data and return it
        return self.get_indicator_by_history_data(history_data_mdl)

    def get_indicator_by_history_data(
        self, history_data_mdl: HistoryDataModel
    ) -> pd.DataFrame:
        """
        Get the CCI indicator for a specific historical data object.
        """
        # Get the historical data as a pandas DataFrame
        history_data = super().get_indicator_by_history_data(history_data_mdl)

        # Check if there is enough historical data to calculate the indicator
        if history_data.shape[0] < self.__length:
            # If there is not enough historical data, raise an exception
            logger.error(
                f"{self.__class__.__name__}: Count of history data less then indicator interval {self.__length}"
            )
            raise Exception(
                f"{self.__class__.__name__}: Count of history data less then indicator interval {self.__length}"
            )

        # Calculate the Commodity Channel Index using the length specified in the constructor
        cci_series = history_data.ta.cci(length=self.__length)

        # Convert the series to a DataFrame with the indicator code as the column name
        cci_df = cci_series.to_frame(name=self._code)

        # Join the indicator DataFrame with the historical data DataFrame
        indicator_df = history_data.join(cci_df)

        # Drop rows with missing values (NaNs) in the indicator column
        indicator_df = indicator_df.dropna(subset=[self._code])

        # Return the indicator DataFrame
        return indicator_df
