import logging
import os
import json

from .core import Const, HistoryData, SimulateOptions
from .model import config, RuntimeBuffer
from .strategy import StrategyFactory

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class Simulator():

    def determineSignal(self, symbol: str, interval: str, strategyCode: str, signals: list, closedBar: bool):

        key = (symbol, interval, strategyCode)

        buffer = RuntimeBuffer()

        # Check buffer first. If key doesn't exist in the buffer -> run signal determination
        if key not in buffer.buffer_signals:
            strategy_df = StrategyFactory(strategyCode).get_strategy_data(
                symbol, interval, closedBar=closedBar).tail(1)

            for index, strategy_row in strategy_df.iterrows():
                buffer.buffer_signals[key] = {'dateTime': index.isoformat(),
                                              'symbol': symbol,
                                              'interval': interval,
                                              'strategy': strategyCode,
                                              'signal': strategy_row[Const.SIGNAL]}

        signal_result = buffer.buffer_signals[key]
        signal_value = signal_result[Const.SIGNAL]

        if self.isCompatibleSignal(signal_value, signals):
            return signal_result
        else:
            return None

    def isCompatibleSignal(self, signalValue, signalList):
        if (not signalList and signalValue) or (signalList and (signalValue in signalList or Const.DEBUG_SIGNAL in signalList)):
            return True
        else:
            return False

    def determineSignals(self, symbols: list = None, intervals: list = None, strategyCodes: list = None, signals: list = None, closedBar: bool = False):

        strategySignals = []

        if not intervals:
            intervals = config.get_intervals()

        if not strategyCodes:
            strategyCodes = config.get_strategy_codes()

        for symbol in symbols:
            for interval in intervals:
                for code in strategyCodes:
                    try:
                        signal = self.determineSignal(
                            symbol, interval, code, signals, closedBar)
                        if signal:
                            strategySignals.append(signal)
                        else:
                            continue
                    except Exception as error:
                        logging.error(
                            f'For symbol={symbol}, interval={interval}, code={code} - {error}')
                        continue

        return strategySignals

    def simulateTrading(self, symbols=[], intervals=[], strategyCodes=[], optionsList=[]):

        simulations = []

        if not intervals:
            intervals = config.get_intervals()

        if not strategyCodes:
            strategyCodes = config.get_strategy_codes()

        if not optionsList:
            optionsList = [SimulateOptions(
                balance=100, limit=500, stopLossRate=0, takeProfitRate=0, feeRate=0.5)]

        for symbol in symbols:
            for interval in intervals:
                limit = 0
                for options in optionsList:
                    if limit == 0 or limit < options.limit:
                        limit = options.limit
                        historyData = config.getHandler().getHistoryData(
                            symbol=symbol, interval=interval, limit=options.limit)
                    for code in strategyCodes:
                        try:
                            simulation = self.__simulateStragy(
                                historyData=historyData, strategyCode=code, options=options)

                            simulations.append(simulation)
                        except Exception as error:
                            logging.error(
                                f'For symbol={symbol}, interval={interval}, limit={limit} - {error}')
                            continue

        return simulations

    def getSimulations(self, symbols=[], intervals=[], strategyCodes=[]):

        filteredSimulations = []

        file_path = f'{os.getcwd()}/static/positiveSimulations.json'

        with open(file_path, 'r') as reader:
            simulations = json.load(reader)

        for simulation in simulations:
            if symbols and simulation['symbol'] not in symbols:
                continue

            if intervals and simulation['interval'] not in intervals:
                continue

            if strategyCodes and simulation['strategy'] not in strategyCodes:
                continue

            filteredSimulations.append(simulation)

        return filteredSimulations

    def getSignalsBySimulation(self, symbols=[], intervals=[], strategyCodes=[]):

        simulationsWithSignal = []

        simulations = self.getSimulations(symbols, intervals, strategyCodes)

        # Detect unique entries for symbol, interval, strategy from simulations
        uniqueSignalParams = set(
            (d['symbol'], d['interval'], d['strategy']) for d in simulations)

        for symbol, interval, strategy in uniqueSignalParams:
            try:
                signal = self.determineSignal(
                    symbol, interval, strategy, None, closedBar=True)

                for simulation in simulations:
                    if signal and simulation['symbol'] == symbol and simulation['interval'] == interval and simulation['strategy'] == strategy:

                        simulation['dateTime'] = signal['dateTime']
                        simulation['signal'] = signal['signal']

                        simulationsWithSignal.append(simulation)
                    else:
                        continue
            except Exception as error:
                logging.error(
                    f'For symbol={symbol}, interval={interval}, code={strategy} - {error}')
                continue

        return simulationsWithSignal

    def __simulateStragy(self, historyData: HistoryData, strategyCode, options: SimulateOptions):

        orderHandler = OrderHandler(
            options.balance, options.stopLossRate, options.takeProfitRate, options.feeRate)

        for interval in StrategyFactory(strategyCode).get_strategy_by_history_data(historyData).itertuples():
            orderHandler.processInterval(interval)

        return {"symbol": historyData.getSymbol(),
                "interval": historyData.getInterval(),
                "strategy": strategyCode,
                "limit": historyData.getLimit(),
                "profit": orderHandler.getBalance() - options.balance,
                "initBalance": options.balance,
                "stopLossRate": options.stopLossRate,
                "takeProfitRate": options.takeProfitRate,
                "feeRate": options.feeRate
                # "orders": orderHandler.getOrders4Json()
                }


class OrderHandler:
    def __init__(self, balance, stopLossRate, takeProfitRate, feeRate):
        self.__balance = balance
        self.__stopLossRate = stopLossRate
        self.__takeProfitRate = takeProfitRate
        self.__feeRate = feeRate
        self.__index = None
        self.__orders = []

    def processInterval(self, interval):

        # Firstly check if there is an open order -> close it if it requires
        if self.__hasOpenOrder() == True:
            self.__closeOrder(interval)

        # Secondly check if there is not an open order -> open a new one
        if self.__hasOpenOrder() == False:
            self.__createOrder(interval)

    def getBalance(self):
        return self.__balance

    def getRates(self):
        return {"stopLoss": self.__stopLossRate, "takeProfit": self.__takeProfitRate, "fee": self.__feeRate}

    def getOrders(self):
        return self.__orders

    def getOrders4Json(self):
        orders = []
        for order in self.__orders:
            orders.append(order.__dict__)

        return orders

    def __hasOpenOrder(self):
        if len(self.__orders) == 0:
            return False
        elif self.__orders[self.__index].status == Const.ORDER_STATUS_OPEN:
            return True
        else:
            return False

    def __createOrder(self, interval):
        direction = ''

        if interval.signal == Const.STRONG_BUY:
            direction = Const.LONG
        elif interval.signal == Const.STRONG_SELL:
            direction = Const.SHORT
        else:
            return

        self.__index = 0 if self.__index == None else (self.__index + 1)

        self.__orders.append(Order(direction=direction, openDateTime=interval.Index,
                                   openPrice=interval.Close, balance=self.__balance, stopLossRate=self.__stopLossRate,
                                   takeProfitRate=self.__takeProfitRate, feeRate=self.__feeRate))

        self.__recalculateOrder(interval)

    def __closeOrder(self, interval):

        order = self.__orders[self.__index]
        closeDateTime = interval.Index
        closePrice = 0
        closeReason = None

        if order.direction == Const.LONG:
            if order.stopLossPrice != 0 and interval.Low <= order.stopLossPrice:
                closePrice = order.stopLossPrice
                closeReason = Const.ORDER_CLOSE_REASON_STOP_LOSS
            elif interval.signal == Const.STRONG_SELL or interval.signal == Const.SELL:
                closePrice = interval.Close
                closeReason = Const.ORDER_CLOSE_REASON_SIGNAL
            elif order.takeProfitPrice != 0 and interval.High >= order.takeProfitPrice:
                closePrice = order.takeProfitPrice
                closeReason = Const.ORDER_CLOSE_REASON_TAKE_PROFIT
        elif order.direction == Const.SHORT:
            if order.takeProfitPrice != 0 and interval.Low <= order.takeProfitPrice:
                closePrice = order.takeProfitPrice
                closeReason = Const.ORDER_CLOSE_REASON_TAKE_PROFIT
            elif interval.signal == Const.STRONG_BUY or interval.signal == Const.BUY:
                closePrice = interval.Close
                closeReason = Const.ORDER_CLOSE_REASON_SIGNAL
            elif order.stopLossPrice != 0 and interval.High >= order.stopLossPrice:
                closePrice = order.stopLossPrice
                closeReason = Const.ORDER_CLOSE_REASON_STOP_LOSS

        if closeReason:
            self.__orders[self.__index].closeOrder(
                closeDateTime, closePrice, closeReason)

        self.__recalculateOrder(interval)

    def __recalculateOrder(self, interval):
        self.__orders[self.__index].setExtremum(interval.Low, interval.High)
        self.__balance += self.__orders[self.__index].profit


class Order:
    def __init__(self, direction, openDateTime, openPrice, balance, stopLossRate, takeProfitRate, feeRate):
        self.direction = direction
        self.status = Const.ORDER_STATUS_OPEN
        self.profit = 0
        self.percent = 0
        self.openDateTime = openDateTime.isoformat()
        self.openPrice = openPrice
        self.closeDateTime = ''
        self.closePrice = 0
        self.closeReason = ''

        self.fee = (balance * feeRate) / 100
        self.amount = balance / self.openPrice

        self.maxCanLoss = 0
        self.maxCanProfit = 0

        self.maxPrice = self.openPrice
        self.minPrice = self.openPrice
        self.maxPercent = 0
        self.minPercent = 0

        if self.direction == Const.LONG:
            stopLossValue = -self.openPrice * stopLossRate / 100
            takeProfitValue = self.openPrice * takeProfitRate / 100
        elif self.direction == Const.SHORT:
            stopLossValue = self.openPrice * stopLossRate / 100
            takeProfitValue = -self.openPrice * takeProfitRate / 100
        else:
            raise Exception('Direction of an order is incorrect or missed')

        self.stopLossPrice = self.openPrice + stopLossValue if stopLossRate > 0 else 0
        self.takeProfitPrice = self.openPrice + \
            takeProfitValue if takeProfitRate > 0 else 0

    def closeOrder(self, closeDateTime, closePrice, closeReason):
        self.status = Const.ORDER_STATUS_CLOSE
        self.closeDateTime = closeDateTime.isoformat()
        self.closePrice = closePrice
        self.closeReason = closeReason
        self.percent = self.__getPercent(self.openPrice, self.closePrice)
        self.maxPercent = self.__getPercent(self.openPrice, self.maxPrice)
        self.minPercent = self.__getPercent(self.openPrice, self.minPrice)

        if self.direction == Const.LONG:

            self.profit = self.__getCloseValue() - (self.__getOpenValue() + self.fee)
            self.maxCanLoss = self.__getMinValue() - (self.__getOpenValue() + self.fee)
            self.maxCanProfit = self.__getMaxValue() - (self.__getOpenValue() + self.fee)

        elif self.direction == Const.SHORT:

            self.profit = self.__getOpenValue() - (self.__getCloseValue() + self.fee)
            self.maxCanLoss = self.__getOpenValue() - (self.__getMaxValue() + self.fee)
            self.maxCanProfit = self.__getOpenValue() - (self.__getMinValue() + self.fee)

    def setExtremum(self, Low, High):
        self.minPrice = self.minPrice if self.minPrice <= Low else Low
        self.maxPrice = self.maxPrice if self.maxPrice >= High else High

    def __getOpenValue(self):
        return self.amount * self.openPrice

    def __getCloseValue(self):
        return self.amount * self.closePrice

    def __getMinValue(self):
        return self.amount * self.minPrice

    def __getMaxValue(self):
        return self.amount * self.maxPrice

    def __getPercent(self, initial, target):
        return (target-initial) / initial * 100
