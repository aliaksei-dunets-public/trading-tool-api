import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import logging
from apscheduler.job import Job

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

logger = logging.getLogger("trading_core")
# logger.info(f"Log file created at {datetime.now()}")


class Symbol:
    def __init__(self, code: str, name: str, status: str, type: str, tradingTime: str):
        self.code = code
        self.name = name
        self.descr = f"{name} ({code})"
        self.status = status
        self.tradingTime = tradingTime
        self.type = type

    def get_symbol_json(self):
        return {
            Const.CODE: self.code,
            Const.NAME: self.name,
            Const.DESCR: self.descr,
            Const.STATUS: self.status,
            Const.TRADING_TIME: self.tradingTime,
            Const.PARAM_SYMBOL_TYPE: self.type,
        }


# class CandelBar:
#     def __init__(
#         self,
#         date_time: datetime,
#         open: float,
#         high: float,
#         low: float,
#         close: float,
#         volume: float,
#     ) -> None:
#         self.date_time = date_time
#         self.open = open
#         self.high = high
#         self.low = low
#         self.close = close
#         self.volume = volume


# class CandelBarSignal(CandelBar):
#     def __init__(
#         self,
#         date_time: datetime,
#         open: float,
#         high: float,
#         low: float,
#         close: float,
#         volume: float,
#         signal: str,
#     ) -> None:
#         CandelBar.__init__(
#             self,
#             date_time=date_time,
#             open=open,
#             high=high,
#             low=low,
#             close=close,
#             volume=volume,
#         )

#         self.signal = signal


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


# class SimulateOptions:
#     def __init__(self, init_balance, limit, stop_loss_rate, take_profit_rate, fee_rate):
#         self.init_balance: float = float(init_balance)
#         self.limit: int = int(limit)
#         self.stop_loss_rate: float = float(stop_loss_rate)
#         self.take_profit_rate: float = float(take_profit_rate)
#         self.fee_rate: float = float(fee_rate)

#     def get_fee_value(self) -> float:
#         return (self.init_balance * self.fee_rate) / 100

#     def get_stop_loss_value(self, price: float) -> float:
#         return (price * self.stop_loss_rate) / 100

#     def get_take_profit_value(self, price: float) -> float:
#         return (price * self.take_profit_rate) / 100

#     def get_balance(self) -> float:
#         return self.init_balance - self.get_fee_value()

#     def set_init_balance(self, init_balance: float) -> None:
#         self.init_balance = init_balance

#     def get_quantity(self, price: float) -> float:
#         if price == 0:
#             return 0
#         else:
#             return self.get_balance() / price


class Signal:
    def __init__(
        self,
        date_time: datetime,
        symbol: str,
        interval: str,
        strategy: str,
        signal: str,
    ):
        self.__date_time = date_time
        self.__symbol = symbol
        self.__interval = interval
        self.__strategy = strategy
        self.__signal = signal

    def get_signal_dict(self) -> dict:
        return {
            Const.DATETIME: self.__date_time.isoformat(),
            Const.PARAM_SYMBOL: self.__symbol,
            Const.INTERVAL: self.__interval,
            Const.STRATEGY: self.__strategy,
            Const.PARAM_SIGNAL: self.__signal,
        }

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
        if (
            Const.DEBUG_SIGNAL in signals_config
            or not signals_config
            and self.__signal
            or (signals_config and (self.__signal in signals_config))
        ):
            return True
        else:
            return False


class RuntimeBufferStore:
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
        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(f"BUFFER: getSymbols()")

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

    def getHistoryDataFromBuffer(
        self, symbol: str, interval: str, limit: int, endDatetime: datetime
    ) -> HistoryData:
        buffer_key = self.getHistoryDataBufferKey(symbol=symbol, interval=interval)
        history_data_buffer = self.__history_data_buffer[buffer_key]
        df_buffer = history_data_buffer.getDataFrame()

        df_required = df_buffer[df_buffer.index <= endDatetime]

        if limit > len(df_required):
            return None

        df_required = df_required.tail(limit)

        history_data_required = HistoryData(
            symbol=symbol, interval=interval, limit=limit, dataFrame=df_required
        )

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"BUFFER: getHistoryData(symbol={symbol}, interval={interval}, limit={limit}, endDatetime={endDatetime})"
            )

        return history_data_required

    def validateHistoryDataInBuffer(
        self, symbol: str, interval: str, limit: int, endDatetime: datetime
    ) -> bool:
        buffer_key = self.getHistoryDataBufferKey(symbol=symbol, interval=interval)
        if self.checkHistoryDataInBuffer(symbol, interval):
            history_data_buffer = self.__history_data_buffer[buffer_key]
            if (
                limit <= history_data_buffer.getLimit()
                and endDatetime <= history_data_buffer.getEndDateTime()
            ):
                return True
            else:
                return False
        else:
            return False

    def checkHistoryDataInBuffer(self, symbol: str, interval: str) -> bool:
        buffer_key = self.getHistoryDataBufferKey(symbol=symbol, interval=interval)
        if buffer_key in self.__history_data_buffer:
            return True
        else:
            return False

    def setHistoryDataToBuffer(self, history_data_inst: HistoryData):
        if history_data_inst:
            buffer_key = self.getHistoryDataBufferKey(
                symbol=history_data_inst.getSymbol(),
                interval=history_data_inst.getInterval(),
            )
            self.__history_data_buffer[buffer_key] = history_data_inst

    def getHistoryDataBufferKey(self, symbol: str, interval: str) -> tuple:
        if not symbol or not interval:
            Exception(
                f"History Data buffer key is invalid: symbol: {symbol}, interval: {interval}"
            )
        buffer_key = (symbol, interval)
        return buffer_key

    def clearHistoryDataBuffer(self):
        self.__history_data_buffer.clear()

    def get_signal_from_buffer(
        self, symbol: str, interval: str, strategy: str, date_time: datetime
    ) -> Signal:
        buffer_key = self.get_signal_buffer_key(
            symbol=symbol, interval=interval, strategy=strategy
        )

        if not self.check_signal_in_buffer(
            symbol=symbol, interval=interval, strategy=strategy
        ):
            return None

        signal_buffer_inst = self.__signal_buffer[buffer_key]

        if date_time == signal_buffer_inst.get_date_time():
            if config.get_config_value(Const.CONFIG_DEBUG_LOG):
                logger.info(
                    f"BUFFER: get_signal(symbol={symbol}, interval={interval}, strategy={strategy}, date_time={date_time})"
                )

            return signal_buffer_inst
        else:
            return None

    def check_signal_in_buffer(self, symbol: str, interval: str, strategy: str) -> bool:
        buffer_key = self.get_signal_buffer_key(
            symbol=symbol, interval=interval, strategy=strategy
        )
        if buffer_key in self.__signal_buffer:
            return True
        else:
            return False

    def set_signal_to_buffer(self, signal_inst: Signal):
        if signal_inst:
            buffer_key = self.get_signal_buffer_key(
                symbol=signal_inst.get_symbol(),
                interval=signal_inst.get_interval(),
                strategy=signal_inst.get_strategy(),
            )
            self.__signal_buffer[buffer_key] = signal_inst

    def get_signal_buffer_key(self, symbol: str, interval: str, strategy: str) -> tuple:
        if not symbol or not interval or not strategy:
            Exception(
                f"Signal buffer key is invalid: symbol: {symbol}, interval: {interval}, strategy: {strategy}"
            )
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
                f"CONFIG: {property} is not maintained in the environment values"
            )
        return env_value

    def get_stock_exchange_id(self) -> str:
        return Const.STOCK_EXCH_CURRENCY_COM
        # return Const.STOCK_EXCH_LOCAL_CURRENCY_COM

    def get_indicators_config(self) -> list:
        return [
            {Const.CODE: Const.TA_INDICATOR_CCI, Const.NAME: "Commodity Channel Index"}
        ]

    def get_strategies_config(self):
        strategies = {
            Const.TA_STRATEGY_CCI_14_TREND_100: {
                Const.CODE: Const.TA_STRATEGY_CCI_14_TREND_100,
                Const.NAME: "CCI(14) cross +/- 100",
                Const.LENGTH: 14,
                Const.VALUE: 100,
            },
            Const.TA_STRATEGY_CCI_14_BASED_TREND_100: {
                Const.CODE: Const.TA_STRATEGY_CCI_14_BASED_TREND_100,
                Const.NAME: "Check Trends and CCI(14) cross +/- 100",
                Const.LENGTH: 14,
                Const.VALUE: 100,
            },
            # Const.TA_STRATEGY_CCI_20_TREND_100: {
            #     Const.CODE: Const.TA_STRATEGY_CCI_20_TREND_100,
            #     Const.NAME: "CCI(20) cross +/- 100",
            #     Const.LENGTH: 20,
            #     Const.VALUE: 100,
            # },
            # Const.TA_STRATEGY_CCI_20_BASED_TREND_100: {
            #     Const.CODE: Const.TA_STRATEGY_CCI_20_BASED_TREND_100,
            #     Const.NAME: "Check Trends and CCI(20) cross +/- 100",
            #     Const.LENGTH: 20,
            #     Const.VALUE: 100,
            # },
            Const.TA_STRATEGY_CCI_20_100_TREND_UP_LEVEL: {
                Const.CODE: Const.TA_STRATEGY_CCI_20_100_TREND_UP_LEVEL,
                Const.NAME: "Check Trend Up Level and CCI(20) +/- 100",
                Const.LENGTH: 20,
                Const.VALUE: 100,
            },
            # Const.TA_STRATEGY_CCI_50_TREND_0: {
            #     Const.CODE: Const.TA_STRATEGY_CCI_50_TREND_0,
            #     Const.NAME: "CCI(50) cross 0",
            #     Const.LENGTH: 50,
            #     Const.VALUE: 0,
            # },
        }

        return strategies

    # def get_default_simulation_options(self, interval: str) -> list[SimulateOptions]:
    #     init_balance = 100
    #     # Strategy ofset
    #     limit = 300 + 50
    #     stop_loss_rate = 0
    #     take_profit_rate = 0
    #     fee_rate = 3
    #     rate_step_1 = 0
    #     rate_step_2 = 0

    #     if interval == IntervalType.MIN_1:
    #         rate_step_1 = 0.5
    #         rate_step_2 = 1.5
    #     if interval == IntervalType.MIN_15:
    #         rate_step_1 = 1
    #         rate_step_2 = 3
    #     if interval == IntervalType.MIN_30:
    #         rate_step_1 = 2
    #         rate_step_2 = 6
    #     if interval == IntervalType.HOUR_1:
    #         rate_step_1 = 3
    #         rate_step_2 = 9
    #     if interval == IntervalType.HOUR_4:
    #         rate_step_1 = 5
    #         rate_step_2 = 10
    #     if interval == IntervalType.DAY_1:
    #         rate_step_1 = 10
    #         rate_step_2 = 20
    #     if interval == IntervalType.WEEK_1:
    #         rate_step_1 = 10
    #         rate_step_2 = 20
    #         limit = 100 + 50

    #     return [
    #         SimulateOptions(
    #             init_balance=init_balance,
    #             limit=limit,
    #             stop_loss_rate=stop_loss_rate,
    #             take_profit_rate=take_profit_rate,
    #             fee_rate=fee_rate,
    #         ),
    #         SimulateOptions(
    #             init_balance=init_balance,
    #             limit=limit,
    #             stop_loss_rate=stop_loss_rate + rate_step_1,
    #             take_profit_rate=take_profit_rate + (rate_step_1 * 3),
    #             fee_rate=fee_rate,
    #         ),
    #         SimulateOptions(
    #             init_balance=init_balance,
    #             limit=limit,
    #             stop_loss_rate=stop_loss_rate + rate_step_2,
    #             take_profit_rate=take_profit_rate + (rate_step_2 * 3),
    #             fee_rate=fee_rate,
    #         ),
    #     ]


config = Config()
runtime_buffer = RuntimeBufferStore()
