import pandas_ta as ta
import pandas as pd

from .constants import Const
from .core import logger, config, Const, HistoryData
from .model import model


class IndicatorBase():
    """The base class for all technical indicators."""

    def __init__(self):
        """Initialize the indicator with an empty code and name."""
        self._code = ''
        self._name = ''

    def get_code(self) -> str:
        """Return the code of the indicator."""
        return self._code

    def get_name(self) -> str:
        """Return the name of the indicator."""
        return self._name

    def get_indicator(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> HistoryData:
        """
        Get the indicator for a specific symbol, interval, and time period.

        Parameters:
        symbol (str): The symbol for which to retrieve the indicator.
        interval (str): The interval of the data (e.g. '1d' for daily data).
        limit (int): The number of data points to retrieve.
        from_buffer(bool): Indicator for detect that the data should be retrieved from buffer firstly
        closed_bars(bool): Indicator for detect that the data should be retrieved for closed bar only

        Returns:
        HistoryData: The historical data for the symbol, interval, and time period.
        """
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f'INDICATOR: {self._code} - get_indicator(symbol={symbol}, interval={interval}, limit={limit}, from_buffer={from_buffer}, closed_bars={closed_bars})')

        return model.get_handler().getHistoryData(symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)

    def get_indicator_by_history_data(self, history_data_inst: HistoryData) -> pd.DataFrame:
        """
        Get the indicator for a specific historical data object.

        Parameters:
        history_data_inst (HistoryData): The historical data for which to calculate the indicator.

        Returns:
        DataFrame: A pandas DataFrame containing the indicator data.
        """
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f'INDICATOR: {self._code} - get_indicator_by_history_data(symbol={history_data_inst.getSymbol()}, interval={history_data_inst.getInterval()}, limit={history_data_inst.getLimit()}, endDatetime={history_data_inst.getEndDateTime()})')

        return history_data_inst.getDataFrame()


class Indicator_CCI(IndicatorBase):
    """A class for the Commodity Channel Index (CCI) technical indicator."""

    def __init__(self, length: int):
        """
        Initialize the CCI indicator with a specific length.

        Parameters:
        length (int): The length of the CCI indicator.
        """
        # Initialize the base class
        IndicatorBase.__init__(self)
        # Set the code and name of the indicator
        self._code = Const.TA_INDICATOR_CCI
        self._name = 'Commodity Channel Index'

        # Set the length of the indicator (number of periods)
        self.__length = int(length)

    def get_length(self) -> int:
        """Return the length of the CCI indicator."""
        return self.__length

    def get_indicator(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> pd.DataFrame:
        """
        Get the CCI indicator for a specific symbol, interval, and time period.

        Parameters:
        symbol (str): The symbol for which to retrieve the CCI indicator.
        interval (str): The interval of the data (e.g. '1d' for daily data).
        limit (int): The number of data points to retrieve.
        from_buffer(bool): Indicator for detect that the data should be retrieved from buffer firstly
        closed_bars(bool): Indicator for detect that the data should be retrieved for closed bar only

        Returns:
        DataFrame: A pandas DataFrame containing the CCI indicator data.
        """
        # Calculate the default limit to ensure there is enough data to calculate the indicator
        default_length = self.__length + 2

        # If the given limit is less than the default limit, use the default limit instead
        limit = limit if limit > default_length else default_length

        # Get the historical data for the given symbol and interval up to the given limit
        history_data_inst = super().get_indicator(symbol=symbol, interval=interval,
                                                  limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)

        # Calculate the indicator based on the historical data and return it
        return self.get_indicator_by_history_data(history_data_inst)

    def get_indicator_by_history_data(self, history_data_inst: HistoryData) -> pd.DataFrame:
        """
        Get the CCI indicator for a specific historical data object.

        Parameters:
        history_data_inst (HistoryData): The historical data for which to calculate the CCI indicator.

        Returns:
        DataFrame: A pandas DataFrame containing the CCI indicator data.
        """
        # Get the historical data as a pandas DataFrame
        history_DataFrame = super().get_indicator_by_history_data(history_data_inst)

        # Check if there is enough historical data to calculate the indicator
        if history_DataFrame.shape[0] < self.__length:
            # If there is not enough historical data, raise an exception
            raise Exception(
                f'Count of history data less then indicator interval {self.__length}')

        # Calculate the Commodity Channel Index using the length specified in the constructor
        cci_series = history_DataFrame.ta.cci(length=self.__length)

        # Convert the series to a DataFrame with the indicator code as the column name
        cci_df = cci_series.to_frame(name=self._code)

        # Join the indicator DataFrame with the historical data DataFrame
        indicator_df = history_DataFrame.join(cci_df)

        # Drop rows with missing values (NaNs) in the indicator column
        indicator_df = indicator_df.dropna(subset=[self._code])

        # Return the indicator DataFrame
        return indicator_df
