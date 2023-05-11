import os
from datetime import datetime
import logging
from logging.handlers import TimedRotatingFileHandler

# Set up logging
log_file_prefix = f"{os.getcwd()}/static/logs/"
log_file_suffix = ".log"
date_format = "%Y-%m-%d"
current_date = datetime.utcnow().strftime(date_format)
log_file_name = log_file_prefix + current_date + log_file_suffix

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        # TimedRotatingFileHandler(log_file_name, when='midnight', backupCount=7),
                        logging.StreamHandler()
                    ])

logger = logging.getLogger("trading_core")
# logger.info(f"Log file created at {datetime.now()}")

class Const:
    # Signal Values
    STRONG_BUY = 'Strong Buy'
    BUY = 'Buy'
    STRONG_SELL = 'Strong Sell'
    SELL = 'Sell'

    # Direction Values
    LONG = 'LONG'
    SHORT = 'SHORT'

    # Column Names
    SIGNAL = 'signal'
    SYMBOL = 'symbol'
    CODE = 'code'
    INTERVAL = 'interval'
    STRATEGY = 'strategy'
    NAME = 'name'
    DESCR = 'descr'
    STATUS = 'status'
    START_TIME = 'start_time'
    END_TIME = 'end_time'
    START_DATE = 'start_date'
    END_DATE = 'end_date'

    # Order Statuses
    ORDER_STATUS_OPEN = 'Open'
    ORDER_STATUS_CLOSE = 'Close'

    # Order Close Reason
    ORDER_CLOSE_REASON_STOP_LOSS = 'Stop Loss'
    ORDER_CLOSE_REASON_TAKE_PROFIT = 'Take Profit'
    ORDER_CLOSE_REASON_SIGNAL = 'Signal'

    #Importance
    IMPORTANCE_LOW = 'LOW'
    IMPORTANCE_MEDIUM = 'MEDIUM'
    IMPORTANCE_HIGH = 'HIGH'


class TradingTimeframe:
    def __init__(self, tradingTime: str):
        self.__tradingTime = tradingTime
        self.__time_frames = {}
        self.__decodeTimeframe()

    def isTradingOpen(self) -> bool:
        # Get current time in UTC
        current_datetime_utc = datetime.utcnow()
        # Get name of a day in lower case
        current_day = current_datetime_utc.strftime('%a').lower()
        current_time = current_datetime_utc.time()

        # Check if today matches the day in the timeframes
        if current_day in self.__time_frames:
            time_frames = self.__time_frames[current_day]
            for time_frame in time_frames:
                if time_frame[Const.START_TIME].time() <= current_time and current_time <= time_frame[Const.END_TIME].time():
                    return True

        return False

    def __decodeTimeframe(self):

        # Split the Trading Time string into individual entries
        time_entries = self.__tradingTime.split('; ')

        # Loop through each time entry and check if the current time aligns
        for entry in time_entries[1:]:
            time_frames = []

            # Split the time entry into day and time ranges
            day, time_ranges = entry.split(' ', 1)

            # Split the time ranges into time period
            time_periods = time_ranges.split(',')

            for time_period in time_periods:
                # Split the time period into start and end times
                start_time, end_time = time_period.split('-')
                start_time = '00:00' if start_time == '' else start_time
                start_time = datetime.strptime(start_time.strip(), '%H:%M')

                end_time = end_time.strip()
                end_time = '23:59' if end_time in ['', '00:00'] else end_time
                end_time = datetime.strptime(end_time, '%H:%M')

                time_frames.append({Const.START_TIME: start_time,
                                    Const.END_TIME: end_time})

            self.__time_frames[day.lower()] = time_frames


class Symbol:
    def __init__(self, code: str, name: str, status: str, type: str, tradingTime: str):
        self.code = code
        self.name = name
        self.descr = f'{name} ({code})'
        self.status = status
        self.tradingTime = tradingTime
        self.type = type

    def isTradingOpen(self) -> bool:
        return TradingTimeframe(self.tradingTime).isTradingOpen()


class HistoryData:
    def __init__(self, symbol: str, interval: str, limit: int, dataFrame):
        self.__symbol = symbol
        self.__interval = interval
        self.__limit = limit
        self.__dataFrame = dataFrame

    def getSymbol(self):
        return self.__symbol

    def getInterval(self):
        return self.__interval

    def getLimit(self):
        return self.__limit

    def getDataFrame(self):
        return self.__dataFrame


class SimulateOptions:
    def __init__(self, balance, limit, stopLossRate, takeProfitRate, feeRate):
        self.balance = balance
        self.limit = int(limit)
        self.stopLossRate = stopLossRate
        self.takeProfitRate = takeProfitRate
        self.feeRate = feeRate
