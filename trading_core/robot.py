# 1. During creation of the session check/schedule a job based on interval
# 2. The application job read active ssesions and procced the next steps for every session:
# 2.1. Read orders from the database
# 2.2. Read orders from exchange API
# 2.3. Get signals based on session config
# 2.4. Make a desicion regarding existing position/create a new position
# 2.4.1. Call API for open/close a position
# 2.4.2. Call DB
# 2.4.2.1. Add transaction
# 2.4.2.2. Update/Create the position
# 2.4.2.3. Update Balance

from bson import ObjectId

from .core import Const
import trading_core.common as cmn
from .handler import (
    SessionHandler,
    BalanceHandler,
    OrderHandler,
    LeverageHandler,
    ExchangeHandler,
    buffer_runtime_handler,
)
from .strategy import StrategyFactory


class Robot:
    def run(self):
        # get user_id
        user_id = None

        active_sessions = SessionHandler.get_sessions(
            user_id=user_id, status=cmn.SessionStatus.active
        )

        for session_mdl in active_sessions:
            session_manager = SessionManager(session_mdl)
            session_manager.run()


class SessionManager:
    def __init__(self, session_mdl: cmn.SessionModel):
        self._session_mdl: cmn.SessionModel = session_mdl

        self._trader_mng: TraderBase = TraderManager.get_manager(self._session_mdl)

    def run(self):
        self._trader_mng.run()

        # transaction_mng = TransactionManager()


class TransactionManager:
    pass


class BalanceManager:
    def __init__(self, session_id: str):
        self.__balance_mdl = BalanceHandler.get_balance_4_session(session_id=session_id)
        self.__change_indicator = False

    def get_account_id(self):
        return self.__balance_mdl.account_id

    def get_total_balance(self):
        return self.__balance_mdl.total_balance

    def add_fee(self, fee: float):
        self.__balance_mdl.total_fee += fee

    def add_total_profit(self, total_profit: float):
        self.__balance_mdl.total_profit += total_profit

    # Operation value for Open is -, and for Close +
    def recalculate_balance(self, operation_value: float, fee: float):
        self.__balance_mdl.total_balance += operation_value - fee

    def save_balance(self):
        if self.__change_indicator:
            query = {
                "total_balance": self.__balance_mdl.total_balance,
                "total_profit": self.__balance_mdl.total_profit,
                "total_fee": self.__balance_mdl.total_fee,
            }
            BalanceHandler.update_balance(self.__balance_mdl.id, query=query)


class TraderBase:
    def __init__(self, session_mdl: cmn.SessionModel):
        self.session_mdl: cmn.SessionModel = session_mdl
        self.balance_mng: BalanceManager = BalanceManager()
        self.tranaction_mng: TransactionManager = TransactionManager()

        self.data_mng: DataManagerBase = None

    @staticmethod
    def get_manager(session_model: cmn.SessionModel):
        if session_model.session_type == cmn.SessionType.TRADING:
            return TraderManager(session_model)
        elif session_model.session_type == cmn.SessionType.SIMULATION:
            return SimulatorManager(session_model)
        elif session_model.session_type == cmn.SessionType.HISTORY:
            return HistorySimulatorManager(session_model)
        else:
            raise Exception(
                f"TraderBase: Manager can't de detected for session type {session_model.session_type}"
            )

    def run(self):
        # signal_data = SignalFactory().get_signal(
        #     symbol=self.session_mdl.symbol,
        #     interval=self.session_mdl.interval,
        #     strategy=self.session_mdl.strategy,
        #     signals_config=[Const.DEBUG_SIGNAL],
        #     closed_bars=True,
        # )

        strategy_df = (
            StrategyFactory(self.session_mdl.strategy)
            .get_strategy_data(
                symbol=self.session_mdl.symbol,
                interval=self.session_mdl.interval,
                closed_bars=True,
            )
            .tail(1)
        )

        # Init signal instance
        for index, strategy_row in strategy_df.iterrows():
            signal_data = {
                "date_time": index,
                "open": strategy_row["Open"],
                "high": strategy_row["High"],
                "low": strategy_row["Low"],
                "close": strategy_row["Close"],
                "volume": strategy_row["Volume"],
                "strategy": self.session_mdl.strategy,
                "signal": strategy_row[Const.PARAM_SIGNAL],
            }

        signal_mdl = cmn.SignalModel(**signal_data)
        self._process_signal(signal_mdl)

        self.balance_mng.save_balance()

    def _process_signal(self, signal_mdl: cmn.SignalModel):
        # Open position exists -> check if required it to close
        if self._is_open_position():
            self._decide_to_close_position(signal_mdl)

        # Open position doesn't exist -> check if required to open a new position
        if not self._is_open_position():
            self._decide_to_open_position(signal_mdl)

    def _decide_to_open_position(self, signal_mdl: cmn.SignalModel) -> bool:
        return self.data_mng.is_required_to_open_position(signal_mdl)

    def _decide_to_close_position(self, signal_mdl: cmn.SignalModel) -> bool:
        return self.data_mng.is_required_to_close_position(signal_mdl)

    def _is_open_position(self) -> bool:
        return self.data_mng.has_open_position()


class TraderManager(TraderBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

        self.api_mng: DataManagerBase = DataManagerBase.get_api_manager(
            self.session_mdl
        )
        self.data_mng: DataManagerBase = DataManagerBase.get_db_manager(
            self.session_mdl
        )

        self.api_mng.synchronize(self.data_mng)
        self.data_mng.synchronize(self.api_mng)

    def _decide_to_open_position(self, signal_mdl: cmn.SignalModel):
        is_required_to_procced = super()._decide_to_open_position(signal_mdl)
        if is_required_to_procced:
            self.api_mng.open_position(signal_mdl)
            self.data_mng.open_position_based_api(self.api_mng)

        return is_required_to_procced

    def _decide_to_close_position(self, signal_mdl: cmn.SignalModel):
        is_required_to_procced = super()._decide_to_open_position(signal_mdl)
        if is_required_to_procced:
            self.api_mng.close_position(signal_mdl)
            self.data_mng.close_position_based_api(self.api_mng)

        return is_required_to_procced


class SimulatorManager(TraderBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

        self.data_mng: DataManagerBase = DataManagerBase.get_db_manager(
            self.session_mdl
        )

    def _decide_to_open_position(self, signal_mdl: cmn.SignalModel):
        is_required_to_procced = super()._decide_to_open_position(signal_mdl)
        if is_required_to_procced:
            self.data_mng.open_position(signal_mdl)

        return is_required_to_procced

    def _decide_to_close_position(self, signal_mdl: cmn.SignalModel):
        is_required_to_procced = super()._decide_to_open_position(signal_mdl)
        if is_required_to_procced:
            self.data_mng.close_position(signal_mdl)

        return is_required_to_procced


class HistorySimulatorManager(TraderBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

        self.data_mng: DataManagerBase = DataManagerBase.get_local_manager(
            self.session_mdl
        )

    def run(self):
        strategy_df = (
            StrategyFactory(self.session_mdl.strategy)
            .get_strategy_data(
                symbol=self.session_mdl.symbol,
                interval=self.session_mdl.interval,
                closed_bars=True,
            )
            .tail(1)
        )

        # Init signal instance
        for index, strategy_row in strategy_df.iterrows():
            signal_data = {
                "date_time": index,
                "open": strategy_row["Open"],
                "high": strategy_row["High"],
                "low": strategy_row["Low"],
                "close": strategy_row["Close"],
                "volume": strategy_row["Volume"],
                "strategy": self.session_mdl.strategy,
                "signal": strategy_row[Const.PARAM_SIGNAL],
            }

        signal_mdl = cmn.SignalModel(**signal_data)
        self._process_signal(signal_mdl)

    def _decide_to_open_position(self, signal_mdl: cmn.SignalModel):
        is_required_to_procced = super()._decide_to_open_position(signal_mdl)
        if is_required_to_procced:
            self.data_mng.open_position(signal_mdl)

        return is_required_to_procced

    def _decide_to_close_position(self, signal_mdl: cmn.SignalModel):
        is_required_to_procced = super()._decide_to_open_position(signal_mdl)
        if is_required_to_procced:
            self.data_mng.close_position(signal_mdl)

        return is_required_to_procced


class DataManagerBase:
    def __init__(self, trader_mng: TraderBase):
        self._session_mdl: cmn.SessionModel = trader_mng.session_mdl
        self._balance_mng = trader_mng.balance_mng

        self._exchange_handler: ExchangeHandler = ExchangeHandler(
            self._session_mdl.trader_id
        )

        symbol_handler = buffer_runtime_handler.get_symbol_handler(
            self._session_mdl.trader_id
        )
        self._symbol_mdl = symbol_handler.get_symbol(self._session_mdl.symbol)

        self._side_mng: SideManager = None

        self._open_positions: dict(cmn.OrderModel) = None
        self._current_position: cmn.OrderModel = None

        self._init_open_positions()

    @staticmethod
    def get_api_manager(trader_mng: TraderBase):
        if trader_mng.session_mdl.trading_type == cmn.TradingType.SPOT:
            return OrderApiManager(trader_mng)
        elif trader_mng.session_mdl.trading_type == cmn.TradingType.LEVERAGE:
            return LeverageApiManager(trader_mng)
        else:
            raise Exception(
                "Robot: API Manager - Incorrect session type {session_mdl.trading_type}"
            )

    @staticmethod
    def get_db_manager(trader_mng: TraderBase):
        if trader_mng.session_mdl.trading_type == cmn.TradingType.SPOT:
            return OrderDatabaseManager(trader_mng)
        elif trader_mng.session_mdl.trading_type == cmn.TradingType.LEVERAGE:
            return LeverageDatabaseManager(trader_mng)
        else:
            raise Exception(
                "Robot: DB Manager - Incorrect trading type {session_mdl.trading_type}"
            )

    @staticmethod
    def get_local_manager(trader_mng: TraderBase):
        if trader_mng.session_mdl.trading_type == cmn.TradingType.SPOT:
            return OrderLocalDataManager(trader_mng)
        elif trader_mng.session_mdl.trading_type == cmn.TradingType.LEVERAGE:
            return LeverageLocalDataManager(trader_mng)
        else:
            raise Exception(
                "Robot: Local Manager - Incorrect trading type {session_mdl.trading_type}"
            )

    def is_required_to_open_position(self, signal_mdl: cmn.SignalModel) -> bool:
        pass

    def is_required_to_close_position(self, signal_mdl: cmn.SignalModel) -> bool:
        return self._side_mng.is_required_to_close_position(
            position_mdl=self._current_position, signal_mdl=signal_mdl
        )

    def open_position(self, signal_mdl: cmn.SignalModel) -> cmn.OrderModel:
        self._set_side_mng(signal_type=signal_mdl.signal)

    def close_position(self, signal_mdl: cmn.SignalModel) -> bool:
        raise Exception(f"DataManagerBase: close_position() isn't implemented")

    def get_current_position(self) -> cmn.OrderModel:
        return self._current_position

    def get_positions(self) -> list:
        return None

    def get_open_positions(self) -> list:
        return None

    def has_open_position(self) -> bool:
        return True if self._current_position else False

    def synchronize(self, data_mng):
        raise Exception(f"DataManagerBase: synchronize() isn't implemented")

    def _init_open_positions(self):
        current_postion = None
        self._open_positions = self.get_open_positions()
        if self._open_positions:
            current_postion = self._open_positions[0]

        self._set_current_postion(current_postion)

    def _set_current_postion(self, position_mdl: cmn.OrderModel = None):
        if position_mdl:
            self._current_position = position_mdl
        else:
            self._current_position = None

        self._set_side_mng()

    def _set_side_mng(self, signal_type: cmn.SignalType = None):
        if self._current_position:
            self._side_mng = SideManager.get_manager_by_type(
                session_mdl=self._session_mdl, side_type=self._current_position.side
            )
        elif signal_type:
            self._side_mng = SideManager.get_manager_by_signal(
                session_mdl=self._session_mdl, signal_type=signal_type
            )
        else:
            self._side_mng = None

    def _get_open_position_template(self, signal_mdl: cmn.SignalModel) -> dict:
        return {
            # Const.DB_ORDER_ID: "",
            Const.DB_SESSION_ID: self._session_mdl.id,
            # Const.DB_ACCOUNT_ID: "",
            Const.DB_TYPE: cmn.OrderType.market,
            Const.DB_SIDE: self._side_mng.get_side_type(),
            Const.DB_STATUS: cmn.OrderStatus.opened,
            Const.DB_SYMBOL: self._session_mdl.symbol,
            Const.DB_QUANTITY: self._get_quantity(),
            Const.DB_FEE: self._get_fee(),
            # Const.DB_LEVERAGE: self._session_mdl.leverage,
            Const.DB_STOP_LOSS: self._side_mng.get_stop_loss(
                balance=self._balance_mng.get_total_balance(),
                price=self._get_open_price(),
            ),
            Const.DB_TAKE_PROFIT: self._side_mng.get_take_profit(
                balance=self._balance_mng.get_total_balance(),
                price=self._get_open_price(),
            ),
            Const.DB_OPEN_PRICE: self._get_open_price(signal_mdl),
            Const.DB_OPEN_DATETIME: signal_mdl.date_time,
        }

    def _get_close_position_details(self, signal_mdl: cmn.SignalModel) -> dict:
        close_details = self._side_mng.get_close_details(
            position_mdl=self._current_position, signal_mdl=signal_mdl
        )

        if not close_details:
            return None

        close_details[Const.DB_STATUS] = cmn.OrderStatus.closed
        close_details[Const.DB_CLOSE_DATETIME] = signal_mdl.date_time

        return close_details

    def _get_quantity(self, signal_mdl: cmn.SignalModel) -> float:
        symbol_quote_precision = self._symbol_mdl.quote_precision
        total_balance = self._balance_mng.get_total_balance()
        fee = self._get_fee()
        price = self._get_open_price(signal_mdl)

        quantity = ((total_balance - fee) / price) // symbol_quote_precision
        return quantity

    def _get_fee(self) -> float:
        total_balance = self._balance_mng.get_total_balance()
        symbol_fee = self._symbol_mdl.trading_fee
        fee = total_balance * symbol_fee / 100
        return fee

    def _get_open_price(self, signal_mdl: cmn.SignalModel) -> float:
        return signal_mdl.open

    def _recalculate_balance(self):
        # This is negative value for open and position for close position action
        if self._current_position.status == cmn.OrderStatus.opened:
            operation_value = (
                -1 * self._current_position.quantity * self._current_position.open_price
            )
        elif self._current_position.status == cmn.OrderStatus.closed:
            operation_value = (
                self._current_position.quantity * self._current_position.close_price
            )

            self._balance_mng.add_total_profit(self._current_position.total_profit)

        else:
            return None

        self._balance_mng.recalculate_balance(
            operation_value=operation_value, fee=self._current_position.fee
        )


class OrderManagerBase(DataManagerBase):
    def is_required_to_open_position(self, signal_mdl: cmn.SignalModel) -> bool:
        return signal_mdl.signal == cmn.SignalType.STRONG_BUY


class OrderApiManager(OrderManagerBase):
    pass


class OrderDatabaseManager(OrderManagerBase):
    def open_position(self, signal_mdl: cmn.SignalModel) -> cmn.OrderModel:
        super().open_position(signal_mdl)

        position_data = self._get_open_position_template(signal_mdl)
        position_mdl = cmn.OrderModel(**position_data)
        created_position_mdl = OrderHandler.create_order(position_mdl)

        self._set_current_postion(created_position_mdl)

        return created_position_mdl

    def close_position(self, signal_mdl: cmn.SignalModel) -> bool:
        pass

    def get_positions(self) -> list[cmn.OrderModel]:
        return OrderHandler.get_orders(
            session_id=self._session_mdl.id, status=cmn.OrderStatus.opened
        )


class OrderLocalDataManager(OrderManagerBase):
    pass


class LeverageManagerBase(DataManagerBase):
    def is_required_to_open_position(self, signal_mdl: cmn.SignalModel) -> bool:
        return signal_mdl.signal in [
            cmn.SignalType.STRONG_BUY,
            cmn.SignalType.STRONG_SELL,
        ]

    def open_position(self, signal_mdl: cmn.SignalModel) -> cmn.LeverageModel:
        super().open_position(signal_mdl)
        position_data = self._get_open_position_template(signal_mdl)
        position_mdl = cmn.LeverageModel(**position_data)
        return position_mdl

    def _get_open_position_template(self, signal_mdl: cmn.SignalModel) -> dict:
        position_data = super()._get_open_position_template(signal_mdl)
        position_data[Const.DB_ORDER_ID] = "1"
        position_data[Const.DB_ACCOUNT_ID] = self._balance_mng.get_account_id()
        position_data[Const.DB_LEVERAGE] = self._session_mdl.leverage
        return position_data


class LeverageApiManager(LeverageManagerBase):
    pass


class LeverageDatabaseManager(LeverageManagerBase):
    def open_position(self, signal_mdl: cmn.SignalModel) -> cmn.LeverageModel:
        # Get Template Position Model from the parent
        position_mdl = super().open_position(signal_mdl)

        # Create Leverage in the Database
        created_position_mdl = LeverageHandler.create_leverage(position_mdl)

        # Set the created leverage as a current position
        self._set_current_postion(created_position_mdl)

        # Recalulate balance after open a position
        self._recalculate_balance()

        return created_position_mdl

    def close_position(self, signal_mdl: cmn.SignalModel) -> bool:
        close_details = super().close_position(signal_mdl)

        if not close_details:
            return False

        result = LeverageHandler.update_leverage(
            id=self._current_position.id, query=close_details
        )

        # Recalulate balance after close the position
        self._recalculate_balance()

        # Set the current position = None
        self._set_current_postion()

        return result

    def get_positions(self) -> list[cmn.LeverageModel]:
        return LeverageHandler.get_leverages(session_id=self._session_mdl.id)

    def get_open_positions(self) -> dict:
        return LeverageHandler.get_leverages(
            session_id=self._session_mdl.id, status=cmn.OrderStatus.opened
        )


class LeverageLocalDataManager(LeverageManagerBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

        self._local_positions: dict(cmn.LeverageModel) = None

    def open_position(self, signal_mdl: cmn.SignalModel) -> cmn.LeverageModel:
        # Get Template Position Model from the parent
        position_mdl = super().open_position(signal_mdl)

        # Simulate creation of the order
        position_mdl.id = str(ObjectId())

        # Set the created leverage as a current position
        self._set_current_postion(position_mdl)

        # Add current postiojn to the local postion storega
        self._local_positions[position_mdl.id] = position_mdl

        return position_mdl

    def close_position(self, signal_mdl: cmn.SignalModel) -> bool:
        close_details = super().close_position(signal_mdl)

        if not close_details:
            return False

        self._local_positions[self._current_position.id][
            Const.DB_STATUS
        ] = close_details[Const.DB_STATUS]
        self._local_positions[self._current_position.id][
            Const.DB_CLOSE_DATETIME
        ] = close_details[Const.DB_CLOSE_DATETIME]
        self._local_positions[self._current_position.id][
            Const.DB_CLOSE_PRICE
        ] = close_details[Const.DB_CLOSE_PRICE]
        self._local_positions[self._current_position.id][
            Const.DB_CLOSE_REASON
        ] = close_details[Const.DB_CLOSE_REASON]

        # Set the current position = None
        self._set_current_postion()

        return True

    def get_positions(self) -> list[cmn.LeverageModel]:
        return [pos_mdl for pos_mdl in self._local_positions.values()]


class SideManager:
    def __ini__(self, session_mdl: cmn.SessionModel):
        self._session_mdl: cmn.SessionModel = session_mdl

    @staticmethod
    def get_manager_by_type(
        session_mdl: cmn.SessionModel, side_type: cmn.OrderSideType
    ):
        if side_type == cmn.OrderSideType.buy:
            return BuyManager(session_mdl)
        elif side_type == cmn.OrderSideType.sell:
            return SellManager(session_mdl)
        else:
            raise Exception("Robot: SideManager - Incorrect order side type")

    @staticmethod
    def get_manager_by_signal(
        session_mdl: cmn.SessionModel, signal_type: cmn.SignalType
    ):
        if signal_type == cmn.SignalType.STRONG_BUY:
            return BuyManager(session_mdl)
        elif signal_type == cmn.SignalType.STRONG_SELL:
            return SellManager(session_mdl)
        else:
            raise Exception("Robot: SideManager - Incorrect signal type")

    def is_required_to_close_position(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> bool:
        return self.get_close_details(position_mdl, signal_mdl) != None

    def get_close_details(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> dict:
        pass

    def get_side_type(self) -> cmn.OrderSideType:
        pass

    def get_stop_loss(self, balance: float, price: float) -> float:
        return (balance * self._session_mdl.stop_loss_rate) / 100

    def get_take_profit(self, balance: float, price: float) -> float:
        return (balance * self._session_mdl.take_profit_rate) / 100


# Short Positions
class SellManager(SideManager):
    def get_close_details(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> dict:
        close_price = 0
        close_reason = ""
        total_profit = 0

        if position_mdl.stop_loss != 0 and signal_mdl.high >= position_mdl.stop_loss:
            close_price = position_mdl.stop_loss
            close_reason = cmn.OrderCloseReason.STOP_LOSS
        elif (
            position_mdl.take_profit != 0 and signal_mdl.low <= position_mdl.take_profit
        ):
            close_price = position_mdl.take_profit
            close_reason = cmn.OrderCloseReason.TAKE_PROFIT
        elif signal_mdl.signal in [cmn.SignalType.STRONG_BUY, cmn.SignalType.BUY]:
            close_price = signal_mdl.close
            close_reason = cmn.OrderCloseReason.SIGNAL
        else:
            return None

        total_profit = position_mdl.quantity * (position_mdl.open_price - close_price)

        return {
            Const.DB_CLOSE_PRICE: close_price,
            Const.DB_CLOSE_REASON: close_reason,
            Const.DB_TOTAL_PROFIT: total_profit,
        }

    def get_side_type(self):
        return cmn.OrderSideType.sell

    def get_stop_loss(self, balance: float, price: float) -> float:
        stop_loss_value = super().get_stop_loss(balance=balance, price=price)
        if stop_loss_value > 0:
            return price + stop_loss_value
        else:
            return 0

    def get_take_profit(self, balance: float, price: float) -> float:
        take_profit_value = super().get_take_profit(balance=balance, price=price)
        if take_profit_value > 0:
            return price - take_profit_value
        else:
            return 0


# LONG Position
class BuyManager(SideManager):
    def get_close_details(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> dict:
        close_price = 0
        close_reason = ""
        total_profit = 0

        if position_mdl.stop_loss != 0 and signal_mdl.low <= position_mdl.stop_loss:
            close_price = position_mdl.stop_loss
            close_reason = cmn.OrderCloseReason.STOP_LOSS
        elif (
            position_mdl.take_profit != 0
            and signal_mdl.high >= position_mdl.take_profit
        ):
            close_price = position_mdl.take_profit
            close_reason = cmn.OrderCloseReason.TAKE_PROFIT
        elif signal_mdl.signal in [cmn.SignalType.STRONG_SELL, cmn.SignalType.SELL]:
            close_price = signal_mdl.close
            close_reason = cmn.OrderCloseReason.SIGNAL
        else:
            return None

        total_profit = position_mdl.quantity * (close_price - position_mdl.open_price)

        return {
            Const.DB_CLOSE_PRICE: close_price,
            Const.DB_CLOSE_REASON: close_reason,
            Const.DB_TOTAL_PROFIT: total_profit,
        }

    def get_side_type(self):
        return cmn.OrderSideType.buy

    def get_stop_loss(self, balance: float, price: float) -> float:
        stop_loss_value = super().get_stop_loss(balance=balance, price=price)
        if stop_loss_value > 0:
            return price - stop_loss_value
        else:
            return 0

    def get_take_profit(self, balance: float, price: float) -> float:
        take_profit_value = super().get_take_profit(balance=balance, price=price)
        if take_profit_value > 0:
            return price + take_profit_value
        else:
            return 0
