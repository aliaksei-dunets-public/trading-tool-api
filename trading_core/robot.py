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

from .core import Const
import trading_core.common as cmn
from .handler import SessionHandler, OrderHandler, LeverageHandler, ExchangeHandler
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
    pass


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

        self.api_mng: ApiManager = ApiManager.get_manager(self.session_mdl)
        self.data_mng: DatabaseManager = DatabaseManager.get_manager(self.session_mdl)

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

        self.data_mng: DatabaseManager = DatabaseManager.get_manager(self.session_mdl)

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

        self.data_mng: LocalDataManager = LocalDataManager(self.session_mdl)

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
    def __init__(self, session_mdl: cmn.SessionModel):
        self._session_mdl: cmn.SessionModel = session_mdl

        self._exchange_handler: ExchangeHandler = ExchangeHandler(
            self._session_mdl.trader_id
        )

        self._side_mng: SideManager = None

        self._open_positions: dict(cmn.OrderModel) = None
        self._current_position: cmn.OrderModel = None

        self._init_open_positions()

    @staticmethod
    def get_api_manager(session_mdl: cmn.SessionModel):
        if session_mdl.trading_type == cmn.TradingType.SPOT:
            return OrderApiManager(session_mdl)
        elif session_mdl.trading_type == cmn.TradingType.LEVERAGE:
            return LeverageApiManager(session_mdl)
        else:
            raise Exception(
                "Robot: API Manager - Incorrect session type {session_mdl.trading_type}"
            )

    @staticmethod
    def get_db_manager(session_mdl: cmn.SessionModel):
        if session_mdl.trading_type == cmn.TradingType.SPOT:
            return OrderDatabaseManager(session_mdl)
        elif session_mdl.trading_type == cmn.TradingType.LEVERAGE:
            return LeverageDatabaseManager(session_mdl)
        else:
            raise Exception(
                "Robot: DB Manager - Incorrect trading type {session_mdl.trading_type}"
            )

    @staticmethod
    def get_local_manager(session_mdl: cmn.SessionModel):
        if session_mdl.trading_type == cmn.TradingType.SPOT:
            return OrderLocalDataManager(session_mdl)
        elif session_mdl.trading_type == cmn.TradingType.LEVERAGE:
            return LeverageLocalDataManager(session_mdl)
        else:
            raise Exception(
                "Robot: Local Manager - Incorrect trading type {session_mdl.trading_type}"
            )

    def is_required_to_open_position(self, signal_mdl: cmn.SignalModel) -> bool:
        if self._session_mdl.type == cmn.SessionType.order:
            return signal_mdl.signal == cmn.SignalType.STRONG_BUY
        else:
            return signal_mdl.signal in [
                cmn.SignalType.STRONG_BUY,
                cmn.SignalType.STRONG_SELL,
            ]

    def is_required_to_close_position(self, signal_mdl: cmn.SignalModel) -> bool:
        return self._side_mng.is_required_to_close_position(
            position_mdl=self._current_position, signal_mdl=signal_mdl
        )

    def _init_open_positions(self):
        current_postion = None
        open_postions = self.get_positions()
        if open_postions:
            current_postion = open_postions[0]

        self._set_current_postion(current_postion)

    def open_position(self, signal_mdl: cmn.SignalModel) -> cmn.OrderModel:
        self._set_side_mng(signal_type=signal_mdl.signal)

    def close_position(self, signal_mdl: cmn.SignalModel) -> bool:
        raise Exception(f"DataManagerBase: close_position() isn't implemented")

    def get_current_position(self) -> cmn.OrderModel:
        return self._current_position

    def get_positions(self) -> list:
        return None

    def get_open_positions(self) -> dict:
        if not self._open_positions:
            open_postions = self.get_positions()

            for position in open_postions:
                self._open_positions[position.id] = position

        return self._open_positions

    def has_open_position(self) -> bool:
        return True if self._current_position else False

    def synchronize(self, data_mng):
        raise Exception(f"DataManagerBase: synchronize() isn't implemented")

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
            Const.DB_STOP_LOSS: self._side_mng.get_stop_loss(signal_mdl),
            Const.DB_TAKE_PROFIT: self._side_mng.get_take_profit(signal_mdl),
            Const.DB_OPEN_PRICE: signal_mdl.open,
            Const.DB_OPEN_DATETIME: signal_mdl.date_time,
        }

    def _get_quantity(self) -> float:
        raise Exception(f"DataManagerBase: _get_quantity() isn't implemented")

    def _get_fee(self) -> float:
        raise Exception(f"DataManagerBase: _get_fee() isn't implemented")


class OrderManagerBase(DataManagerBase):
    pass


class LeverageManagerBase(DataManagerBase):
    pass


class ApiManager(DataManagerBase):
    def __ini__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)
        self._exchange_handler: ExchangeHandler = ExchangeHandler(
            self._session_mdl.trader_id
        )

    @staticmethod
    def get_manager(session_mdl: cmn.SessionModel):
        if session_mdl.type == cmn.SessionType.order:
            return OrderApiManager(session_mdl)
        elif session_mdl.type == cmn.SessionType.leverage:
            return LeverageApiManager(session_mdl)
        else:
            raise Exception("Robot: ApiManger - Incorrect session type")

    def open_position(self, signal_mdl: cmn.SignalModel) -> cmn.OrderModel:
        pass

    def close_position(self, signal_mdl: cmn.SignalModel) -> bool:
        pass

    def get_current_position(self) -> cmn.OrderModel:
        return self._current_position

    def get_positions(self) -> list:
        pass

    def get_open_positions(self) -> dict:
        if not self._open_positions:
            open_postions = self.get_positions()

            for position_mdl in open_postions:
                self._open_positions[position_mdl.id] = position_mdl

        return self._open_positions

    def synchronize(self, db_mng: DataManagerBase):
        pass


class OrderApiManager(OrderManagerBase):
    pass


class LeverageApiManager(LeverageManagerBase):
    pass


class DatabaseManager(DataManagerBase):
    @staticmethod
    def get_manager(session_mdl: cmn.SessionModel):
        if session_mdl.type == cmn.SessionType.order:
            return OrderDatabaseManager(session_mdl)
        elif session_mdl.type == cmn.SessionType.leverage:
            return LeverageDatabaseManager(session_mdl)
        else:
            raise Exception("Robot: DatabaseManager - Incorrect session type")

    def synchronize(self, api_mng: DataManagerBase):
        pass

    def open_position_based_api(self, api_mng: DataManagerBase):
        pass

    def close_position_based_api(self, api_mng: DataManagerBase):
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


class LeverageDatabaseManager(LeverageManagerBase):
    def open_position(self, signal_mdl: cmn.SignalModel) -> cmn.LeverageModel:
        super().open_position(signal_mdl)

        position_data = self._get_open_position_template(signal_mdl)
        position_mdl = cmn.LeverageModel(**position_data)
        created_position_mdl = LeverageHandler.create_leverage(position_mdl)

        self._set_current_postion(created_position_mdl)

        return created_position_mdl

    def close_position(self, signal_mdl: cmn.SignalModel) -> bool:
        close_details = self._side_mng.get_close_details(
            position_mdl=self._current_position, signal_mdl=signal_mdl
        )

        if not close_details:
            return False

        close_details[Const.DB_STATUS] = cmn.OrderStatus.closed
        close_details[Const.DB_CLOSE_DATETIME] = signal_mdl.date_time

        result = LeverageHandler.update_leverage(
            id=self._current_position.id, query=close_details
        )

        return result

    def get_positions(self) -> list[cmn.LeverageModel]:
        return LeverageHandler.get_leverages(
            session_id=self._session_mdl.id, status=cmn.OrderStatus.opened
        )

    def _get_open_position_template(self, signal_mdl: cmn.SignalModel) -> dict:
        position_data = super()._get_open_position_template(signal_mdl)
        position_data[Const.DB_ORDER_ID] = "1"
        position_data[Const.DB_ACCOUNT_ID] = "1"
        position_data[Const.DB_LEVERAGE] = self._session_mdl.leverage
        return position_data


class OrderLocalDataManager(OrderManagerBase):
    pass


class LeverageLocalDataManager(LeverageManagerBase):
    pass


class LocalDataManager(DataManagerBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

    def open_position(self, signal_mdl: cmn.SignalModel) -> cmn.LeverageModel:
        super().open_position(signal_mdl)

        position_data = self._get_open_position_template(signal_mdl)
        position_mdl = cmn.LeverageModel(**position_data)
        created_position_mdl = LeverageHandler.create_leverage(position_mdl)

        self._set_current_postion(created_position_mdl)

        return created_position_mdl

    def close_position(self, signal_mdl: cmn.SignalModel) -> bool:
        close_details = self._side_mng.get_close_details(
            position_mdl=self._current_position, signal_mdl=signal_mdl
        )

        if not close_details:
            return False

        close_details[Const.DB_STATUS] = cmn.OrderStatus.closed
        close_details[Const.DB_CLOSE_DATETIME] = signal_mdl.date_time

        result = LeverageHandler.update_leverage(
            id=self._current_position.id, query=close_details
        )

        return result

    def get_positions(self) -> list[cmn.LeverageModel]:
        return LeverageHandler.get_leverages(
            session_id=self._session_mdl.id, status=cmn.OrderStatus.opened
        )

    def _get_open_position_template(self, signal_mdl: cmn.SignalModel) -> dict:
        position_data = super()._get_open_position_template(signal_mdl)
        position_data[Const.DB_ORDER_ID] = "1"
        position_data[Const.DB_ACCOUNT_ID] = "1"
        position_data[Const.DB_LEVERAGE] = self._session_mdl.leverage
        return position_data


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

    def get_stop_loss(self, signal_mdl: cmn.SignalModel) -> float:
        return (signal_mdl.open * self._session_mdl.stop_loss_rate) / 100

    def get_take_profit(self, signal_mdl: cmn.SignalModel) -> float:
        return (signal_mdl.open * self._session_mdl.take_profit_rate) / 100


class SellManager(SideManager):
    def get_close_details(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> dict:
        if position_mdl.stop_loss != 0 and signal_mdl.high >= position_mdl.stop_loss:
            return {
                Const.DB_CLOSE_PRICE: position_mdl.stop_loss,
                Const.DB_CLOSE_REASON: cmn.OrderCloseReason.STOP_LOSS,
            }
        elif (
            position_mdl.take_profit != 0 and signal_mdl.low <= position_mdl.take_profit
        ):
            return {
                Const.DB_CLOSE_PRICE: position_mdl.take_profit,
                Const.DB_CLOSE_REASON: cmn.OrderCloseReason.TAKE_PROFIT,
            }
        elif signal_mdl.signal in [cmn.SignalType.STRONG_BUY, cmn.SignalType.BUY]:
            return {
                Const.DB_CLOSE_PRICE: signal_mdl.close,
                Const.DB_CLOSE_REASON: cmn.OrderCloseReason.SIGNAL,
            }
        else:
            return None

    def get_side_type(self):
        return cmn.OrderSideType.sell

    def get_stop_loss(self, signal_mdl: cmn.SignalModel) -> float:
        stop_loss_value = super().get_stop_loss(signal_mdl)
        if stop_loss_value > 0:
            return signal_mdl.open + stop_loss_value
        else:
            return 0

    def get_take_profit(self, signal_mdl: cmn.SignalModel) -> float:
        take_profit_value = super().get_take_profit(signal_mdl)
        if take_profit_value > 0:
            return signal_mdl.open - take_profit_value
        else:
            return 0


class BuyManager(SideManager):
    def get_close_details(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> dict:
        if position_mdl.stop_loss != 0 and signal_mdl.low <= position_mdl.stop_loss:
            return {
                Const.DB_CLOSE_PRICE: position_mdl.stop_loss,
                Const.DB_CLOSE_REASON: cmn.OrderCloseReason.STOP_LOSS,
            }
        elif (
            position_mdl.take_profit != 0
            and signal_mdl.high >= position_mdl.take_profit
        ):
            return {
                Const.DB_CLOSE_PRICE: position_mdl.take_profit,
                Const.DB_CLOSE_REASON: cmn.OrderCloseReason.TAKE_PROFIT,
            }
        elif signal_mdl.signal in [cmn.SignalType.STRONG_SELL, cmn.SignalType.SELL]:
            return {
                Const.DB_CLOSE_PRICE: signal_mdl.close,
                Const.DB_CLOSE_REASON: cmn.OrderCloseReason.SIGNAL,
            }
        else:
            return None

    def get_side_type(self):
        return cmn.OrderSideType.buy

    def get_stop_loss(self, signal_mdl: cmn.SignalModel) -> float:
        stop_loss_value = super().get_stop_loss(signal_mdl)
        if stop_loss_value > 0:
            return signal_mdl.open - stop_loss_value
        else:
            return 0

    def get_take_profit(self, signal_mdl: cmn.SignalModel) -> float:
        take_profit_value = super().get_take_profit(signal_mdl)
        if take_profit_value > 0:
            return signal_mdl.open + take_profit_value
        else:
            return 0
