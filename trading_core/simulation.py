from datetime import datetime

from .constants import Const
from .core import CandelBarSignal, SimulateOptions
from .model import ParamSimulation
from .strategy import StrategyFactory


class Order:
    def __init__(self, type: str, open_date_time: datetime, open_price: float, quantity: float):
        self.id = None
        self.type = type
        self.open_date_time = open_date_time
        self.open_price = open_price
        self.quantity = quantity
        self.status = Const.STATUS_OPEN
        self.close_date_time: datetime = None
        self.close_price: float = 0

    def close(self, close_date_time: datetime, close_price: float):
        self.status = Const.STATUS_CLOSE
        self.close_date_time = close_date_time
        self.close_price = close_price


class Simulator:
    def __init__(self, param: ParamSimulation):
        self.symbol = param.symbol
        self.interval = param.interval
        self.strategy = param.strategy
        self.simulation_options = param.simulation_options

        # Initial balance
        self.init_balance = self.simulation_options.init_balance
        # Total profit of the opened and closed orders
        self.total_profit: float = 0

        # List of simulations
        self.simulations: list[SimulationBase] = []
        # Current open simulation
        self.current_simulation: SimulationBase = None

    def execute(self) -> dict:
        # Get strategy DataFrame for symbol, interval, strategy and limit
        strategy_df = StrategyFactory(self.strategy).get_strategy_data(symbol=self.symbol,
                                                                       interval=self.interval,
                                                                       limit=self.simulation_options.limit,
                                                                       from_buffer=True,
                                                                       closed_bars=False)

        # Process each candle bar for detecting of the signals
        for row in strategy_df.itertuples():
            candle_bar = CandelBarSignal(date_time=row.Index,
                                         open=row.Open,
                                         high=row.High,
                                         low=row.Low,
                                         close=row.Close,
                                         volume=row.Volume,
                                         signal=row.signal)

            # Process candle bar -> create/close order and calculate profits and loses
            self._process_candle_bar(candle_bar)

        orders = []

        for simulation in self.simulations:
            orders.append(simulation.get_simulation())

        return {"summary":
                {Const.DB_SYMBOL: self.symbol,
                 Const.DB_INTERVAL: self.interval,
                 Const.DB_STRATEGY: self.strategy,
                 Const.DB_INIT_BALANCE: self.init_balance,
                 Const.DB_LIMIT: self.simulation_options.limit,
                 Const.DB_STOP_LOSS_RATE: self.simulation_options.stop_loss_rate,
                 Const.DB_TAKE_PROFIT_RATE: self.simulation_options.take_profit_rate,
                 Const.DB_FEE_RATE: self.simulation_options.fee_rate,
                 Const.DB_BALANCE: (self.init_balance + self.total_profit),
                 Const.DB_PROFIT: self.total_profit},
                "orders": orders,
                "analysis": self.__analyze()}

    def __analyze(self) -> dict:
        analysis = {
            Const.LONG: {
                "count": {
                    "profit": 0,
                    "loss": 0,
                    "all": 0
                },
                "sum": {
                    "profit": 0,
                    "loss": 0,
                    "all": 0
                },
                # "avg": {
                #     "profit_percent": 0,
                #     "loss_percent": 0
                # },
                "close_reason": {
                    Const.ORDER_CLOSE_REASON_STOP_LOSS: 0,
                    Const.ORDER_CLOSE_REASON_TAKE_PROFIT: 0,
                    Const.ORDER_CLOSE_REASON_SIGNAL: 0,
                }
            },
            Const.SHORT: {
                "count": {
                    "profit": 0,
                    "loss": 0,
                    "all": 0
                },
                "sum": {
                    "profit": 0,
                    "loss": 0,
                    "all": 0
                },
                # "avg": {
                #     "profit_percent": 0,
                #     "loss_percent": 0
                # },
                "close_reason": {
                    Const.ORDER_CLOSE_REASON_STOP_LOSS: 0,
                    Const.ORDER_CLOSE_REASON_TAKE_PROFIT: 0,
                    Const.ORDER_CLOSE_REASON_SIGNAL: 0,
                }
            },
            "sum_fee_value": 0,
            "sum_max_loss_value": 0,
            "sum_max_profit_value": 0
        }

        for simulation in self.simulations:

            order_type = simulation.get_order().type

            if simulation.profit > 0:
                analysis[order_type]["count"]["profit"] += 1
                analysis[order_type]["sum"]["profit"] += simulation.profit
            else:
                analysis[order_type]["count"]["loss"] += 1
                analysis[order_type]["sum"]["loss"] += simulation.profit

            analysis[order_type]["count"]["all"] += 1
            analysis[order_type]["sum"]["all"] += simulation.profit

            analysis[order_type]["close_reason"][simulation.close_reason] += 1

            analysis["sum_fee_value"] += simulation.fee_value
            analysis["sum_max_loss_value"] += simulation.max_loss_value
            analysis["sum_max_profit_value"] += simulation.max_profit_value

        return analysis

    def _process_candle_bar(self, candler_bar: CandelBarSignal) -> None:
        # The first step - Check if an open order exists
        if self._exist_open_order():
            # Check signals for closing of the open order
            self._close_simulation(candler_bar)

        # The second step - Check if an open order doesn't exist
        if not self._exist_open_order():
            # Check signals for opening of a new order
            self._create_simulation(candler_bar)

    def _create_simulation(self, candler_bar: CandelBarSignal) -> None:
        # When signal = Strong Buy -> Buy stocks (Open LONG order)
        if candler_bar.signal == Const.STRONG_BUY:
            self.current_simulation = SimulationLong(self.simulation_options)
        # When signal = Strong Sell -> Sell stocks (Open SHORT order)
        elif candler_bar.signal == Const.STRONG_SELL:
            self.current_simulation = SimulationShort(self.simulation_options)
        else:
            return None

        # Create order and calculate some attributes
        self.current_simulation.open_simulation(open_date_time=candler_bar.date_time,
                                                open_price=candler_bar.close)

        # Clear current open simulation if order is not open
        if not self._exist_open_order():
            self.current_simulation = None

    def _close_simulation(self, candler_bar: CandelBarSignal) -> None:
        # Close an open order and recalculate some attributes
        if self.current_simulation.close_simulation(candler_bar):
            # Recalculate Total Profit
            self.total_profit += self.current_simulation.profit

            # Recalculate init balance in the simulation options
            self.simulation_options.set_init_balance(
                self.init_balance + self.total_profit)

            # Add curretn closed simulation to the list of the simulations
            self.simulations.append(self.current_simulation)

    def _exist_open_order(self) -> bool:
        # check if current open simulation exists, an order exists and the order is open
        if self.current_simulation:
            order_inst = self.current_simulation.get_order()
            if order_inst and order_inst.status == Const.STATUS_OPEN:
                return True
        return False


class SimulationBase:
    def __init__(self, options_inst: SimulateOptions):

        self._order: Order = None
        self._options_inst: SimulateOptions = options_inst

        self.close_reason = ''
        self.fee_value = self._options_inst.get_fee_value()
        self.balance: float = self._options_inst.get_balance()
        self.profit: float = 0
        self.percent_change: float = 0
        self.stop_loss_value: float = 0
        self.stop_loss_price: float = 0
        self.take_profit_value: float = 0
        self.take_profit_price: float = 0
        self.max_loss_value: float = 0
        self.max_profit_value: float = 0
        self.max_price: float = 0
        self.min_price: float = 0
        self.max_percent_change: float = 0
        self.min_percent_change: float = 0

    def open_simulation(self, type: str, open_date_time: datetime, open_price: float) -> None:
        # Get quantity of an order based on an init balance and an open price
        quantity = self._options_inst.get_quantity(open_price)
        # Get Stop loss value based on Stop loss rate and the open price
        self.stop_loss_value = self._options_inst.get_stop_loss_value(
            open_price)
        # Get Take profit value based on Take profit rate and the open price
        self.take_profit_value = self._options_inst.get_take_profit_value(
            open_price)
        self.max_price = open_price
        self.min_price = open_price

        # Create an order with the open status
        self._order = Order(type=type,
                            open_date_time=open_date_time,
                            open_price=open_price,
                            quantity=quantity)

    def close_simulation(self, candler_bar: CandelBarSignal) -> bool:
        self.__recalculate(low=candler_bar.low, high=candler_bar.high)
        return True

    def get_order(self) -> Order:
        return self._order

    def get_simulation(self) -> dict:

        order_dict = dict(self._order.__dict__)
        # simulation_options = vars(self._options_inst)
        simulation = dict(self.__dict__)
        simulation.pop('_order')
        simulation.pop('_options_inst')

        simulation.update(order_dict)
        # simulation.update(simulation_options)

        return simulation

    def _close_order(self, close_date_time: datetime, close_price: float, close_reason: str) -> bool:
        # Set a reason of an order closing
        self.close_reason = close_reason
        # Set changes in percents of the candle bar
        self.percent_change = self._get_percent_change(initial=self._order.open_price,
                                                       target=close_price)
        # Set max changes in percents of the candle bar
        self.max_percent_change = self._get_percent_change(initial=self._order.open_price,
                                                           target=self.max_price)
        # Set min changes in percents of the candle bar
        self.min_percent_change = self._get_percent_change(initial=self._order.open_price,
                                                           target=self.min_price)

        # Close the order
        if self._order and self._order.status == Const.STATUS_OPEN:
            self._order.close(close_date_time=close_date_time,
                              close_price=close_price)
            return True
        else:
            return False

    def __recalculate(self, low: float, high: float) -> None:
        # Set min price of the candle bar
        self.min_price = self.min_price if self.min_price <= low else low
        # Set max price of the candle bar
        self.max_price = self.max_price if self.max_price >= high else high

    def _get_percent_change(self, initial, target):
        return (target-initial) / initial * 100

    def _get_price_value(self, price):
        return self._order.quantity * price


class SimulationLong(SimulationBase):
    def __init__(self, options_inst: SimulateOptions):
        super().__init__(options_inst)

    def open_simulation(self, open_date_time: datetime, open_price: float):
        super().open_simulation(type=Const.LONG,
                                open_date_time=open_date_time,
                                open_price=open_price)

        # Calculate Stop Loss Price based on the open price and Stop Loss value: Open price - Stop Loss value
        self.stop_loss_price = open_price - \
            self.stop_loss_value if self.stop_loss_value > 0 else 0
        # Calculate Take Profit Price based on the open price and Take Profit value: Open price + Take Profit value
        self.take_profit_price = open_price + \
            self.take_profit_value if self.take_profit_value > 0 else 0

    def close_simulation(self, candler_bar: CandelBarSignal) -> bool:

        super().close_simulation(candler_bar)

        if self.stop_loss_price != 0 and candler_bar.low <= self.stop_loss_price:
            close_price = self.stop_loss_price
            close_reason = Const.ORDER_CLOSE_REASON_STOP_LOSS
        elif self.take_profit_price != 0 and candler_bar.high >= self.take_profit_price:
            close_price = self.take_profit_price
            close_reason = Const.ORDER_CLOSE_REASON_TAKE_PROFIT
        elif candler_bar.signal in [Const.STRONG_SELL, Const.SELL]:
            close_price = candler_bar.close
            close_reason = Const.ORDER_CLOSE_REASON_SIGNAL
        else:
            return False

        return self._close_order(close_date_time=candler_bar.date_time,
                                 close_price=close_price,
                                 close_reason=close_reason)

    # def get_order(self) -> Order:
    #     return super().get_order()

    def _close_order(self, close_date_time: datetime, close_price: float, close_reason: str) -> bool:

        self.profit = self._get_price_value(close_price) - self.balance
        self.max_loss_value = self._get_price_value(
            self.min_price) - self.balance
        self.max_profit_value = self._get_price_value(
            self.max_price) - self.balance

        return super()._close_order(close_date_time=close_date_time,
                                    close_price=close_price,
                                    close_reason=close_reason)


class SimulationShort(SimulationBase):
    def __init__(self, options_inst: SimulateOptions):
        super().__init__(options_inst)

    def open_simulation(self, open_date_time: datetime, open_price: float):
        super().open_simulation(type=Const.SHORT,
                                open_date_time=open_date_time,
                                open_price=open_price)

        # Calculate Stop Loss Price based on the open price and Stop Loss value: Open price + Stop Loss value
        self.stop_loss_price = open_price + \
            self.stop_loss_value if self.stop_loss_value > 0 else 0
        # Calculate Take Profit Price based on the open price and Take Profit value: Open price - Take Profit value
        self.take_profit_price = open_price - \
            self.take_profit_value if self.take_profit_value > 0 else 0

    def close_simulation(self, candler_bar: CandelBarSignal) -> bool:

        super().close_simulation(candler_bar)

        if self.stop_loss_price != 0 and candler_bar.high >= self.stop_loss_price:
            close_price = self.stop_loss_price
            close_reason = Const.ORDER_CLOSE_REASON_STOP_LOSS
        elif self.take_profit_price != 0 and candler_bar.low <= self.take_profit_price:
            close_price = self.take_profit_price
            close_reason = Const.ORDER_CLOSE_REASON_TAKE_PROFIT
        elif candler_bar.signal in [Const.STRONG_BUY, Const.STRONG_BUY]:
            close_price = candler_bar.close
            close_reason = Const.ORDER_CLOSE_REASON_SIGNAL
        else:
            return False

        return self._close_order(close_date_time=candler_bar.date_time,
                                 close_price=close_price,
                                 close_reason=close_reason)

    # def get_order(self) -> Order:
    #     return super().get_order()

    def _close_order(self, close_date_time: datetime, close_price: float, close_reason: str) -> bool:

        self.profit = self.balance - self._get_price_value(close_price)
        self.max_loss_value = self.balance - \
            self._get_price_value(self.max_price)
        self.max_profit_value = self.balance - \
            self._get_price_value(self.min_price)

        return super()._close_order(close_date_time=close_date_time,
                                    close_price=close_price,
                                    close_reason=close_reason)


class Executor:

    def simulate(self, param: ParamSimulation):
        return Simulator(param).execute()

    def simulate_many(self, params: list[ParamSimulation]):
        simulations = []

        for param in params:
            simulations.append(self.simulate(param))

        return simulations

    def simulate_and_save(self, params: list[ParamSimulation]):

        simulations = self.simulate_many(params)
