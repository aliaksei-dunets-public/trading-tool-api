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

from core import Const
import common as cmn
from handler import SessionHandler, OrderHandler, LeverageHandler, ExchangeHandler
from strategy import SignalFactory
import trading_core.common as cmn


class Robot:
    def run(self):
        # get user_id
        user_id = None

        active_sessions = SessionHandler.get_sessions(
            user_id=user_id, status=cmn.SessionStatus.active
        )

        for session in active_sessions:
            session_manager = SessionManager(session)
            session_manager.run()


class SessionManager:
    def __init__(self, session_mdl: cmn.SessionModel):
        self._session_mdl: cmn.SessionModel = session_mdl

        self._trading_mng: TraderBase = TraderManager.get_manager(self._session_mdl)

    def run(self):
        self._trading_mng.run()

        # transaction_mng = TransactionManager()


class TransactionManager:
    pass


class BalanceManager:
    pass


class TraderBase:
    def __init__(self, session_mdl: cmn.SessionModel):
        self.session_mdl: cmn.SessionModel = session_mdl
        self.balance_mng: BalanceManager = BalanceManager()
        self.tranaction_mng: TransactionManager = TransactionManager()

        self.exchange_handler: ExchangeHandler = ExchangeHandler(session_mdl.trader_id)

        self._position_mng: PositionManagerBase = PositionManagerBase.get_manager(
            trading_mng=self
        )

    @staticmethod
    def get_manager(session_model: cmn.SessionModel):
        if session_model.is_simulation:
            return SimulatorManager(session_model)
        else:
            return TraderManager(session_model)

    def run(self):
        signal_data = SignalFactory().get_signal(
            **self.session_mdl, signals_config=[], closed_bars=True
        )

        signal_mdl = cmn.SignalModel(**signal_data)
        self._process_signal(signal_mdl)

    def _process_signal(self, signal_mdl: cmn.SignalModel):
        # Open position exists -> check if required it to close
        if self._position_mng.get_position_status() == cmn.OrderStatus.opened:
            self._decide_to_close_position(signal_mdl)

        # Open position doesn't exist -> check if required to open a new position
        if self._position_mng.get_position_status() in [
            cmn.OrderStatus.canceled,
            cmn.OrderStatus.closed,
            None,
        ]:
            self._decide_to_open_position(signal_mdl)

    def _decide_to_open_position(self, signal_mdl: cmn.SignalModel):
        pass
        # self._position_manager.open_api_position(signal_mdl)
        # self._position_manager.open_db_position(signal_mdl)

    def _decide_to_close_position(self, signal_mdl: cmn.SignalModel):
        pass
        # self._position_manager.close_api_position(signal_mdl)
        # self._position_manager.close_db_position(signal_mdl)


class TraderManager(TraderBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

        self._position_mng.get_api_open_positions()
        self._position_mng.get_db_open_positions()
        self._position_mng.synchronize_positions()

    def _decide_to_open_position(self, signal_mdl: cmn.SignalModel):
        self._position_mng.open_api_position(signal_mdl)
        self._position_mng.open_db_position(signal_mdl)

    def _decide_to_close_position(self, signal_mdl: cmn.SignalModel):
        self._position_mng.close_api_position(signal_mdl)
        self._position_mng.close_db_position(signal_mdl)


class SimulatorManager(TraderBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

        self._position_mng.get_db_open_positions()
        self._position_mng.synchronize_positions()

    def _decide_to_open_position(self, signal_mdl: cmn.SignalModel):
        self._position_mng.open_db_position(signal_mdl)

    def _decide_to_close_position(self, signal_mdl: cmn.SignalModel):
        self._position_mng.close_db_position(signal_mdl)


class PositionManagerBase:
    def __init__(self, trading_mng: TraderBase):
        self._trader_mng: TraderBase = trading_mng

        self._api_positions: dict = {}
        self._db_positions: dict = {}
        self._current_position: PositionBase = None

    @staticmethod
    def get_manager(trading_mng: TraderBase):
        if trading_mng.session_mdl.type == cmn.SessionType.order:
            return OrderManager(trading_mng)
        elif trading_mng.session_mdl.type == cmn.SessionType.leverage:
            return LeverageManager(trading_mng)
        else:
            raise Exception("Robot: Incorrect session type")

    # def get_current_position(self):
    #     return self._current_position

    def get_position_status(self) -> cmn.OrderStatus:
        if self._current_position:
            return self._current_position.get_status()
        else:
            return None

    def get_api_open_positions(self) -> dict:
        pass

    def get_db_open_positions(self) -> dict:
        pass

    def synchronize_positions(self):
        for id, api_position in self._api_positions:
            if id not in self._db_positions:
                pass

        if self._db_positions:
            pass

        # initialize current position

    def open_api_position(self, signal_mdl: cmn.SignalModel):
        pass

    def open_db_position(self, signal_mdl: cmn.SignalModel):
        pass

    def close_api_position(self, signal_mdl: cmn.SignalModel):
        pass

    def close_db_position(self, signal_mdl: cmn.SignalModel):
        pass


class OrderManager(PositionManagerBase):
    # def __init__(self, trading_mng: TraderBase):
    #     super().__init__(trading_mng)

    #     self._current_position: cmn.OrderModel = None

    def get_db_open_positions(self) -> dict:
        open_positions = OrderHandler.get_orders(
            self._trader_mng.session_mdl.id, status=cmn.OrderStatus.opened
        )

        for position in open_positions:
            self._db_positions[position.id] = position

    def get_api_open_positions(self) -> dict:
        open_positions = []

        for position in open_positions:
            self._api_positions[position.id] = position

    def open_db_position(self, signal_mdl: cmn.SignalModel):
        pass


class LeverageManager(PositionManagerBase):
    # def __init__(self, trading_mng: TraderBase):
    #     super().__init__(trading_mng)

    #     self._current_position: PositionBase = None

    def get_db_open_positions(self) -> list:
        self._db_positions = LeverageHandler.get_leverages(
            self._trader_mng.session_mdl.id, status=cmn.OrderStatus.opened
        )

    def open_db_position(self, signal_mdl: cmn.SignalModel):
        pass

    def close_db_position(self, signal_mdl: cmn.SignalModel) -> bool:
        pass

    def open_api_position(self, signal_mdl: cmn.SignalModel):
        pass


class CalculationBase:
    pass


class CalculationLong(CalculationBase):
    pass


class CalculationShort(CalculationBase):
    pass


class PositionBase:
    def __init__(self, trader_mng: TraderBase):
        self._trader_mng = trader_mng
        self._position_mdl = None

    def init_position(self, position_mdl: cmn.OrderModel):
        self._position_mdl = position_mdl

    def get_status(self) -> cmn.OrderStatus:
        if self._position_mdl:
            return self._position_mdl.status
        else:
            return None

    def get_template_position(self, signal_mdl: cmn.SignalModel) -> cmn.OrderModel:
        pass

    def open_position(self, position_mdl: cmn.OrderModel) -> cmn.OrderModel:
        pass

    def close_position(self, signal_mdl: cmn.SignalModel):
        pass

    def _get_quantity(self):
        pass

    def _get_fee(self):
        pass


class Order(PositionBase):
    def get_template_position(self, signal_mdl: cmn.SignalModel) -> cmn.OrderModel:
        oder_data = {
            "session_id": self._trader_mng.session_mdl.id,
            "type": cmn.OrderType.market,
            "side": cmn.OrderSideType.buy,
            "status": cmn.OrderStatus.opened,
            "symbol": self._trader_mng.session_mdl.symbol,
            "quantity": self._get_quantity(),
            "fee": self._get_fee(),
            "open_price": signal_mdl.open,
            "open_datetime": signal_mdl.date_time,
        }
        order_mdl = cmn.OrderModel(**oder_data)
        return order_mdl

    def open_position(self, position_mdl: cmn.OrderModel):
        self._position_mdl = OrderHandler.create_order(position_mdl)
        return self._position_mdl


class LeverageBase(PositionBase):
    def get_template_position(self, signal_mdl: cmn.SignalModel) -> cmn.LeverageModel:
        leverage_data = {
            Const.DB_ORDER_ID: "",
            Const.DB_SESSION_ID: self._trader_mng.session_mdl.id,
            Const.DB_ACCOUNT_ID: "",
            Const.DB_TYPE: cmn.OrderType.market,
            Const.DB_STATUS: cmn.OrderStatus.opened,
            Const.DB_SYMBOL: self._trader_mng.session_mdl.symbol,
            Const.DB_QUANTITY: self._get_quantity(),
            Const.DB_FEE: self._get_fee(),
            Const.DB_OPEN_PRICE: signal_mdl.open,
            Const.DB_OPEN_DATETIME: signal_mdl.date_time,
            Const.DB_LEVERAGE: self._trader_mng.session_mdl.leverage,
            Const.DB_STOP_LOSS: self._calculate_stop_loss(signal_mdl),
            Const.DB_TAKE_PROFIT: self._calculate_take_profit(signal_mdl),
        }

        return cmn.LeverageModel(**leverage_data)

    def open_position(self, position_mdl: cmn.LeverageModel) -> cmn.LeverageModel:
        self._position_mdl = LeverageHandler.create_leverage(position_mdl)
        return self._position_mdl

    def _calculate_stop_loss(self, signal_mdl: cmn.SignalModel) -> float:
        pass

    def _calculate_take_profit(self, signal_mdl: cmn.SignalModel) -> float:
        pass


class LeverageShort(LeverageBase):
    def get_template_position(self, signal_mdl: cmn.SignalModel) -> cmn.LeverageModel:
        leverage_mdl = super().get_template_position(signal_mdl)
        leverage_mdl.side = cmn.OrderSideType.sell
        return leverage_mdl

    def close_position(self, signal_mdl: cmn.SignalModel):
        super().close_position(signal_mdl)

        # if (
        #     self._current_position.stop_loss != 0
        #     and signal_mdl.high >= self._current_position.stop_loss
        # ):
        #     pass
        # elif (
        #     self._current_position.take_profit != 0
        #     and signal_mdl.low <= self._current_position.take_profit
        # ):
        #     pass
        # elif signal_mdl.signal in [cmn.SignalType.BUY, cmn.SignalType.STRONG_BUY]:
        #     pass
        # else:
        #     return False

        # update_query = {
        #     Const.DB_CLOSE_PRICE: signal_mdl.close,
        #     Const.DB_CLOSE_DATETIME: signal_mdl.date_time,
        # }
        # LeverageHandler.update_leverage(
        #     id=self._current_position.id, query=update_query
        # )

    def _calculate_stop_loss(self, signal_mdl: cmn.SignalModel) -> float:
        stop_loss_value = (
            signal_mdl.open * self._trader_mng.session_mdl.stop_loss_rate
        ) / 100

        stop_loss_price = signal_mdl.open + stop_loss_value

        return stop_loss_price if stop_loss_value > 0 else 0

    def _calculate_take_profit(self, signal_mdl: cmn.SignalModel) -> float:
        take_profit_value = (
            signal_mdl.open * self._trader_mng.session_mdl.take_profit_rate
        ) / 100

        take_profit_price = signal_mdl.open - take_profit_value

        return take_profit_price if take_profit_value > 0 else 0


class LeverageLong(LeverageBase):
    def get_template_position(self, signal_mdl: cmn.SignalModel) -> cmn.LeverageModel:
        leverage_mdl = super().get_template_position(signal_mdl)
        leverage_mdl.side = cmn.OrderSideType.buy
        return leverage_mdl

    def _calculate_stop_loss(self, signal_mdl: cmn.SignalModel) -> float:
        stop_loss_value = (
            signal_mdl.open * self._trader_mng.session_mdl.stop_loss_rate
        ) / 100

        stop_loss_price = signal_mdl.open - stop_loss_value

        return stop_loss_price if stop_loss_value > 0 else 0

    def _calculate_take_profit(self, signal_mdl: cmn.SignalModel) -> float:
        take_profit_value = (
            signal_mdl.open * self._trader_mng.session_mdl.take_profit_rate
        ) / 100

        take_profit_price = signal_mdl.open + take_profit_value

        return take_profit_price if take_profit_value > 0 else 0
