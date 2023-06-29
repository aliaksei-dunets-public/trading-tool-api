import os
import pandas as pd
from datetime import datetime
import logging
from apscheduler.job import Job
# from logging.handlers import TimedRotatingFileHandler

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
    # Intervals
    TA_INTERVAL_5M = "5m"
    TA_INTERVAL_15M = "15m"
    TA_INTERVAL_30M = "30m"
    TA_INTERVAL_1H = "1h"
    TA_INTERVAL_4H = "4h"
    TA_INTERVAL_1D = "1d"
    TA_INTERVAL_1WK = "1w"

    # Indicators
    TA_INDICATOR_CCI = "CCI"

    # Strategies
    TA_STRATEGY_CCI_14_TREND_100 = "CCI_14_TREND_100"
    TA_STRATEGY_CCI_20_TREND_100 = "CCI_20_TREND_100"
    TA_STRATEGY_CCI_50_TREND_0 = "CCI_50_TREND_0"

    # Config properties
    CONFIG_DEBUG_LOG = 'DEBUG_LOG'

    # Signal Values
    STRONG_BUY = 'Strong Buy'
    BUY = 'Buy'
    STRONG_SELL = 'Strong Sell'
    SELL = 'Sell'
    DEBUG_SIGNAL = 'Debug'

    # Direction Values
    LONG = 'LONG'
    SHORT = 'SHORT'

    # Column Names
    COLUMN_DATETIME = 'Datetime'
    COLUMN_OPEN = 'Open'
    COLUMN_HIGH = 'High'
    COLUMN_LOW = 'Low'
    COLUMN_CLOSE = 'Close'
    COLUMN_VOLUME = 'Volume'

    # Parameters
    SIGNAL = 'signal'
    SYMBOL = 'symbol'
    CODE = 'code'
    INTERVAL = 'interval'
    LIMIT = 'limit'
    STRATEGY = 'strategy'
    DATETIME = 'date_time'
    NAME = 'name'
    DESCR = 'descr'
    STATUS = 'status'
    START_TIME = 'start_time'
    END_TIME = 'end_time'
    START_DATE = 'start_date'
    END_DATE = 'end_date'
    CLOSED_BARS = 'closed_bars'
    IMPORTANCE = 'importance'
    LENGTH = "length"
    VALUE = "value"
    JOB_ID = "job_id"

    # DB fields
    DB_ID = "_id"
    DB_JOB_TYPE = 'job_type'
    DB_INTERVAL = 'interval'
    DB_IS_ACTIVE = 'is_active'
    DB_CREATED_AT = "created_at"
    DB_CREATED_BY = "created_by"
    DB_CHANGED_AT = "changed_at"
    DB_CHANGED_BY = "changed_by"
    DB_CHANNEL_ID = 'channel_id'
    DB_SYMBOL = 'symbol'
    DB_STRATEGIES = 'strategies'
    DB_SIGNALS = 'signals'
    DB_COMMENT = 'comment'
    DB_ORDER_TYPE = 'order_type'

    # API fields
    END_TIME = 'endTime'

    # Order Statuses
    ORDER_STATUS_OPEN = 'Open'
    ORDER_STATUS_CLOSE = 'Close'

    # Order Close Reason
    ORDER_CLOSE_REASON_STOP_LOSS = 'Stop Loss'
    ORDER_CLOSE_REASON_TAKE_PROFIT = 'Take Profit'
    ORDER_CLOSE_REASON_SIGNAL = 'Signal'

    # Importance
    IMPORTANCE_LOW = 'LOW'
    IMPORTANCE_MEDIUM = 'MEDIUM'
    IMPORTANCE_HIGH = 'HIGH'

    # Job types
    JOB_TYPE_INIT = 'JOB_TYPE_INIT'
    JOB_TYPE_BOT = 'JOB_TYPE_BOT'
    JOB_TYPE_EMAIL = 'JOB_TYPE_EMAIL'

    # Collections name
    DB_COLLECTION_JOBS = 'jobs_temp'
    DB_COLLECTION_ALERTS = 'alerts_temp'
    DB_COLLECTION_ORDERS = 'orders_temp'

    # Stock Exchanges
    STOCK_EXCH_CURRENCY_COM = 'CURRENCY.COM'


class Config:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.__config_data = {Const.CONFIG_DEBUG_LOG: False}
        return class_._instance

    def get_config_value(self, property: str):
        if property and property in self.__config_data:
            return self.__config_data[property]
        else:
            None

    def get_stock_exchange_id(self) -> str:
        return Const.STOCK_EXCH_CURRENCY_COM

    def get_indicators_config(self) -> list:
        return [{Const.CODE: Const.TA_INDICATOR_CCI, Const.NAME: "Commodity Channel Index"}]

    def get_strategies_config(self):
        strategies = {Const.TA_STRATEGY_CCI_14_TREND_100: {Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
                                                           Const.NAME: "CCI(14): Indicator value +/- 100",
                                                           Const.LENGTH: 14,
                                                           Const.VALUE: 100},
                      Const.TA_STRATEGY_CCI_20_TREND_100: {Const.CODE: Const.TA_STRATEGY_CCI_20_TREND_100,
                                                           Const.NAME: "CCI(20): Indicator value +/- 100",
                                                           Const.LENGTH: 20,
                                                           Const.VALUE: 100},
                      Const.TA_STRATEGY_CCI_50_TREND_0: {Const.CODE: Const.TA_STRATEGY_CCI_50_TREND_0,
                                                         Const.NAME: "CCI(50): Indicator value 0",
                                                         Const.LENGTH: 50,
                                                         Const.VALUE: 0}}

        return strategies


class Symbol:
    def __init__(self, code: str, name: str, status: str, type: str, tradingTime: str):
        self.code = code
        self.name = name
        self.descr = f'{name} ({code})'
        self.status = status
        self.tradingTime = tradingTime
        self.type = type


class HistoryData:
    def __init__(self, symbol: str, interval: str, limit: int, dataFrame: pd.DataFrame):
        self.__symbol = symbol
        self.__interval = interval
        self.__limit = int(limit)
        self.__dataFrame = dataFrame
        self.__endDateTime = self.__dataFrame.index[-1]

    def getSymbol(self):
        return self.__symbol

    def getInterval(self):
        return self.__interval

    def getLimit(self) -> int:
        return self.__limit

    def getDataFrame(self):
        return self.__dataFrame

    def getEndDateTime(self):
        return self.__endDateTime


class SimulateOptions:
    def __init__(self, balance, limit, stopLossRate, takeProfitRate, feeRate):
        self.balance = balance
        self.limit = int(limit)
        self.stopLossRate = stopLossRate
        self.takeProfitRate = takeProfitRate
        self.feeRate = feeRate


class Signal():
    def __init__(self, date_time: datetime, symbol: str, interval: str, strategy: str, signal: str):
        self.__date_time = date_time
        self.__symbol = symbol
        self.__interval = interval
        self.__strategy = strategy
        self.__signal = signal

    def get_signal_dict(self) -> dict:
        return {Const.DATETIME: self.__date_time.isoformat(),
                Const.SYMBOL: self.__symbol,
                Const.INTERVAL: self.__interval,
                Const.STRATEGY: self.__strategy,
                Const.SIGNAL: self.__signal}

    def get_date_time(self) -> datetime:
        return self.__date_time

    def get_symbol(self) -> str:
        return self.__symbol

    def get_interval(self) -> str:
        return self.__interval

    def get_strategy(self) -> str:
        return self.__strategy

    def get_signal(self) -> str:
        return self.__signal

    def is_compatible(self, signals_config: list = []) -> bool:
        if Const.DEBUG_SIGNAL in signals_config \
                or not signals_config and self.__signal \
                or (signals_config and (self.__signal in signals_config)):
            return True
        else:
            return False


class RuntimeBufferStore():
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_.__symbol_buffer = {}
            class_.__timeframe_buffer = {}
            class_.__history_data_buffer = {}
            class_.__signal_buffer = {}
            class_.__job_buffer = {}
        return class_._instance

    def getSymbolsFromBuffer(self) -> dict[Symbol]:
        return self.__symbol_buffer

    def checkSymbolsInBuffer(self) -> bool:
        if self.__symbol_buffer:
            return True
        else:
            return False

    def setSymbolsToBuffer(self, symbols: dict[Symbol]):
        self.__symbol_buffer = symbols

    def clearSymbolsBuffer(self):
        self.__symbol_buffer.clear()

    def checkTimeframeInBuffer(self, trading_time: str):
        return trading_time in self.__timeframe_buffer

    def getTimeFrameFromBuffer(self, trading_time: str) -> dict:
        if self.checkTimeframeInBuffer(trading_time):
            return self.__timeframe_buffer[trading_time]
        else:
            None

    def setTimeFrameToBuffer(self, trading_time: str, timeframe: dict):
        self.__timeframe_buffer[trading_time] = timeframe

    def clearTimeframeBuffer(self):
        self.__timeframe_buffer.clear()

    def getHistoryDataFromBuffer(self, symbol: str, interval: str, limit: int, endDatetime: datetime) -> HistoryData:
        buffer_key = self.getHistoryDataBufferKey(
            symbol=symbol, interval=interval)
        history_data_buffer = self.__history_data_buffer[buffer_key]
        df_buffer = history_data_buffer.getDataFrame()

        df_required = df_buffer[df_buffer.index <= endDatetime]

        if limit > len(df_required):
            return None

        df_required = df_required.tail(limit)

        history_data_required = HistoryData(
            symbol=symbol, interval=interval, limit=limit, dataFrame=df_required)

        return history_data_required

    def validateHistoryDataInBuffer(self, symbol: str, interval: str, limit: int, endDatetime: datetime) -> bool:
        buffer_key = self.getHistoryDataBufferKey(
            symbol=symbol, interval=interval)
        if self.checkHistoryDataInBuffer(symbol, interval):
            history_data_buffer = self.__history_data_buffer[buffer_key]
            if limit <= history_data_buffer.getLimit() and endDatetime <= history_data_buffer.getEndDateTime():
                return True
            else:
                return False
        else:
            return False

    def checkHistoryDataInBuffer(self, symbol: str, interval: str) -> bool:
        buffer_key = self.getHistoryDataBufferKey(
            symbol=symbol, interval=interval)
        if buffer_key in self.__history_data_buffer:
            return True
        else:
            return False

    def setHistoryDataToBuffer(self, history_data_inst: HistoryData):
        if history_data_inst:
            buffer_key = self.getHistoryDataBufferKey(
                symbol=history_data_inst.getSymbol(), interval=history_data_inst.getInterval())
            self.__history_data_buffer[buffer_key] = history_data_inst

    def getHistoryDataBufferKey(self, symbol: str, interval: str) -> tuple:
        if not symbol or not interval:
            Exception(
                f'History Data buffer key is invalid: symbol: {symbol}, interval: {interval}')
        buffer_key = (symbol, interval)
        return buffer_key

    def clearHistoryDataBuffer(self):
        self.__history_data_buffer.clear()

    def get_signal_from_buffer(self, symbol: str, interval: str, strategy: str, date_time: datetime) -> Signal:
        buffer_key = self.get_signal_buffer_key(
            symbol=symbol, interval=interval, strategy=strategy)

        if not self.check_signal_in_buffer(symbol=symbol, interval=interval, strategy=strategy):
            return None

        signal_buffer_inst = self.__signal_buffer[buffer_key]

        if date_time == signal_buffer_inst.get_date_time():
            return signal_buffer_inst
        else:
            return None

    def check_signal_in_buffer(self, symbol: str, interval: str, strategy: str) -> bool:
        buffer_key = self.get_signal_buffer_key(
            symbol=symbol, interval=interval, strategy=strategy)
        if buffer_key in self.__signal_buffer:
            return True
        else:
            return False

    def set_signal_to_buffer(self, signal_inst: Signal):
        if signal_inst:
            buffer_key = self.get_signal_buffer_key(
                symbol=signal_inst.get_symbol(), interval=signal_inst.get_interval(), strategy=signal_inst.get_strategy())
            self.__signal_buffer[buffer_key] = signal_inst

    def get_signal_buffer_key(self, symbol: str, interval: str, strategy: str) -> tuple:
        if not symbol or not interval or not strategy:
            Exception(
                f'Signal buffer key is invalid: symbol: {symbol}, interval: {interval}, strategy: {strategy}')
        buffer_key = (symbol, interval, strategy)
        return buffer_key

    def clear_signal_buffer(self):
        self.__signal_buffer.clear()

    def get_job_from_buffer(self, job_id: str) -> Job:
        if job_id in self.__job_buffer:
            return self.__job_buffer[job_id]
        else:
            None

    def set_job_to_buffer(self, job: Job) -> None:
        self.__job_buffer[job.id] = job

    def remove_job_from_buffer(self, job_id: str) -> None:
        self.__job_buffer.pop(job_id)


config = Config()
runtime_buffer = RuntimeBufferStore()
