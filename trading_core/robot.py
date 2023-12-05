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

from decimal import Decimal, ROUND_DOWN
from datetime import datetime
from bson import ObjectId

from .core import Const, logger
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


class BalanceManager:
    def __init__(self, balance_mdl: cmn.BalanceModel):
        self.__balance_mdl: cmn.BalanceModel = balance_mdl
        self.__change_indicator: bool = False

    def get_balance_model(self):
        return self.__balance_mdl

    def get_account_id(self):
        return self.__balance_mdl.account_id

    def get_total_balance(self):
        return self.__balance_mdl.total_balance

    def add_fee(self, fee: float):
        self.__balance_mdl.total_fee += fee
        self.__change_indicator = True

    def add_total_profit(self, total_profit: float):
        self.__balance_mdl.total_profit += total_profit
        self.__change_indicator = True

    # Operation value for Open is -, and for Close +
    def recalculate_balance(self, position_balance: float, fee: float = 0):
        self.__balance_mdl.total_balance = (
            self.__balance_mdl.total_balance + position_balance - fee
        )
        self.__change_indicator = True

    def save_balance(self):
        if self.__change_indicator:
            query = {
                "total_balance": self.__balance_mdl.total_balance,
                "total_profit": self.__balance_mdl.total_profit,
                "total_fee": self.__balance_mdl.total_fee,
            }
            is_success = BalanceHandler.update_balance(
                self.__balance_mdl.id, query=query
            )

        self.__change_indicator = False


class SessionManager:
    def __init__(self, session_mdl: cmn.SessionModel):
        self._session_mdl: cmn.SessionModel = session_mdl
        self._trader_mng: TraderBase = TraderManager.get_manager(self._session_mdl)

    def run(self):
        logger.info(
            f"{self.__class__.__name__}: Session {self._session_mdl.id} has started."
        )
        self._trader_mng.run()

    def get_positions(self) -> list:
        return self._trader_mng.get_positions()

    def get_balance_manager(self) -> BalanceManager:
        return self._trader_mng.balance_mng

    def open_position(self, open_mdl: cmn.OrderOpenModel):
        return self._trader_mng.open_position(open_mdl)

    def close_position(self) -> bool:
        return self._trader_mng.close_position()


class TraderBase:
    def __init__(self, session_mdl: cmn.SessionModel):
        self.session_mdl: cmn.SessionModel = session_mdl
        self.balance_mng: BalanceManager = None
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

    def get_positions(self) -> list:
        position: cmn.OrderModel = None
        positions = self.data_mng.get_positions()

        for position in positions:
            position.calculate_percent()
            position.calculate_high_percent()
            position.calculate_low_percent()

        return positions

    def open_position(self, open_mdl: cmn.OrderOpenModel) -> cmn.OrderOpenModel:
        if not self.data_mng.has_open_position():
            open_mdl.open_reason = cmn.OrderReason.MANUAL
            position = self.data_mng.open_position(open_mdl)
            self.balance_mng.save_balance()
            return position

    def close_position(self) -> bool:
        if self.data_mng.has_open_position():
            if self.data_mng.close_position():
                self.balance_mng.save_balance()
                return True
            else:
                return False

    def run(self):
        logger.info(f"{self.__class__.__name__}: Trading has started.")

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
        if self.data_mng.has_open_position():
            self._recalculate_position(signal_mdl)
            if self.data_mng.is_required_to_close_position(signal_mdl):
                self._decide_to_close_position(signal_mdl)

        # Open position doesn't exist -> check if required to open a new position
        if not self.data_mng.has_open_position():
            if self.data_mng.is_required_to_open_position(signal_mdl):
                self._decide_to_open_position(signal_mdl)

    def _decide_to_open_position(self, signal_mdl: cmn.SignalModel):
        self.data_mng.open_position_by_signal(signal_mdl)

    def _decide_to_close_position(self, signal_mdl: cmn.SignalModel):
        self.data_mng.close_position_by_signal(signal_mdl)

    def _recalculate_position(self, signal_mdl: cmn.SignalModel):
        self.data_mng.recalculate_position(signal_mdl)


class TraderManager(TraderBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

        self.balance_mng: BalanceManager = BalanceManager(
            BalanceHandler.get_balance_4_session(session_id=self.session_mdl.id)
        )

        self.api_mng: DataManagerBase = DataManagerBase.get_api_manager(trader_mng=self)
        self.data_mng: DataManagerBase = DataManagerBase.get_db_manager(trader_mng=self)

        self.api_mng.synchronize(self.data_mng)
        self.data_mng.synchronize(self.api_mng)

    def _decide_to_open_position(self, signal_mdl: cmn.SignalModel):
        self.api_mng.open_position_by_signal(signal_mdl)
        self.data_mng.open_position_by_signal(signal_mdl)

    def _decide_to_close_position(self, signal_mdl: cmn.SignalModel):
        self.api_mng.close_position_by_signal(signal_mdl)
        self.data_mng.open_position_by_signal(signal_mdl)


class SimulatorManager(TraderBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

        self.balance_mng: BalanceManager = BalanceManager(
            BalanceHandler.get_balance_4_session(session_id=self.session_mdl.id)
        )

        self.data_mng: DataManagerBase = DataManagerBase.get_db_manager(trader_mng=self)


class HistorySimulatorManager(TraderBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

        balance_mdl = cmn.BalanceModel(
            **{
                "session_id": self.session_mdl.id,
                "account_id": "1",
                "currency": "USD",
                "init_balance": 100,
            }
        )

        self.balance_mng: BalanceManager = BalanceManager(balance_mdl)

        self.data_mng: DataManagerBase = DataManagerBase.get_local_manager(
            trader_mng=self
        )

    def run(self):
        logger.info(f"{self.__class__.__name__}: History Simulation has started")

        strategy_df = StrategyFactory(self.session_mdl.strategy).get_strategy_data(
            symbol=self.session_mdl.symbol,
            interval=self.session_mdl.interval,
            limit=400,
            closed_bars=True,
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


class DataManagerBase:
    def __init__(self, trader_mng: TraderBase):
        self._session_mdl: cmn.SessionModel = trader_mng.session_mdl
        self._balance_mng: BalanceManager = trader_mng.balance_mng

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
        raise Exception(
            f"DataManagerBase: is_required_to_open_position() isn't implemented"
        )

    def is_required_to_close_position(self, signal_mdl: cmn.SignalModel) -> bool:
        return self._side_mng.is_required_to_close_position(
            position_mdl=self._current_position, signal_mdl=signal_mdl
        )

    def open_position(self, open_mdl: cmn.OrderOpenModel) -> cmn.OrderModel:
        # Prepate model for opennig
        position_mdl = self._prepare_open_position(open_mdl)

        # Persit an openning position
        created_position_mdl = self._open_position(position_mdl)
        # Post processing of the position
        created_position_mdl = self._after_open_position(
            position_mdl=created_position_mdl
        )

        logger.info(
            f"{self.__class__.__name__}: Position {created_position_mdl.id} for {created_position_mdl.open_datetime} has been opened"
        )

        return created_position_mdl

    def open_position_by_signal(self, signal_mdl: cmn.SignalModel) -> cmn.OrderModel:
        # Get Side type by Signal
        side_type = SideManager.get_side_type_by_signal(signal_type=signal_mdl.signal)

        # Prepafe model for open a position
        open_mdl = cmn.OrderOpenModel(
            side=side_type,
            open_price=signal_mdl.close,
            open_datetime=signal_mdl.date_time,
            open_reason=cmn.OrderReason.SIGNAL,
        )

        # Open the position
        return self.open_position(open_mdl)

    def close_position(self, order_close_mdl: cmn.OrderCloseModel = None) -> bool:
        result = False
        position_id = self._current_position.id

        # Generate current order close model for Manual Close
        if not order_close_mdl:
            close_price = self._get_current_price(price_type=cmn.PriceType.ASK)

            close_details_data = {
                Const.DB_STATUS: cmn.OrderStatus.closed,
                Const.DB_CLOSE_DATETIME: datetime.now(),
                Const.DB_CLOSE_PRICE: close_price,
                Const.DB_CLOSE_REASON: cmn.OrderReason.MANUAL,
                Const.DB_TOTAL_PROFIT: self._side_mng.get_total_profit(
                    quantity=self._current_position.quantity,
                    open_price=self._current_position.open_price,
                    close_price=close_price,
                ),
            }

            order_close_mdl = cmn.OrderCloseModel(**close_details_data)

        order_close_mdl = self._prepare_close_position(order_close_mdl)
        if order_close_mdl:
            result = self._close_position(order_close_mdl)
            if result:
                self._after_close_position(order_close_mdl=order_close_mdl)

                logger.info(
                    f"{self.__class__.__name__}: Position {position_id} for {order_close_mdl.close_datetime} has been closed"
                )

        return result

    def close_position_by_signal(self, signal_mdl: cmn.SignalModel) -> bool:
        order_close_mdl = self._side_mng.get_close_details_by_signal(
            position_mdl=self._current_position, signal_mdl=signal_mdl
        )

        return self.close_position(order_close_mdl)

    def recalculate_position(self, signal_mdl: cmn.SignalModel):
        # Highest Order price
        self._current_position.calculate_high_price(signal_mdl.high)

        # Lowest Order price
        self._current_position.calculate_low_price(signal_mdl.low)

        # Calculate Trailing Stop
        if self._current_position.is_trailing_stop:
            self._calculate_trailing_stop_loss(signal_mdl)

        trailing_stop_mdl = cmn.TrailingStopModel(
            **self._current_position.to_mongodb_doc()
        )

        if not self._update_position(trailing_stop_mdl):
            raise Exception(
                f"DataManagerBase: _update_position() - Error during update position {self._current_position.id}"
            )

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

    def _get_open_position_template(self, open_mdl: cmn.OrderOpenModel) -> dict:
        open_price = self._get_open_price(open_mdl.open_price)

        return {
            Const.DB_SESSION_ID: self._session_mdl.id,
            Const.DB_TYPE: open_mdl.type,
            Const.DB_SIDE: self._side_mng.get_side_type(),
            Const.DB_STATUS: cmn.OrderStatus.opened,
            Const.DB_SYMBOL: self._session_mdl.symbol,
            Const.DB_QUANTITY: self._get_quantity(open_price),
            Const.DB_FEE: self._get_fee(),
            Const.DB_STOP_LOSS: self._side_mng.get_stop_loss(open_price),
            Const.DB_IS_TRAILING_STOP: self._session_mdl.is_trailing_stop,
            Const.DB_TAKE_PROFIT: self._side_mng.get_take_profit(open_price),
            Const.DB_OPEN_PRICE: open_price,
            Const.DB_OPEN_DATETIME: open_mdl.open_datetime,
            Const.DB_OPEN_REASON: open_mdl.open_reason,
            Const.DB_HIGH_PRICE: open_price,
            Const.DB_LOW_PRICE: open_price,
        }

    def _prepare_open_position(self, open_mdl: cmn.OrderOpenModel) -> cmn.OrderModel:
        # Set Side manager by Side Type
        self._set_side_mng(side_type=open_mdl.side)

    def _open_position(self, position_mdl: cmn.OrderModel):
        raise Exception(f"DataManagerBase: _open_position() isn't implemented")

    def _after_open_position(self, position_mdl: cmn.OrderModel):
        # Set the created leverage as a current position
        self._set_current_postion(position_mdl)

        # Recalulate balance after open a position
        self._recalculate_balance()

        return position_mdl

    def _prepare_close_position(
        self, order_close_mdl: cmn.OrderCloseModel
    ) -> cmn.OrderCloseModel:
        if order_close_mdl:
            self._current_position.status = order_close_mdl.status
            self._current_position.close_datetime = order_close_mdl.close_datetime
            self._current_position.close_price = order_close_mdl.close_price
            self._current_position.close_reason = order_close_mdl.close_reason
            self._current_position.total_profit = order_close_mdl.total_profit

            return order_close_mdl
        else:
            return None

    def _close_position(self, order_close_mdl: cmn.OrderCloseModel) -> bool:
        raise Exception(f"DataManagerBase: _close_position() isn't implemented")

    def _update_position(self, trailing_stop_mdl: cmn.TrailingStopModel) -> bool:
        raise Exception(f"DataManagerBase: _update_position() isn't implemented")

    def _after_close_position(self, order_close_mdl: cmn.OrderCloseModel):
        # Recalulate balance after close the position
        self._recalculate_balance()

        # Set the current position = None
        self._set_current_postion()

    def _set_current_postion(self, position_mdl: cmn.OrderModel = None):
        if position_mdl:
            self._current_position = position_mdl
        else:
            self._current_position = None

        self._set_side_mng()

    def _set_side_mng(self, side_type: cmn.OrderSideType = None):
        if self._current_position:
            self._side_mng = SideManager.get_manager(
                session_mdl=self._session_mdl, side_type=self._current_position.side
            )
        elif side_type:
            self._side_mng = SideManager.get_manager(
                session_mdl=self._session_mdl, side_type=side_type
            )
        else:
            self._side_mng = None

    def _get_open_price(self, open_price: float = 0) -> float:
        if not open_price:
            open_price = self._get_current_price()

        return open_price

    def _get_quantity(self, open_price: float) -> float:
        symbol_quote_precision = self._symbol_mdl.quote_precision
        fee = self._get_fee()
        total_balance_without_fee = self._get_current_balance(fee)
        price = self._get_open_price(open_price)

        quantity = total_balance_without_fee / price

        rounded_value = Decimal(str(quantity)).quantize(
            Decimal("1e-{0}".format(symbol_quote_precision)), rounding=ROUND_DOWN
        )

        quantity_round_down = float(rounded_value)

        if quantity_round_down <= 0:
            raise Exception(
                f"{self.__class__.__name__}: It's not enough balance {total_balance_without_fee} for trading"
            )

        return quantity_round_down

    def _get_fee(self) -> float:
        total_balance = self._get_current_balance()
        symbol_fee = self._symbol_mdl.trading_fee
        fee = total_balance * symbol_fee / 100
        return fee

    def _get_current_price(
        self, price_type: cmn.PriceType = cmn.PriceType.BID
    ) -> float:
        # Get current price from exchnage handler
        param = cmn.HistoryDataParam(
            interval=self._session_mdl.interval,
            symbol=self._session_mdl.symbol,
            limit=1,
        )
        history_data = self._exchange_handler.get_history_data(
            param, price_type=price_type
        )
        candle_bar = history_data.getDataFrame().tail(1)

        price = candle_bar["Close"].values[0]

        return price

    def _get_current_balance(self, fee: float = 0) -> float:
        # Take Total Balance from Balance Model and take into account Fee if it's required
        return self._balance_mng.get_total_balance() - fee

    def _recalculate_balance(self):
        # This is negative value for open and position for close position action
        if self._current_position.status == cmn.OrderStatus.opened:
            position_balance = self._current_position.calculate_balance()
            self._balance_mng.add_fee(self._current_position.fee)
            self._balance_mng.recalculate_balance(
                position_balance=(-1 * position_balance), fee=self._current_position.fee
            )

        elif self._current_position.status == cmn.OrderStatus.closed:
            position_volume = (
                self._current_position.calculate_balance()
                + self._current_position.total_profit
            )
            self._balance_mng.add_total_profit(self._current_position.total_profit)
            self._balance_mng.recalculate_balance(position_balance=position_volume)

    def _calculate_trailing_stop_loss(self, signal_mdl: cmn.SignalModel):
        pass

    def _calculate_percent(self, source_price: float, target_price: float) -> float:
        percent = (
            ((target_price - source_price) / source_price) * 100 if source_price else 0
        )
        return percent


class OrderManagerBase(DataManagerBase):
    def is_required_to_open_position(self, signal_mdl: cmn.SignalModel) -> bool:
        return signal_mdl.signal == cmn.SignalType.STRONG_BUY

    def _prepare_open_position(self, open_mdl: cmn.OrderOpenModel) -> cmn.OrderModel:
        super()._prepare_open_position(open_mdl)
        position_data = self._get_open_position_template(open_mdl)
        return cmn.OrderModel(**position_data)


class OrderApiManager(OrderManagerBase):
    pass


class OrderDatabaseManager(OrderManagerBase):
    # def open_position_by_signal(self, signal_mdl: cmn.SignalModel) -> cmn.OrderModel:
    #     super().open_position_by_signal(signal_mdl)

    #     position_data = self._get_open_position_template(open_datetime=open_datetime, open_price=open_price)
    #     position_mdl = cmn.OrderModel(**position_data)
    #     created_position_mdl = OrderHandler.create_order(position_mdl)

    #     self._set_current_postion(created_position_mdl)

    #     return created_position_mdl

    def close_position_by_signal(self, signal_mdl: cmn.SignalModel) -> bool:
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

    def _get_open_position_template(self, open_mdl: cmn.OrderOpenModel) -> dict:
        position_data = super()._get_open_position_template(open_mdl)
        position_data[Const.DB_ORDER_ID] = "1"
        position_data[Const.DB_ACCOUNT_ID] = self._balance_mng.get_account_id()
        position_data[Const.DB_LEVERAGE] = self._session_mdl.leverage
        return position_data

    def _prepare_open_position(self, open_mdl: cmn.OrderOpenModel) -> cmn.LeverageModel:
        super()._prepare_open_position(open_mdl)
        position_data = self._get_open_position_template(open_mdl)
        return cmn.LeverageModel(**position_data)

    def _get_current_balance(self, fee: float = 0) -> float:
        return super()._get_current_balance(fee) * self._session_mdl.leverage

    def _calculate_trailing_stop_loss(self, signal_mdl: cmn.SignalModel):
        self._current_position.stop_loss = self._side_mng.get_trailing_stop_loss(
            position_mdl=self._current_position, signal_mdl=signal_mdl
        )


class LeverageApiManager(LeverageManagerBase):
    pass


class LeverageDatabaseManager(LeverageManagerBase):
    def get_positions(self) -> list[cmn.LeverageModel]:
        position: cmn.LeverageModel = None
        positions = LeverageHandler.get_leverages(session_id=self._session_mdl.id)

        if self._current_position:
            current_price = self._get_current_price(cmn.PriceType.ASK)

            for position in positions:
                if position.status == cmn.OrderStatus.opened:
                    position.close_price = current_price
                    position.close_datetime = datetime.now()
                    position.total_profit = self._side_mng.get_total_profit(
                        quantity=self._current_position.quantity,
                        open_price=self._current_position.open_price,
                        close_price=current_price,
                    )

        return positions

    def get_open_positions(self) -> dict:
        return LeverageHandler.get_leverages(
            session_id=self._session_mdl.id, status=cmn.OrderStatus.opened
        )

    def _open_position(self, position_mdl: cmn.LeverageModel):
        return LeverageHandler.create_leverage(position_mdl)

    def _update_position(self, trailing_stop_mdl: cmn.TrailingStopModel) -> bool:
        return LeverageHandler.update_leverage(
            id=self._current_position.id, query=trailing_stop_mdl.to_mongodb_doc()
        )

    def _close_position(self, order_close_mdl: cmn.OrderCloseModel) -> bool:
        return LeverageHandler.update_leverage(
            id=self._current_position.id, query=order_close_mdl.to_mongodb_doc()
        )


class LeverageLocalDataManager(LeverageManagerBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

        self._local_positions: dict(cmn.LeverageModel) = {}

    def get_positions(self) -> list[cmn.LeverageModel]:
        return [pos_mdl for pos_mdl in self._local_positions.values()]

    def _open_position(self, position_mdl: cmn.LeverageModel):
        # Simulate creation of the order
        position_mdl.id = str(ObjectId())
        return position_mdl

    def _after_open_position(self, position_mdl: cmn.LeverageModel):
        super()._after_open_position(position_mdl=position_mdl)

        # Add current postiojn to the local postion storega
        self._local_positions[position_mdl.id] = position_mdl
        return position_mdl

    def _close_position(self, order_close_mdl: cmn.OrderCloseModel) -> bool:
        current_position: cmn.LeverageModel = self._local_positions[
            self._current_position.id
        ]

        current_position.status = order_close_mdl.status
        current_position.close_datetime = order_close_mdl.close_datetime
        current_position.close_price = order_close_mdl.close_price
        current_position.close_reason = order_close_mdl.close_reason
        current_position.total_profit = order_close_mdl.total_profit

        return True

    def _update_position(self, trailing_stop_mdl: cmn.TrailingStopModel) -> bool:
        return True


class SideManager:
    def __init__(self, session_mdl: cmn.SessionModel):
        self._session_mdl: cmn.SessionModel = session_mdl

    @staticmethod
    def get_manager(session_mdl: cmn.SessionModel, side_type: cmn.OrderSideType):
        if side_type == cmn.OrderSideType.buy:
            return BuyManager(session_mdl)
        elif side_type == cmn.OrderSideType.sell:
            return SellManager(session_mdl)
        else:
            raise Exception("Robot: SideManager - Incorrect order side type")

    @staticmethod
    def get_side_type_by_signal(signal_type: cmn.SignalType) -> cmn.OrderSideType:
        if signal_type == cmn.SignalType.STRONG_BUY:
            return cmn.OrderSideType.buy
        elif signal_type == cmn.SignalType.STRONG_SELL:
            return cmn.OrderSideType.sell
        else:
            raise Exception("Robot: SideManager - Incorrect signal type")

    def is_required_to_close_position(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> bool:
        return self.get_close_details_by_signal(position_mdl, signal_mdl) != None

    def get_close_details_by_signal(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> cmn.OrderCloseModel:
        raise Exception(
            "Robot: SideManager - get_close_details_by_signal() isn't implemented"
        )

    def get_side_type(self) -> cmn.OrderSideType:
        raise Exception("Robot: SideManager - get_side_type() isn't implemented")

    def get_stop_loss(self, price: float) -> float:
        return (price * self._session_mdl.stop_loss_rate) / 100

    def get_trailing_stop_loss(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> float:
        pass

    def get_take_profit(self, price: float) -> float:
        return (price * self._session_mdl.take_profit_rate) / 100

    def get_total_profit(
        self, quantity: float, open_price: float, close_price: float
    ) -> float:
        pass


# Short Positions
class SellManager(SideManager):
    def get_close_details_by_signal(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> cmn.OrderCloseModel:
        close_price = 0
        close_reason = ""
        total_profit = 0

        if position_mdl.stop_loss != 0 and signal_mdl.high >= position_mdl.stop_loss:
            close_price = position_mdl.stop_loss
            close_reason = cmn.OrderReason.STOP_LOSS
        elif (
            position_mdl.take_profit != 0 and signal_mdl.low <= position_mdl.take_profit
        ):
            close_price = position_mdl.take_profit
            close_reason = cmn.OrderReason.TAKE_PROFIT
        elif signal_mdl.signal in [cmn.SignalType.STRONG_BUY, cmn.SignalType.BUY]:
            close_price = signal_mdl.close
            close_reason = cmn.OrderReason.SIGNAL
        else:
            return None

        total_profit = self.get_total_profit(
            quantity=position_mdl.quantity,
            open_price=position_mdl.open_price,
            close_price=close_price,
        )

        close_details_data = {
            Const.DB_STATUS: cmn.OrderStatus.closed,
            Const.DB_CLOSE_DATETIME: signal_mdl.date_time,
            Const.DB_CLOSE_PRICE: close_price,
            Const.DB_CLOSE_REASON: close_reason,
            Const.DB_TOTAL_PROFIT: total_profit,
        }

        return cmn.OrderCloseModel(**close_details_data)

    def get_side_type(self):
        return cmn.OrderSideType.sell

    def get_stop_loss(self, price: float) -> float:
        stop_loss_value = super().get_stop_loss(price=price)
        if stop_loss_value > 0:
            return price + stop_loss_value
        else:
            return 0

    def get_trailing_stop_loss(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> float:
        if signal_mdl.signal == cmn.SignalType.SELL:
            value = (position_mdl.open_price * 0.08) / 100

            return position_mdl.open_price - value
        else:
            return position_mdl.stop_loss

    def get_take_profit(self, price: float) -> float:
        take_profit_value = super().get_take_profit(price=price)
        if take_profit_value > 0:
            return price - take_profit_value
        else:
            return 0

    def get_total_profit(
        self, quantity: float, open_price: float, close_price: float
    ) -> float:
        return quantity * (open_price - close_price)


# LONG Position
class BuyManager(SideManager):
    def get_close_details_by_signal(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> cmn.OrderCloseModel:
        close_price = 0
        close_reason = ""
        total_profit = 0

        if position_mdl.stop_loss != 0 and signal_mdl.low <= position_mdl.stop_loss:
            close_price = position_mdl.stop_loss
            close_reason = cmn.OrderReason.STOP_LOSS
        elif (
            position_mdl.take_profit != 0
            and signal_mdl.high >= position_mdl.take_profit
        ):
            close_price = position_mdl.take_profit
            close_reason = cmn.OrderReason.TAKE_PROFIT
        elif signal_mdl.signal in [cmn.SignalType.STRONG_SELL, cmn.SignalType.SELL]:
            close_price = signal_mdl.close
            close_reason = cmn.OrderReason.SIGNAL
        else:
            return None

        total_profit = self.get_total_profit(
            quantity=position_mdl.quantity,
            open_price=position_mdl.open_price,
            close_price=close_price,
        )

        close_details_data = {
            Const.DB_STATUS: cmn.OrderStatus.closed,
            Const.DB_CLOSE_DATETIME: signal_mdl.date_time,
            Const.DB_CLOSE_PRICE: close_price,
            Const.DB_CLOSE_REASON: close_reason,
            Const.DB_TOTAL_PROFIT: total_profit,
        }

        return cmn.OrderCloseModel(**close_details_data)

    def get_side_type(self):
        return cmn.OrderSideType.buy

    def get_stop_loss(self, price: float) -> float:
        stop_loss_value = super().get_stop_loss(price=price)
        if stop_loss_value > 0:
            return price - stop_loss_value
        else:
            return 0

    def get_trailing_stop_loss(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> float:
        if signal_mdl.signal == cmn.SignalType.BUY:
            value = (position_mdl.open_price * 0.08) / 100

            return position_mdl.open_price + value
        else:
            return position_mdl.stop_loss

    def get_take_profit(self, price: float) -> float:
        take_profit_value = super().get_take_profit(price=price)
        if take_profit_value > 0:
            return price + take_profit_value
        else:
            return 0

    def get_total_profit(
        self, quantity: float, open_price: float, close_price: float
    ) -> float:
        return quantity * (close_price - open_price)


class Robot:
    def get_session_manager(self, session_id: str) -> SessionManager:
        session_mdl = self._get_session_mdl(session_id)
        return SessionManager(session_mdl)

    def run_session(self, session_id: str):
        session_mdl = self._get_session_mdl(session_id)
        self._run(session_mdl)

    def run_job(self, interval: str):
        active_sessions = SessionHandler.get_sessions(
            interval=interval, status=cmn.SessionStatus.active
        )

        for session_mdl in active_sessions:
            try:
                self._run(session_mdl)
            except Exception as error:
                logger.error(f"Error during session run - {error}")

    def run_history_simulation(self):
        pass

    def _get_session_mdl(self, session_id) -> cmn.SessionModel:
        return SessionHandler.get_session(session_id)

    def _run(self, session_mdl: cmn.SessionModel):
        session_manager = SessionManager(session_mdl)
        session_manager.run()
