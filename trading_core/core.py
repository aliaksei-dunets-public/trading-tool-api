import datetime


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


class TradingTimeframe:
    def __init__(self, tradingTime: str):
        self.__tradingTime = tradingTime
        self.__timeFrames = {}
        self.__decodeTimeframe()

    def __decodeTimeframe(self):

        # Split the Trading Time string into individual entries
        time_entries = self.__tradingTime.split('; ')

        # Loop through each time entry and check if the current time aligns
        for entry in time_entries[1:]:
            timeFrames = []

            # Split the time entry into day and time ranges
            day, time_ranges = entry.split(' ', 1)

            # Split the time ranges into time period
            time_periods = time_ranges.split(',')

            for time_period in time_periods:
                # Split the time period into start and end times
                start_time, end_time = time_period.split('-')
                start_time = '00:00' if start_time == '' else start_time
                start_time = datetime.datetime.strptime(
                    start_time.strip(), '%H:%M')

                end_time = '23:59' if end_time in ['', '00:00'] else end_time
                end_time = datetime.datetime.strptime(
                    end_time.strip(), '%H:%M')

                timeFrames.append({'start_time': start_time, 'end_time': end_time})

            self.__timeFrames[day.lower()] = timeFrames

    def isTradingOpen(self) -> bool:
        # Convert the current time to UTC
        current_time_utc = datetime.datetime.utcnow()
        current_day = current_time_utc.strftime('%a').lower()

        # Check if today matches the day in the timeframes
        if current_day in self.__timeFrames:
            timeframes = self.__timeFrames[current_day]
            for timeframe in timeframes:
                if timeframe['start_time'].time() <= current_time_utc.time() and current_time_utc.time() <= timeframe['end_time'].time():
                    return True

        return False


class Symbol:
    def __init__(self, code: str, name: str, status: str, type: str, tradingTime: str):
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
        self.balance = balance
        self.limit = int(limit)
        self.stopLossRate = stopLossRate
        self.takeProfitRate = takeProfitRate
        self.feeRate = feeRate
