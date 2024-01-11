from decimal import Decimal, ROUND_DOWN
from datetime import datetime
from bson import ObjectId

from trading_core.common import OrderModel, TrailingStopModel

from .core import Const
import trading_core.common as cmn
from .strategy import StrategyFactory, SignalFactory, Indicator_ATR
from .handler import (
    SessionHandler,
    BalanceHandler,
    OrderHandler,
    LeverageHandler,
    TransactionHandler,
    ExchangeHandler,
    buffer_runtime_handler,
)

import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger("robot")


class TransactionManager:
    def __init__(self, session_mdl: cmn.SessionModel):
        self.__session_mdl: cmn.SessionModel = session_mdl
        self.__transaction_models: list[cmn.TransactionModel] = []

    def add_transaction(
        self,
        type: cmn.TransactionType,
        local_order_id: str = "",
        order_id: str = "",
        date_time: datetime = datetime.now(),
        data: dict = {},
        save: bool = True,
    ):
        transaction_mdl = cmn.TransactionModel(
            **{
                Const.DB_LOCAL_ORDER_ID: local_order_id,
                Const.DB_ORDER_ID: order_id,
                Const.DB_SESSION_ID: self.__session_mdl.id,
                Const.DB_USER_ID: self.__session_mdl.user_id,
                Const.DB_DATE_TIME: date_time,
                Const.DB_TYPE: type,
                Const.DB_TRANSACTION_DATA: data,
            }
        )
        if save:
            self.create_transaction(transaction_mdl)
        else:
            self.add_transaction_model(transaction_mdl)

    def add_transaction_model(self, transaction_mdl: cmn.TransactionModel):
        if transaction_mdl:
            self.__transaction_models.append(transaction_mdl)

            logger.info(
                f"{self.__class__.__name__}: {self.__session_mdl.id} - Add transaction {transaction_mdl.type} for {transaction_mdl.date_time}"
            )

    def create_transaction(self, transaction_mdl: cmn.TransactionModel):
        TransactionHandler().create_transaction(transaction_mdl)
        logger.info(
            f"{self.__class__.__name__}: {self.__session_mdl.id} - The transaction {transaction_mdl.type} for {transaction_mdl.date_time} have been saved"
        )

    def get_transactions(self) -> list:
        return self.__transaction_models

    def save_transactions(self):
        if self.__transaction_models:
            TransactionHandler().create_transactions(self.__transaction_models)

            # Clear transactions buffer
            self.__transaction_models = []

            logger.info(
                f"{self.__class__.__name__}: {self.__session_mdl.id} - The transactions have been saved"
            )


class BalanceManager:
    def __init__(self, balance_mdl: cmn.BalanceModel):
        self.__balance_mdl: cmn.BalanceModel = balance_mdl
        self.__change_indicator: bool = False

    def get_balance_model(self):
        return self.__balance_mdl

    def get_account_id(self):
        return self.__balance_mdl.account_id

    def get_change_indicator(self) -> bool:
        return self.__change_indicator

    def get_total_balance(self):
        return self.__balance_mdl.total_balance

    def add_fee(self, fee: float):
        self.__balance_mdl.total_fee += fee
        self.__change_indicator = True

        logger.info(
            f"{self.__class__.__name__}: {self.__balance_mdl.session_id} - Add Fee = {fee}"
        )

    def add_total_profit(self, total_profit: float):
        self.__balance_mdl.total_profit += total_profit
        self.__change_indicator = True

        logger.info(
            f"{self.__class__.__name__}: {self.__balance_mdl.session_id} - Add Total Profit = {total_profit}"
        )

    def recalculate_balance(self, total_profit: float):
        self.add_total_profit(total_profit)
        self.__balance_mdl.total_balance += total_profit
        self.__change_indicator = True

        logger.info(
            f"{self.__class__.__name__}: {self.__balance_mdl.session_id} - Recalculate the balance with Total Profit = {total_profit}"
        )

    def save_balance(self):
        if self.__change_indicator:
            query = {
                "total_balance": self.__balance_mdl.total_balance,
                "total_profit": self.__balance_mdl.total_profit,
                "total_fee": self.__balance_mdl.total_fee,
            }
            BalanceHandler.update_balance(self.__balance_mdl.id, query=query)

            self.__change_indicator = False

            logger.info(
                f"{self.__class__.__name__}: {self.__balance_mdl.session_id} - The balance has been saved"
            )


class SessionManager:
    def __init__(self, session_mdl: cmn.SessionModel):
        self._session_mdl: cmn.SessionModel = session_mdl
        self._trader_mng: TraderBase = TraderManager.get_manager(self._session_mdl)

    def run(self, **kwargs):
        logger.info(
            f"{self.__class__.__name__}: {self._session_mdl.id} - The Session Run has started"
        )
        self._trader_mng.run(**kwargs)

    def get_positions(self) -> list:
        return self._trader_mng.get_positions()

    def get_transactions(self) -> list:
        return self._trader_mng.transaction_mng.get_transactions()

    def get_balance_manager(self) -> BalanceManager:
        return self._trader_mng.balance_mng

    def open_position(self, open_mdl: cmn.OrderOpenModel):
        logger.info(
            f"{self.__class__.__name__}: {self._session_mdl.id} - The session has triggered to open a position"
        )
        return self._trader_mng.open_position(open_mdl)

    def close_position(self) -> bool:
        logger.info(
            f"{self.__class__.__name__}: {self._session_mdl.id} - The session has triggered to close positions"
        )
        return self._trader_mng.close_position()


class TraderBase:
    def __init__(self, session_mdl: cmn.SessionModel):
        self.session_mdl: cmn.SessionModel = session_mdl
        self.transaction_mng: TransactionManager = TransactionManager(self.session_mdl)
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
            position.calculate_stop_loss_percent()
            position.calculate_take_profit_percent()

        return positions

    def run(self):
        logger.info(
            f"{self.__class__.__name__}: {self.session_mdl.id} - The Trader Run has started"
        )

        signal_param = cmn.SignalParamModel(
            trader_id=self.session_mdl.trader_id,
            symbol=self.session_mdl.symbol,
            interval=self.session_mdl.interval,
            strategy=self.session_mdl.strategy,
            from_buffer=True,
            closed_bars=True,
            # DEBUG type is required because there should be all signals
            types=[cmn.SignalType.DEBUG_SIGNAL],
        )

        signal_mdl = SignalFactory().get_signal(param=signal_param)

        self._process_signal(signal_mdl)
        self.save()

    def open_position(self, open_mdl: cmn.OrderOpenModel) -> cmn.OrderOpenModel:
        logger.info(f"{self.__class__.__name__}: The Trader is openning a position")
        if not self.data_mng.has_open_position():
            open_mdl.open_reason = cmn.OrderReason.MANUAL
            open_mdl.open_atr = self.data_mng.get_current_atr()

            position = self.data_mng.open_position(open_mdl)
            return position

    def close_position(self) -> bool:
        logger.info(f"{self.__class__.__name__}: The Trader is closing the positions")
        if self.data_mng.has_open_position():
            self.data_mng.close_position()
            self.save()
            return True

    def save(self):
        if self.balance_mng.get_change_indicator():
            self.transaction_mng.add_transaction(
                type=cmn.TransactionType.DB_UPDATE_BALANCE,
                data=self.balance_mng.get_balance_model().model_dump(),
            )
        self.balance_mng.save_balance()

    def _process_signal(self, signal_mdl: cmn.SignalModel):
        logger.info(
            f"{self.__class__.__name__}: The Trader is processing the signal - {signal_mdl.signal} for {signal_mdl.date_time}"
        )

        # Open position exists -> check if required it to close
        if self.data_mng.has_open_position():
            if self.data_mng.is_required_to_close_position(signal_mdl):
                self._decide_to_close_position(signal_mdl)
            # Recalculate Position should be done after decision about close the position because the robot are working with closed bars
            self._recalculate_position(signal_mdl)

        # Open position doesn't exist -> check if required to open a new position
        if not self.data_mng.has_open_position():
            if self.data_mng.is_required_to_open_position(signal_mdl):
                self._decide_to_open_position(signal_mdl)

    def _decide_to_open_position(self, signal_mdl: cmn.SignalModel):
        logger.info(
            f"{self.__class__.__name__}: The Trader is openning a position by the signal"
        )
        self.data_mng.open_position_by_signal(signal_mdl)

    def _decide_to_close_position(self, signal_mdl: cmn.SignalModel):
        logger.info(
            f"{self.__class__.__name__}: The Trader is closing the positions by the signal"
        )
        self.data_mng.close_position_by_signal(signal_mdl)

    def _recalculate_position(self, signal_mdl: cmn.SignalModel):
        if self.data_mng.has_open_position():
            self.data_mng.recalculate_position(signal_mdl)


class TraderManager(TraderBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

        self.balance_mng: BalanceManager = BalanceManager(
            BalanceHandler.get_balance_4_session(session_id=self.session_mdl.id)
        )

        self.api_mng: DataManagerBase = DataManagerBase.get_api_manager(trader_mng=self)
        self.data_mng: DataManagerBase = DataManagerBase.get_db_manager(trader_mng=self)

        # Make synchronize just for ACTIVE sessions
        self.data_mng.synchronize(manager=self.api_mng)

    def open_position(self, open_mdl: cmn.OrderOpenModel) -> cmn.OrderOpenModel:
        logger.info(f"{self.__class__.__name__}: The Trader is openning a position")

        if not self.data_mng.has_open_position():
            open_mdl.open_reason = cmn.OrderReason.MANUAL
            open_mdl.open_atr = self.data_mng.get_current_atr()

            api_mng_position = self.api_mng.open_position(open_mdl)
            data_mng_position = self.data_mng.open_position_by_ref(api_mng_position)
            return data_mng_position

    def close_position(self) -> bool:
        logger.info(f"{self.__class__.__name__}: The Trader is closing the positions")
        api_order_close_mdl = None

        if self.api_mng.has_open_position():
            api_order_close_mdl = self.api_mng.close_position()

        if self.data_mng.has_open_position():
            self.data_mng.close_position(order_close_mdl=api_order_close_mdl)
            self.save()

        return True

    def _recalculate_position(self, signal_mdl: cmn.SignalModel):
        if self.data_mng.has_open_position():
            trailing_stop_mdl = self.data_mng.recalculate_position(signal_mdl)
            self.api_mng.recalculate_position_by_ref(
                signal_mdl=signal_mdl, trailing_stop_mdl=trailing_stop_mdl
            )

    def _decide_to_open_position(self, signal_mdl: cmn.SignalModel):
        logger.info(
            f"{self.__class__.__name__}: The Trader is openning a position by the signal"
        )
        api_mng_position = self.api_mng.open_position_by_signal(signal_mdl)
        data_mng_position = self.data_mng.open_position_by_ref(api_mng_position)
        return data_mng_position

    def _decide_to_close_position(self, signal_mdl: cmn.SignalModel):
        logger.info(
            f"{self.__class__.__name__}: The Trader is closing the positions by the signal"
        )
        api_order_close_mdl = self.api_mng.close_position_by_signal(signal_mdl)
        self.data_mng.close_position(order_close_mdl=api_order_close_mdl)


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

        # Simulate Balance
        balance_mdl = cmn.BalanceModel(
            **{
                "session_id": self.session_mdl.id,
                "account_id": "1",
                "currency": "USD",
                "init_balance": 1000,
            }
        )

        self.balance_mng = BalanceManager(balance_mdl)

        self.data_mng: DataManagerBase = DataManagerBase.get_local_manager(
            trader_mng=self
        )

    def run(self, **kwargs):
        logger.info(f"{self.__class__.__name__}: History Simulation has started")

        strategy_param = cmn.StrategyParamModel(
            trader_id=self.session_mdl.trader_id,
            symbol=self.session_mdl.symbol,
            interval=self.session_mdl.interval,
            strategy=self.session_mdl.strategy,
            limit=kwargs.get(Const.SRV_LIMIT),
            from_buffer=True,
            closed_bars=True,
        )

        strategy_df = StrategyFactory.get_strategy_data(strategy_param)

        # Init signal instance
        for index, strategy_row in strategy_df.iterrows():
            signal_mdl = cmn.SignalModel(
                trader_id=strategy_param.trader_id,
                symbol=strategy_param.symbol,
                interval=strategy_param.interval,
                strategy=strategy_param.strategy,
                limit=strategy_param.limit,
                from_buffer=strategy_param.from_buffer,
                closed_bars=strategy_param.closed_bars,
                date_time=index,
                open=strategy_row["Open"],
                high=strategy_row["High"],
                low=strategy_row["Low"],
                close=strategy_row["Close"],
                volume=strategy_row["Volume"],
                atr=strategy_row[cmn.IndicatorType.ATR.value],
                signal=strategy_row[Const.PARAM_SIGNAL],
            )
            self._process_signal(signal_mdl)


class DataManagerBase:
    def __init__(self, trader_mng: TraderBase):
        self._trader_mng = trader_mng
        self._session_mdl: cmn.SessionModel = trader_mng.session_mdl

        self._exchange_handler: ExchangeHandler = ExchangeHandler(
            self._session_mdl.trader_id
        )

        self._symbol_handler = buffer_runtime_handler.get_symbol_handler(
            self._session_mdl.trader_id
        )

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
        logger.error(
            f"{self.__class__.__name__}: is_required_to_open_position() isn't implemented"
        )
        raise Exception(
            f"{self.__class__.__name__}: is_required_to_open_position() isn't implemented"
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
            f"{self.__class__.__name__}: Position {created_position_mdl.id} for {created_position_mdl.open_datetime} has been openned"
        )

        return created_position_mdl

    def open_position_by_signal(self, signal_mdl: cmn.SignalModel) -> cmn.OrderModel:
        logger.info(
            f"{self.__class__.__name__}: The Manager is openning a position by signal"
        )

        # Get Side type by Signal
        side_type = SideManager.get_side_type_by_signal(signal_type=signal_mdl.signal)

        # Prepafe model for open a position
        open_mdl = cmn.OrderOpenModel(
            side=side_type,
            open_price=signal_mdl.close,
            open_datetime=signal_mdl.date_time,
            open_reason=cmn.OrderReason.SIGNAL,
            open_atr=signal_mdl.atr,
        )

        # Open the position
        return self.open_position(open_mdl)

    def open_position_by_ref(self, position_mdl: cmn.OrderModel) -> cmn.OrderModel:
        logger.info(
            f"{self.__class__.__name__}: The Manager is openning reference Order ID {position_mdl.order_id}"
        )
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

    def close_position(
        self, order_close_mdl: cmn.OrderCloseModel = None
    ) -> cmn.OrderCloseModel:
        id = self._current_position.id

        # Generate current order close model for Manual Close
        if not order_close_mdl:
            close_price = self._get_current_price(price_type=cmn.PriceType.ASK)
            # There are open fee + close fee
            fee = self._get_fee()

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
                Const.DB_FEE: fee,
            }

            order_close_mdl = cmn.OrderCloseModel(**close_details_data)

        logger.info(
            f"{self.__class__.__name__}: Position close options - {order_close_mdl.model_dump()}"
        )

        order_close_mdl = self._prepare_close_position(order_close_mdl)
        if order_close_mdl:
            order_close_mdl = self._close_position(order_close_mdl)
            self._after_close_position(order_close_mdl=order_close_mdl)

            logger.info(
                f"{self.__class__.__name__}: Position {id} for {order_close_mdl.close_datetime} has been closed"
            )

        return order_close_mdl

    def close_position_by_signal(
        self, signal_mdl: cmn.SignalModel
    ) -> cmn.OrderCloseModel:
        logger.info(
            f"{self.__class__.__name__}: The manager are closing the position {self._current_position.id} by the signal"
        )
        order_close_mdl = self._side_mng.get_close_details_by_signal(
            position_mdl=self._current_position,
            signal_mdl=signal_mdl,
            fee=self._get_fee(),
        )

        return self.close_position(order_close_mdl)

    def recalculate_position(
        self, signal_mdl: cmn.SignalModel
    ) -> cmn.TrailingStopModel:
        logger.info(
            f"{self.__class__.__name__}: Recalculate the position (order_id: {self._current_position.order_id}) by the signal"
        )

        # Calculate Trailing Stop
        if self._session_mdl.is_trailing_stop:
            trailing_stop_mdl = self._side_mng.get_trailing_stop_loss(
                position_mdl=self._current_position, signal_mdl=signal_mdl
            )
            if trailing_stop_mdl:
                logger.info(
                    f"{self.__class__.__name__}: Set Stop Loss = {trailing_stop_mdl.stop_loss} and Take Profit = {trailing_stop_mdl.take_profit} for {signal_mdl.date_time}"
                )
                return trailing_stop_mdl

        return None

    def recalculate_position_by_ref(
        self, signal_mdl: cmn.SignalModel, trailing_stop_mdl: cmn.TrailingStopModel
    ) -> cmn.TrailingStopModel:
        pass

    def get_current_position(self) -> cmn.OrderModel:
        return self._current_position

    def get_positions(self) -> list:
        return None

    def get_open_positions(self) -> list:
        return None

    def get_position(
        self, order_id: str = None, position_id: str = None
    ) -> cmn.OrderModel:
        return None

    def has_open_position(self) -> bool:
        return True if self._current_position else False

    def synchronize(self, manager):
        self._trader_mng.save()

    def _init_open_positions(self):
        current_postion = None
        self._open_positions = self.get_open_positions()
        if self._open_positions:
            current_postion = self._open_positions[0]

        self._set_current_postion(current_postion)

    def _get_open_position_template(self, open_mdl: cmn.OrderOpenModel) -> dict:
        open_price = self._get_open_price(open_mdl.open_price)

        position_template = {
            Const.DB_ORDER_ID: "000001",
            Const.DB_SESSION_ID: self._session_mdl.id,
            Const.DB_TYPE: open_mdl.type,
            Const.DB_SIDE: self._side_mng.get_side_type(),
            Const.DB_STATUS: cmn.OrderStatus.opened,
            Const.DB_SYMBOL: self._session_mdl.symbol,
            Const.DB_QUANTITY: self._get_quantity(open_price),
            Const.DB_STOP_LOSS: self._side_mng.get_stop_loss(
                price=open_price, atr=open_mdl.open_atr
            ),
            Const.DB_TAKE_PROFIT: self._side_mng.get_take_profit(
                price=open_price, atr=open_mdl.open_atr
            ),
            Const.DB_OPEN_PRICE: open_price,
            Const.DB_OPEN_DATETIME: open_mdl.open_datetime,
            Const.DB_OPEN_REASON: open_mdl.open_reason,
            Const.DB_HIGH_PRICE: open_price,
            Const.DB_LOW_PRICE: open_price,
            Const.DB_FEE: self._get_fee(),
        }

        return position_template

    def _prepare_open_position(self, open_mdl: cmn.OrderOpenModel) -> cmn.OrderModel:
        # Set Side manager by Side Type
        self._set_side_mng(side_type=open_mdl.side)

    def _open_position(self, position_mdl: cmn.OrderModel):
        logger.error(f"{self.__class__.__name__}: _open_position() isn't implemented")
        raise Exception(
            f"{self.__class__.__name__}: _open_position() isn't implemented"
        )

    def _after_open_position(self, position_mdl: cmn.OrderModel):
        # Set the created leverage as a current position
        self._set_current_postion(position_mdl)

        return position_mdl

    def _prepare_close_position(
        self, order_close_mdl: cmn.OrderCloseModel
    ) -> cmn.OrderCloseModel:
        if order_close_mdl:
            order_close_mdl.fee += self._current_position.fee
            order_close_mdl.total_profit += order_close_mdl.fee

            self._current_position.status = order_close_mdl.status
            self._current_position.close_datetime = order_close_mdl.close_datetime
            self._current_position.close_price = order_close_mdl.close_price
            self._current_position.close_reason = order_close_mdl.close_reason
            self._current_position.fee = order_close_mdl.fee
            self._current_position.total_profit = order_close_mdl.total_profit

            return order_close_mdl
        else:
            return None

    def _close_position(self, order_close_mdl: cmn.OrderCloseModel) -> bool:
        logger.error(f"{self.__class__.__name__}: _close_position() isn't implemented")
        raise Exception(
            f"{self.__class__.__name__}: _close_position() isn't implemented"
        )

    def _update_position(self, trailing_stop_mdl: cmn.TrailingStopModel) -> bool:
        logger.error(f"{self.__class__.__name__}: _update_position() isn't implemented")
        raise Exception(
            f"{self.__class__.__name__}: _update_position() isn't implemented"
        )

    def _after_close_position(self, order_close_mdl: cmn.OrderCloseModel):
        # Recalulate balance after close the position
        self._recalculate_balance()

        # Set the current position = None
        self._set_current_postion()

    def _set_current_postion(self, position_mdl: cmn.OrderModel = None):
        if position_mdl:
            self._current_position = position_mdl
            logger.info(
                f"{self.__class__.__name__}: Set the position {position_mdl.id} (Position ID: {position_mdl.position_id}) as openned"
            )
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
        symbol_quote_precision = self._symbol_handler.get_symbol(
            self._session_mdl.symbol
        ).quote_precision
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
        symbol_fee = self._symbol_handler.get_symbol_fee(self._session_mdl.symbol)
        fee = total_balance * symbol_fee / 100
        return -fee

    def _get_current_price(
        self, price_type: cmn.PriceType = cmn.PriceType.BID
    ) -> float:
        # Get current price from exchnage handler
        param = cmn.HistoryDataParamModel(
            interval=self._session_mdl.interval,
            symbol=self._session_mdl.symbol,
            limit=1,
        )
        history_data = self._exchange_handler.get_history_data(
            param, price_type=price_type
        )
        candle_bar = history_data.data.tail(1)

        price = candle_bar["Close"].values[0]

        return price

    def get_current_atr(self):
        if self._session_mdl.is_trailing_stop:
            indicator = Indicator_ATR(length=14)

            param = cmn.IndicatorParamModel(
                trader_id=self._session_mdl.trader_id,
                symbol=self._session_mdl.symbol,
                interval=self._session_mdl.interval,
                closed_bars=True,
            )
            atr_df = indicator.get_indicator(param)

            atr_value = atr_df.tail(1)[cmn.IndicatorType.ATR.value].values[0]

            return atr_value
        else:
            return None

    def _get_current_balance(self, fee: float = 0) -> float:
        # Take Total Balance from Balance Model and take into account Fee if it's required
        return self._trader_mng.balance_mng.get_total_balance() + fee

    def _recalculate_balance(self):
        if self._current_position.status == cmn.OrderStatus.closed:
            self._trader_mng.balance_mng.add_fee(self._current_position.fee)
            self._trader_mng.balance_mng.recalculate_balance(
                self._current_position.total_profit
            )


class OrderManagerBase(DataManagerBase):
    def is_required_to_open_position(self, signal_mdl: cmn.SignalModel) -> bool:
        return signal_mdl.signal == cmn.SignalType.STRONG_BUY


class OrderApiManager(OrderManagerBase):
    pass


class OrderDatabaseManager(OrderManagerBase):
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
        position_template = super()._get_open_position_template(open_mdl)
        position_template[Const.DB_POSITION_ID] = "000002"
        position_template[
            Const.DB_ACCOUNT_ID
        ] = self._trader_mng.balance_mng.get_account_id()
        position_template[Const.DB_LEVERAGE] = self._session_mdl.leverage
        return position_template

    def _prepare_open_position(self, open_mdl: cmn.OrderOpenModel) -> cmn.LeverageModel:
        super()._prepare_open_position(open_mdl)
        position_data = self._get_open_position_template(open_mdl)

        logger.info(
            f"{self.__class__.__name__}: An position template for openning - {position_data}"
        )

        return cmn.LeverageModel(**position_data)

    def _get_current_balance(self, fee: float = 0) -> float:
        return super()._get_current_balance(fee) * self._session_mdl.leverage


class LeverageApiManager(LeverageManagerBase):
    def get_position(self, order_id: str = None, position_id: str = None) -> OrderModel:
        position_mdl = self._exchange_handler.get_open_position(
            symbol=self._session_mdl.symbol,
            order_id=order_id,
            position_id=position_id,
        )
        if position_mdl:
            position_mdl.session_id = self._session_mdl.id
            position_mdl.leverage = self._session_mdl.leverage

        return position_mdl

    def open_position(self, open_mdl: cmn.LeverageModel) -> cmn.LeverageModel:
        # Prepate model for opennig
        position_mdl = self._prepare_open_position(open_mdl)

        # Persit an openning position
        created_position_mdl = self._open_position(position_mdl)

        logger.info(
            f"{self.__class__.__name__}: Position ID {created_position_mdl.position_id} for {created_position_mdl.open_datetime} has been opened"
        )

        return created_position_mdl

    def close_position_by_signal(
        self, signal_mdl: cmn.SignalModel
    ) -> cmn.OrderCloseModel:
        order_close_mdl = self.close_position()
        order_close_mdl.close_reason = cmn.OrderReason.SIGNAL
        return order_close_mdl

    def close_position(self) -> cmn.OrderCloseModel:
        order_close_mdl = self._exchange_handler.close_leverage(
            symbol=self._current_position.symbol,
            order_id=self._current_position.order_id,
            position_id=self._current_position.position_id,
        )

        self._trader_mng.transaction_mng.add_transaction(
            order_id=self._current_position.order_id,
            type=cmn.TransactionType.API_CLOSE_POSITION,
            date_time=order_close_mdl.close_datetime,
            data=order_close_mdl.model_dump(),
        )

        # Set the current position = None
        self._set_current_postion()

        return order_close_mdl

    def recalculate_position_by_ref(
        self, signal_mdl: cmn.SignalModel, trailing_stop_mdl: TrailingStopModel = None
    ) -> cmn.TrailingStopModel:
        if trailing_stop_mdl:
            logger.info(
                f"{self.__class__.__name__}: Recalculate the position (order_id: {self._current_position.order_id}) by the reference"
            )

            self._exchange_handler.update_trading_stop(
                symbol=self._session_mdl.symbol,
                trading_stop=trailing_stop_mdl,
                order_id=self._current_position.order_id,
                position_id=self._current_position.position_id,
            )

            self._trader_mng.transaction_mng.add_transaction(
                order_id=self._current_position.order_id,
                type=cmn.TransactionType.API_UPDATE_POSITION,
                date_time=signal_mdl.date_time,
                data=trailing_stop_mdl.model_dump(),
            )

        return trailing_stop_mdl

    def _init_open_positions(self):
        pass

    def _open_position(self, position_mdl: cmn.LeverageModel) -> cmn.LeverageModel:
        logger.info(
            f"{self.__class__.__name__}: An position template for openning via API - {position_mdl.model_dump()}"
        )
        created_position_mdl = self._exchange_handler.create_leverage(position_mdl)

        self._trader_mng.transaction_mng.add_transaction(
            order_id=created_position_mdl.order_id,
            type=cmn.TransactionType.API_CREATE_POSITION,
            date_time=created_position_mdl.open_datetime,
            data=created_position_mdl.model_dump(),
        )

        return created_position_mdl


class LeverageDatabaseManager(LeverageManagerBase):
    def get_positions(self) -> list[cmn.LeverageModel]:
        position: cmn.LeverageModel = None
        positions = LeverageHandler.get_leverages(session_id=self._session_mdl.id)

        if self._current_position:
            current_price = self._get_current_price(cmn.PriceType.ASK)
            fee = self._current_position.fee + self._get_fee()

            for position in positions:
                if position.status == cmn.OrderStatus.opened:
                    position.close_price = current_price
                    position.close_datetime = datetime.now()
                    position.total_profit = self._side_mng.get_total_profit(
                        quantity=self._current_position.quantity,
                        open_price=self._current_position.open_price,
                        close_price=current_price,
                    )
                    position.fee = fee

        return positions

    def get_open_positions(self) -> dict:
        return LeverageHandler.get_leverages(
            session_id=self._session_mdl.id, status=cmn.OrderStatus.opened
        )

    def synchronize(self, manager: LeverageManagerBase):
        # manager - api data manager works with the Trader
        if self._current_position:
            api_position_mdl = manager.get_position(
                order_id=self._current_position.order_id,
                position_id=self._current_position.position_id,
            )

            manager._set_current_postion(api_position_mdl)

            # Open position exists in the Database
            if not api_position_mdl:
                # Open position doens't exists in the Exhange Trader -> cancel the position in the Database
                logger.info(
                    f"{self.__class__.__name__}: Close the leverage {self._current_position.id} by the ref position id {self._current_position.position_id}"
                )
                api_order_closed_mdl = self._exchange_handler.get_close_position(
                    symbol=self._current_position.symbol,
                    order_id=self._current_position.order_id,
                    position_id=self._current_position.position_id,
                )

                self.close_position(api_order_closed_mdl)

                super().synchronize(manager)

    def recalculate_position(
        self, signal_mdl: cmn.SignalModel
    ) -> cmn.TrailingStopModel:
        trailing_stop_mdl = super().recalculate_position(signal_mdl)

        # Highest Order price
        self._current_position.calculate_high_price(signal_mdl.high)

        # Lowest Order price
        self._current_position.calculate_low_price(signal_mdl.low)

        order_analytic_mdl = cmn.OrderAnalyticModel(
            **self._current_position.to_mongodb_doc()
        )

        query = {**order_analytic_mdl.to_mongodb_doc()}

        if trailing_stop_mdl:
            self._current_position.stop_loss = trailing_stop_mdl.stop_loss
            self._current_position.take_profit = trailing_stop_mdl.take_profit

            query.update(trailing_stop_mdl.to_mongodb_doc())

            self._trader_mng.transaction_mng.add_transaction(
                local_order_id=self._current_position.id,
                type=cmn.TransactionType.DB_UPDATE_POSITION,
                date_time=signal_mdl.date_time,
                data=trailing_stop_mdl.model_dump(),
            )

        if not self._update_position(query):
            raise Exception(
                f"DataManagerBase: _update_position() - Error during update position {self._current_position.id}"
            )

        return trailing_stop_mdl

    def _open_position(self, position_mdl: cmn.LeverageModel):
        logger.info(
            f"{self.__class__.__name__}: An position template for openning in the DB - {position_mdl.model_dump()}"
        )
        created_position_mdl = LeverageHandler.create_leverage(position_mdl)
        created_position_mdl.calculate_stop_loss_percent()
        created_position_mdl.calculate_take_profit_percent()

        self._trader_mng.transaction_mng.add_transaction(
            local_order_id=created_position_mdl.id,
            type=cmn.TransactionType.DB_CREATE_POSITION,
            date_time=created_position_mdl.open_datetime,
            data=created_position_mdl.model_dump(),
        )

        return created_position_mdl

    def _update_position(self, query: dict) -> bool:
        logger.info(
            f"{self.__class__.__name__}: Update the leverage {self._current_position.id} in the DB"
        )
        result = LeverageHandler.update_leverage(
            id=self._current_position.id, query=query
        )

        return result

    def _close_position(
        self, order_close_mdl: cmn.OrderCloseModel
    ) -> cmn.OrderCloseModel:
        logger.info(
            f"{self.__class__.__name__}: Update/Close the leverage {self._current_position.id} in the DB"
        )
        LeverageHandler.update_leverage(
            id=self._current_position.id, query=order_close_mdl.to_mongodb_doc()
        )

        self._trader_mng.transaction_mng.add_transaction(
            local_order_id=self._current_position.id,
            type=cmn.TransactionType.DB_CLOSE_POSITION,
            date_time=order_close_mdl.close_datetime,
            data=order_close_mdl.model_dump(),
        )

        return order_close_mdl

    def _close_position_by_ref(self) -> bool:
        logger.info(
            f"{self.__class__.__name__}: Close the leverage {self._current_position.id} by the ref position id {self._current_position.position_id}"
        )
        api_order_closed_mdl = self._exchange_handler.get_close_leverages(
            symbol=self._current_position.symbol,
            order_id=self._current_position.order_id,
            position_id=self._current_position.position_id,
            limit=10,
        )

        return self.close_position(api_order_closed_mdl)


class LeverageLocalDataManager(LeverageManagerBase):
    def __init__(self, session_mdl: cmn.SessionModel):
        super().__init__(session_mdl)

        self._local_positions: dict(cmn.LeverageModel) = {}

    def get_positions(self) -> list[cmn.LeverageModel]:
        return [pos_mdl for pos_mdl in self._local_positions.values()]

    def recalculate_position(
        self, signal_mdl: cmn.SignalModel
    ) -> cmn.TrailingStopModel:
        trailing_stop_mdl = super().recalculate_position(signal_mdl)

        # Highest Order price
        self._current_position.calculate_high_price(signal_mdl.high)

        # Lowest Order price
        self._current_position.calculate_low_price(signal_mdl.low)

        if trailing_stop_mdl:
            self._current_position.stop_loss = trailing_stop_mdl.stop_loss
            self._current_position.take_profit = trailing_stop_mdl.take_profit

            self._trader_mng.transaction_mng.add_transaction(
                local_order_id=self._current_position.id,
                type=cmn.TransactionType.DB_UPDATE_POSITION,
                date_time=signal_mdl.date_time,
                data=trailing_stop_mdl.model_dump(),
                save=False,
            )

        return trailing_stop_mdl

    def _open_position(self, position_mdl: cmn.LeverageModel):
        # Simulate creation of the order
        position_mdl.id = str(ObjectId())
        position_mdl.calculate_stop_loss_percent()
        position_mdl.calculate_take_profit_percent()

        self._trader_mng.transaction_mng.add_transaction(
            local_order_id=position_mdl.id,
            type=cmn.TransactionType.DB_CREATE_POSITION,
            date_time=position_mdl.open_datetime,
            data=position_mdl.model_dump(),
            save=False,
        )

        return position_mdl

    def _after_open_position(self, position_mdl: cmn.LeverageModel):
        super()._after_open_position(position_mdl=position_mdl)

        # Add current postiojn to the local postion storega
        self._local_positions[position_mdl.id] = position_mdl
        return position_mdl

    def _close_position(
        self, order_close_mdl: cmn.OrderCloseModel
    ) -> cmn.OrderCloseModel:
        current_position: cmn.LeverageModel = self._local_positions[
            self._current_position.id
        ]

        current_position.status = order_close_mdl.status
        current_position.close_datetime = order_close_mdl.close_datetime
        current_position.close_price = order_close_mdl.close_price
        current_position.close_reason = order_close_mdl.close_reason
        current_position.total_profit = order_close_mdl.total_profit
        current_position.fee += order_close_mdl.fee

        self._trader_mng.transaction_mng.add_transaction(
            local_order_id=current_position.id,
            type=cmn.TransactionType.DB_CLOSE_POSITION,
            date_time=current_position.close_datetime,
            data=order_close_mdl.model_dump(),
            save=False,
        )

        return order_close_mdl

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
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel, fee: float = 0
    ) -> cmn.OrderCloseModel:
        raise Exception(
            "Robot: SideManager - get_close_details_by_signal() isn't implemented"
        )

    def get_side_type(self) -> cmn.OrderSideType:
        raise Exception("Robot: SideManager - get_side_type() isn't implemented")

    def get_stop_loss(self, price: float, atr: float = None) -> float:
        # Static Stop Loss Value
        stop_loss_value = (price * self._session_mdl.stop_loss_rate) / 100

        if self._session_mdl.is_trailing_stop == True and atr:
            stop_loss_value_atr = self._get_stop_loss_atr_coeff() * atr

            if stop_loss_value == 0:
                stop_loss_value = stop_loss_value_atr

        return stop_loss_value

    def get_trailing_stop_loss(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> cmn.TrailingStopModel:
        pass

    def get_take_profit(self, price: float, atr: float = None) -> float:
        # Static Take Pofit Value
        take_profit_value = (price * self._session_mdl.take_profit_rate) / 100

        if self._session_mdl.is_trailing_stop == True and atr:
            take_profit_value_atr = self._get_take_profit_atr_coeff() * atr

            if take_profit_value == 0:
                take_profit_value = take_profit_value_atr

        return take_profit_value

    def get_total_profit(
        self, quantity: float, open_price: float, close_price: float
    ) -> float:
        pass

    def _get_stop_loss_atr_coeff(self) -> float:
        return 2

    def _get_take_profit_atr_coeff(self) -> float:
        return 4


# Short Positions
class SellManager(SideManager):
    def get_close_details_by_signal(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel, fee: float = 0
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
        elif signal_mdl.signal in [
            cmn.SignalType.STRONG_BUY,
            cmn.SignalType.BUY,
        ]:
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
            Const.DB_FEE: fee,
        }

        return cmn.OrderCloseModel(**close_details_data)

    def get_side_type(self):
        return cmn.OrderSideType.sell

    def get_stop_loss(self, price: float, atr: float = None) -> float:
        stop_loss_value = super().get_stop_loss(price=price, atr=atr)
        if stop_loss_value > 0:
            return price + stop_loss_value
        else:
            return 0

    def get_trailing_stop_loss(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> cmn.TrailingStopModel:
        if self._session_mdl.is_trailing_stop == True and signal_mdl.atr:
            # Current Stop Loss and Take Profit
            take_profit = position_mdl.take_profit
            stop_loss = position_mdl.stop_loss

            # Take Profit calculation is performed only when Static Take Profit = 0
            if self._session_mdl.take_profit_rate == 0:
                new_take_profit = (
                    signal_mdl.close
                    - self._get_take_profit_atr_coeff() * signal_mdl.atr
                )

                if take_profit > new_take_profit:
                    take_profit = new_take_profit

            # Stop Loss calculation
            new_stop_loss = (
                signal_mdl.close + self._get_stop_loss_atr_coeff() * signal_mdl.atr
            )

            if stop_loss > new_stop_loss:
                stop_loss = new_stop_loss

            if (
                take_profit != position_mdl.take_profit
                or stop_loss != position_mdl.stop_loss
            ):
                trailing_stop_mdl = cmn.TrailingStopModel(
                    stop_loss=stop_loss, take_profit=take_profit
                )
                trailing_stop_mdl.calculate_stop_loss_percent(
                    open_price=position_mdl.open_price, side=position_mdl.side
                )
                trailing_stop_mdl.calculate_take_profit_percent(
                    open_price=position_mdl.open_price, side=position_mdl.side
                )

                return trailing_stop_mdl
            else:
                return None

    def get_take_profit(self, price: float, atr: float = None) -> float:
        take_profit_value = super().get_take_profit(price=price, atr=atr)

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
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel, fee: float = 0
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
        elif signal_mdl.signal in [
            cmn.SignalType.STRONG_SELL,
            cmn.SignalType.SELL,
        ]:
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
            Const.DB_FEE: fee,
        }

        return cmn.OrderCloseModel(**close_details_data)

    def get_side_type(self):
        return cmn.OrderSideType.buy

    def get_stop_loss(self, price: float, atr: float = None) -> float:
        stop_loss_value = super().get_stop_loss(price=price, atr=atr)
        if stop_loss_value > 0:
            return price - stop_loss_value
        else:
            return 0

    def get_trailing_stop_loss(
        self, position_mdl: cmn.OrderModel, signal_mdl: cmn.SignalModel
    ) -> cmn.TrailingStopModel:
        if self._session_mdl.is_trailing_stop == True and signal_mdl.atr:
            # Current Stop Loss and Take Profit
            take_profit = position_mdl.take_profit
            stop_loss = position_mdl.stop_loss

            # Take Profit calculation is performed only when Static Take Profit = 0
            if self._session_mdl.take_profit_rate == 0:
                new_take_profit = (
                    signal_mdl.close
                    + self._get_take_profit_atr_coeff() * signal_mdl.atr
                )

                if take_profit > new_take_profit:
                    take_profit = new_take_profit

            # Stop Loss calculation
            new_stop_loss = (
                signal_mdl.close - self._get_stop_loss_atr_coeff() * signal_mdl.atr
            )

            if stop_loss < new_stop_loss:
                stop_loss = new_stop_loss

            if (
                take_profit != position_mdl.take_profit
                or stop_loss != position_mdl.stop_loss
            ):
                trailing_stop_mdl = cmn.TrailingStopModel(
                    stop_loss=stop_loss, take_profit=take_profit
                )
                trailing_stop_mdl.calculate_stop_loss_percent(
                    open_price=position_mdl.open_price, side=position_mdl.side
                )
                trailing_stop_mdl.calculate_take_profit_percent(
                    open_price=position_mdl.open_price, side=position_mdl.side
                )

                return trailing_stop_mdl
            else:
                return None

    def get_take_profit(self, price: float, atr: float = None) -> float:
        take_profit_value = super().get_take_profit(price=price, atr=atr)
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
        logger.info(
            f"{self.__class__.__name__}: Robot has started for the session {session_id}"
        )
        session_mdl = self._get_session_mdl(session_id)
        self._run(session_mdl)

    def run_job(self, interval: str) -> dict:
        errors = {}

        logger.info(
            f"{self.__class__.__name__}: Robot has started for the interval {interval}"
        )

        active_sessions = SessionHandler.get_sessions(
            interval=interval, status=cmn.SessionStatus.active
        )

        for session_mdl in active_sessions:
            try:
                self._run(session_mdl)
            except Exception as error:
                error_message = f"Error during session {session_mdl.id} run - {error}"
                logger.error(error_message)
                errors[session_mdl.id] = error_message

        return errors

    def run_history_simulation(self):
        logger.info(
            f"{self.__class__.__name__}: Robot has started a History Simulation"
        )

    def _get_session_mdl(self, session_id) -> cmn.SessionModel:
        return SessionHandler.get_session(session_id)

    def _run(self, session_mdl: cmn.SessionModel):
        session_manager = SessionManager(session_mdl)
        session_manager.run()
