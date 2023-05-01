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
    SIGNAL = 'Signal'

    # Order Statuses
    ORDER_STATUS_OPEN = 'Open'
    ORDER_STATUS_CLOSE = 'Close'

    # Order Close Reason
    ORDER_CLOSE_REASON_STOP_LOSS = 'Stop Loss'
    ORDER_CLOSE_REASON_TAKE_PROFIT = 'Take Profit'
    ORDER_CLOSE_REASON_SIGNAL = 'Signal'

class ExhangeInfo:
    pass


class TradingTime:
    pass


class Symbol:
    def __init__(self, code: str, name: str, status: str, type: str, tradingTime: TradingTime):
        self.code = code
        self.name = name
        self.descr = f'{name} ({code})'
        self.status = status
        self.tradingTime = tradingTime
        self.type = type


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
        self.balance=balance
        self.limit=int(limit)
        self.stopLossRate=stopLossRate
        self.takeProfitRate=takeProfitRate
        self.feeRate=feeRate

