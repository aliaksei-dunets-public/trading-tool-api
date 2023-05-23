import pandas_ta as ta

from .core import HistoryData
from .model import config


class IndicatorBase():
    """The base class for all technical indicators."""

    def __init__(self):
        """Initialize the indicator with an empty code and name."""
        self._code = ''
        self._name = ''

    def getCode(self):
        """Return the code of the indicator."""
        return self._code

    def getName(self):
        """Return the name of the indicator."""
        return self._name

    def getIndicator(self, symbol: str, interval: str, limit: int):
        """
        Get the indicator for a specific symbol, interval, and time period.

        Parameters:
        symbol (str): The symbol for which to retrieve the indicator.
        interval (str): The interval of the data (e.g. '1d' for daily data).
        limit (int): The number of data points to retrieve.

        Returns:
        HistoryData: The historical data for the symbol, interval, and time period.
        """
        return config.getHandler().getHistoryData(symbol=symbol, interval=interval, limit=limit)

    def getIndicatorByHistoryData(self, historyData: HistoryData):
        """
        Get the indicator for a specific historical data object.

        Parameters:
        historyData (HistoryData): The historical data for which to calculate the indicator.

        Returns:
        DataFrame: A pandas DataFrame containing the indicator data.
        """
        return historyData.getDataFrame()


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
        self._code = 'CCI'
        self._name = 'Commodity Channel Index'

        # Set the length of the indicator (number of periods)
        self.__length = int(length)

    def getLength(self) -> int:
        """Return the length of the CCI indicator."""
        return self.__length

    def getIndicator(self, symbol: str, interval: str, limit: int):
        """
        Get the CCI indicator for a specific symbol, interval, and time period.

        Parameters:
        symbol (str): The symbol for which to retrieve the CCI indicator.
        interval (str): The interval of the data (e.g. '1d' for daily data).
        limit (int): The number of data points to retrieve.

        Returns:
        DataFrame: A pandas DataFrame containing the CCI indicator data.
        """
        # Calculate the default limit to ensure there is enough data to calculate the indicator
        default_length = self.__length + 2

        # If the given limit is less than the default limit, use the default limit instead
        limit = limit if limit > default_length else default_length

        # Get the historical data for the given symbol and interval up to the given limit
        historyData = super().getIndicator(symbol=symbol, interval=interval, limit=limit)

        # Calculate the indicator based on the historical data and return it
        return self.getIndicatorByHistoryData(historyData)

    def getIndicatorByHistoryData(self, historyData: HistoryData):
        """
        Get the CCI indicator for a specific historical data object.

        Parameters:
        historyData (HistoryData): The historical data for which to calculate the CCI indicator.

        Returns:
        DataFrame: A pandas DataFrame containing the CCI indicator data.
        """
        # Get the historical data as a pandas DataFrame
        historyDataFrame = super().getIndicatorByHistoryData(historyData)

        # Check if there is enough historical data to calculate the indicator
        if historyDataFrame.shape[0] < self.__length:
            # If there is not enough historical data, raise an exception
            raise Exception(f'Count of history data less then indicator interval {self.__length}')

        # Calculate the Commodity Channel Index using the length specified in the constructor
        cci_series = historyDataFrame.ta.cci(length=self.__length)

        # Convert the series to a DataFrame with the indicator code as the column name
        cci_df = cci_series.to_frame(name=self._code)

        # Join the indicator DataFrame with the historical data DataFrame
        indicator_df = historyDataFrame.join(cci_df)

        # Drop rows with missing values (NaNs) in the indicator column
        indicator_df = indicator_df.dropna(subset=[self._code])

        # Return the indicator DataFrame
        return indicator_df
