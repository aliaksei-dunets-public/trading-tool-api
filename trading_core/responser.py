import json
import bson.json_util as json_util
import pandas as pd
from flask import jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job
from dotenv import load_dotenv
import requests
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


from .constants import Const
from .core import config, logger, runtime_buffer, Symbol, Signal, SimulateOptions
from .model import model, Symbols, ParamSimulationList, ParamSymbolIntervalLimit
from .strategy import StrategyFactory, SignalFactory
from .simulation import Executor
from .mongodb import MongoJobs, MongoAlerts, MongoOrders, MongoSimulations
from .handler import ExchangeHandler, SymbolHandler
from .trend import TrendCCI

from trading_core.common import (
    BaseModel,
    UserModel,
    TraderModel,
    SessionModel,
    SessionType,
    BalanceModel,
    OrderModel,
    LeverageModel,
    TransactionModel,
    SessionStatus,
    OrderOpenModel,
)
from trading_core.handler import (
    UserHandler,
    TraderHandler,
    SessionHandler,
    BalanceHandler,
    OrderHandler,
    LeverageHandler,
    TransactionHandler,
    buffer_runtime_handler,
)
from trading_core.robot import Robot, SessionManager

load_dotenv()


def decorator_json(func) -> str:
    def wrapper(*args, **kwargs):
        try:
            value = func(*args, **kwargs)

            if isinstance(value, pd.DataFrame):
                return value.to_json(orient="table", index=True), 200
            if isinstance(value, list) and all(
                isinstance(item, BaseModel) for item in value
            ):
                return jsonify([item.model_dump() for item in value]), 200
            elif isinstance(value, BaseModel):
                return jsonify(value.model_dump()), 200
            else:
                return json_util.dumps(value), 200

        except Exception as error:
            logger.error(f"{func} - {error}")
            return jsonify({"error": f"{error}"}), 400

    return wrapper


def job_func_initialise_runtime_data():
    if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        logger.info(f"JOB: {Const.JOB_TYPE_INIT} - Refresh runtime buffer")

    runtime_buffer.clearSymbolsBuffer()
    runtime_buffer.clearTimeframeBuffer()
    runtime_buffer.clearHistoryDataBuffer()
    runtime_buffer.clear_signal_buffer()

    model.get_handler().getSymbols(from_buffer=False)

    buffer_runtime_handler.clear_buffer()
    buffer_runtime_handler.get_symbol_handler().get_symbols()


def job_func_send_bot_notification(interval):
    if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        logger.info(f"JOB: {Const.JOB_TYPE_BOT} is triggered for interval - {interval}")

    responser = ResponserBot()
    notificator = NotificationBot()

    alerts_db = MongoAlerts().get_alerts(
        alert_type=Const.ALERT_TYPE_BOT, interval=interval
    )

    alert_messages = responser.get_signals_for_alerts(alerts_db)
    notificator.send(alert_messages)


def job_func_send_email_notification(interval):
    if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        logger.info(
            f"JOB: {Const.JOB_TYPE_EMAIL} is triggered for interval - {interval}"
        )

    messages = ResponserEmail().get_signals(
        symbols=[],
        intervals=[interval],
        strategies=[],
        signals_config=[],
        closed_bars=True,
    )

    NotificationEmail().send(messages)


def job_func_trading_robot(interval):
    if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        logger.info(
            f"JOB: {Const.JOB_TYPE_ROBOT} is triggered for interval - {interval}"
        )

    Robot().run_job(interval)


class MessageBase:
    def __init__(self, channel_id: str, message_text: str) -> None:
        self._channel_id = channel_id
        self._message_text = message_text

    def get_channel_id(self) -> str:
        return self._channel_id

    def get_message_text(self) -> str:
        return self._message_text

    def set_message_text(self, text: str) -> None:
        self._message_text = text

    def add_message_text(self, text: str) -> None:
        self._message_text += text


class MessageEmail(MessageBase):
    def __init__(self, channel_id: str, subject: str, message_text: str) -> None:
        MessageBase.__init__(self, channel_id=channel_id, message_text=message_text)
        self._subject = subject

    def get_subject(self) -> str:
        return self._subject


class Messages:
    def __init__(self):
        self._messages = {}

    def check_message(self, channel_id: str) -> bool:
        if channel_id in self._messages:
            return True
        else:
            return False

    def get_message(self, channel_id: str) -> MessageBase:
        if self.check_message(channel_id):
            return self._messages[channel_id]
        else:
            None

    def get_messages(self) -> dict:
        return self._messages

    def add_message_text(self, channel_id: str, text: str) -> MessageBase:
        message = self.get_message(channel_id)
        if message:
            message.add_message_text(text)
        else:
            message = self.create_message(channel_id=channel_id, text=text)

        return message

    def set_message_text(self, channel_id: str, text: str) -> MessageBase:
        message = self.get_message(channel_id)
        if message:
            message.set_message_text(text)
        else:
            message = self.create_message(channel_id=channel_id, text=text)

        return message

    def add_message(self, message: MessageBase) -> None:
        self._messages[message.get_channel_id()] = message

    def create_message(self, channel_id: str, text: str) -> MessageBase:
        message = MessageBase(channel_id=channel_id, message_text=text)
        self.add_message(message)
        return message


class ResponserBase:
    def get_param_bool(self, param_value):
        return bool(param_value.lower() == "true")

    def get_symbol(self, code: str) -> Symbol:
        return Symbols(from_buffer=True).get_symbol(code)

    def get_symbol_list(**kwargs) -> list[Symbol]:
        symbol_handler = buffer_runtime_handler.get_symbol_handler()

        return symbol_handler.get_symbol_list(**kwargs)

    def get_intervals(self, importances: list = None) -> list:
        return model.get_intervals_config(importances)

    def get_indicators(self) -> list:
        return model.get_indicators_config()

    def get_strategies(self) -> list:
        return model.get_strategies()

    def get_history_data(
        self,
        symbol: str,
        interval: str,
        limit: int,
        from_buffer: bool,
        closed_bars: bool,
    ) -> pd.DataFrame:
        history_data_inst = model.get_handler().getHistoryData(
            symbol=symbol,
            interval=interval,
            limit=limit,
            from_buffer=from_buffer,
            closed_bars=closed_bars,
        )
        return history_data_inst.getDataFrame()

    def get_strategy_data(
        self,
        code: str,
        symbol: str,
        interval: str,
        limit: int,
        from_buffer: bool,
        closed_bars: bool,
    ) -> pd.DataFrame:
        strategy_inst = StrategyFactory(code)
        return strategy_inst.get_strategy_data(
            symbol=symbol,
            interval=interval,
            limit=limit,
            from_buffer=from_buffer,
            closed_bars=closed_bars,
        )

    def get_signals(
        self,
        symbols: list,
        intervals: list,
        strategies: list,
        signals_config: list,
        closed_bars: bool,
    ) -> list[Signal]:
        return SignalFactory().get_signals(
            symbols=symbols,
            intervals=intervals,
            strategies=strategies,
            signals_config=signals_config,
            closed_bars=closed_bars,
        )

    def create_job(self, job_type: str, interval: str) -> str:
        return JobScheduler().create_job(job_type=job_type, interval=interval)

    def remove_job(self, job_id: str) -> bool:
        return JobScheduler().remove_job(job_id)

    def get_jobs(self) -> list:
        return JobScheduler().get_jobs()

    def activate_job(self, job_id) -> bool:
        return JobScheduler().activate_job(job_id)

    def deactivate_job(self, job_id) -> bool:
        return JobScheduler().deactivate_job(job_id)

    def create_alert(
        self,
        alert_type: str,
        channel_id: str,
        symbol: str,
        interval: str,
        strategies: list,
        signals: list,
        comment: str,
    ) -> str:
        return MongoAlerts().create_alert(
            alert_type=alert_type,
            channel_id=channel_id,
            symbol=symbol,
            interval=interval,
            strategies=strategies,
            signals=signals,
            comment=comment,
        )

    def update_alert(
        self, id: str, interval: str, strategies: list, signals: list, comment: str
    ) -> bool:
        return MongoAlerts().update_alert(
            id=id,
            interval=interval,
            strategies=strategies,
            signals=signals,
            comment=comment,
        )

    def remove_alert(self, id: str) -> bool:
        return MongoAlerts().delete_one(id)

    def get_alerts(self, alert_type: str, symbol: str, interval: str) -> list:
        return MongoAlerts().get_alerts(
            alert_type=alert_type, symbol=symbol, interval=interval
        )

    def create_order(
        self,
        order_type: str,
        open_date_time: str,
        symbol: str,
        interval: str,
        price: float,
        quantity: float,
        strategies: list,
    ) -> str:
        return MongoOrders().create_order(
            order_type=order_type,
            open_date_time=open_date_time,
            symbol=symbol,
            interval=interval,
            price=price,
            quantity=quantity,
            strategies=strategies,
        )

    def remove_order(self, id: str) -> bool:
        return MongoOrders().delete_one(id)

    def get_orders(self, symbol: str, interval: str) -> list:
        return MongoOrders().get_orders(symbol=symbol, interval=interval)

    def get_simulations(self, symbols: list, intervals: list, strategies: list) -> list:
        return MongoSimulations().get_simulations(
            symbols=symbols, intervals=intervals, strategies=strategies
        )

    def get_simulate(self, params: ParamSimulationList) -> list:
        simulations = []
        executor = Executor()
        simulators = executor.simulate_many(params=params)

        for simulator in simulators:
            simulation = simulator.get_simulation()
            simulations.append(simulation)

        return simulations

    def get_user(self, id: str):
        return UserHandler.get_user_by_id(id)

    def get_users(self, search: str):
        return UserHandler.get_users(search)

    def create_user(self, user_model: UserModel):
        return UserHandler.create_user(user_model)


class ResponserWeb(ResponserBase):
    @decorator_json
    def get_symbol(self, code: str) -> json:
        symbol = super().get_symbol(code)
        if symbol:
            return symbol
        else:
            raise Exception(f"Symbol: {code} can't be detected")

    @decorator_json
    def get_symbol_list(*args, **kwargs) -> json:
        symbol_handler = buffer_runtime_handler.get_symbol_handler(
            trader_id=kwargs.get(Const.DB_TRADER_ID)
        )
        return symbol_handler.get_symbol_list(**kwargs)

    @decorator_json
    def get_intervals(self, importances: list = None) -> json:
        return super().get_intervals(importances=importances)

    @decorator_json
    def get_indicators(self) -> json:
        return super().get_indicators()

    @decorator_json
    def get_strategies(self) -> json:
        return super().get_strategies()

    @decorator_json
    def get_history_data(
        self,
        symbol: str,
        interval: str,
        limit: int,
        from_buffer: bool,
        closed_bars: bool,
    ) -> json:
        return super().get_history_data(
            symbol=symbol,
            interval=interval,
            limit=limit,
            from_buffer=from_buffer,
            closed_bars=closed_bars,
        )

    @decorator_json
    def get_strategy_data(
        self,
        code: str,
        symbol: str,
        interval: str,
        limit: int,
        from_buffer: bool,
        closed_bars: bool,
    ) -> json:
        return super().get_strategy_data(
            code=code,
            symbol=symbol,
            interval=interval,
            limit=limit,
            from_buffer=from_buffer,
            closed_bars=closed_bars,
        )

    @decorator_json
    def get_signals(
        self,
        symbols: list,
        intervals: list,
        strategies: list,
        signals_config: list,
        closed_bars: bool,
    ) -> json:
        signals = []
        signals_list = super().get_signals(
            symbols=symbols,
            intervals=intervals,
            strategies=strategies,
            signals_config=signals_config,
            closed_bars=closed_bars,
        )

        for signal_inst in signals_list:
            signals.append(signal_inst.get_signal_dict())

        return signals

    @decorator_json
    def create_job(self, job_type: str, interval: str) -> json:
        job_id = super().create_job(job_type=job_type, interval=interval)
        return {Const.JOB_ID: job_id}

    @decorator_json
    def remove_job(self, job_id: str) -> json:
        if super().remove_job(job_id):
            return {"message": f"Job {job_id} has been deleted"}
        else:
            raise Exception(f"Error during deletion of the job id: {job_id}")

    @decorator_json
    def activate_job(self, job_id) -> json:
        if super().activate_job(job_id):
            return {"message": f"Job {job_id} has been activated"}
        else:
            raise Exception(f"Error during activation of the job id: {job_id}")

    @decorator_json
    def deactivate_job(self, job_id) -> json:
        if super().deactivate_job(job_id):
            return {"message": f"Job {job_id} has been deactivated"}
        else:
            raise Exception(f"Error during deactivation of the job id: {job_id}")

    @decorator_json
    def get_job_status(self) -> str:
        job_state = JobScheduler().get().state
        if job_state != 1:
            raise Exception(f"Job Scheduler is not running")
        return job_state

    @decorator_json
    def create_alert(
        self,
        alert_type: str,
        channel_id: str,
        symbol: str,
        interval: str,
        strategies: list,
        signals: list,
        comment: str,
    ):
        alert_id = super().create_alert(
            alert_type=alert_type,
            channel_id=channel_id,
            symbol=symbol,
            interval=interval,
            strategies=strategies,
            signals=signals,
            comment=comment,
        )

        return {Const.DB_ID: alert_id}

    @decorator_json
    def update_alert(
        self, id: str, interval: str, strategies: list, signals: list, comment: str
    ):
        if super().update_alert(
            id=id,
            interval=interval,
            strategies=strategies,
            signals=signals,
            comment=comment,
        ):
            return {"message": f"Alert {id} has been updated"}
        else:
            raise Exception(f"Error during update of the alert: {id}")

    @decorator_json
    def remove_alert(self, id: str):
        if super().remove_alert(id):
            return {"message": f"Alert {id} has been deleted"}
        else:
            raise Exception(f"Error during deletion of the alert: {id}")

    @decorator_json
    def get_alerts(self, alert_type: str, symbol: str, interval: str):
        return super().get_alerts(
            alert_type=alert_type, symbol=symbol, interval=interval
        )

    @decorator_json
    def create_order(
        self,
        order_type: str,
        open_date_time: str,
        symbol: str,
        interval: str,
        price: float,
        quantity: float,
        strategies: list,
    ) -> json:
        order_id = super().create_order(
            order_type=order_type,
            open_date_time=open_date_time,
            symbol=symbol,
            interval=interval,
            price=price,
            quantity=quantity,
            strategies=strategies,
        )

        return {Const.DB_ID: order_id}

    @decorator_json
    def remove_order(self, id: str) -> json:
        if super().remove_order(id):
            return {"message": f"Order {id} has been deleted"}
        else:
            raise Exception(f"Error during deletion of the order: {id}")

    @decorator_json
    def get_orders(self, symbol: str, interval: str) -> json:
        return super().get_orders(symbol=symbol, interval=interval)

    @decorator_json
    def get_dashboard(self, symbol: str):
        response = {}

        response["symbol"] = (
            Symbols(from_buffer=True).get_symbol(code=symbol).get_symbol_json()
        )
        response["history_data"] = []
        response["strategy_data"] = []
        response["signals"] = []
        response["trends"] = []

        signals_list = super().get_signals(
            symbols=[symbol],
            intervals=[],
            strategies=[],
            signals_config=[Const.STRONG_BUY, Const.STRONG_SELL],
            closed_bars=True,
        )

        for signal_inst in signals_list:
            response["signals"].append(signal_inst.get_signal_dict())

        return response

    @decorator_json
    def get_user(self, id: str) -> json:
        return UserHandler.get_user_by_id(id)

    @decorator_json
    def get_user_by_email(self, email: str) -> json:
        return UserHandler().get_user_by_email(email)

    @decorator_json
    def get_users(self, search: str = None) -> json:
        return UserHandler.get_users(search)

    @decorator_json
    def create_user(self, user_model: UserModel) -> json:
        return UserHandler.create_user(user_model)

    @decorator_json
    def update_user(self, id: str, query: dict) -> json:
        return UserHandler.update_user(id=id, query=query)

    @decorator_json
    def delete_user(self, id: str) -> json:
        return UserHandler.delete_user(id)

    @decorator_json
    def get_trader(self, id: str) -> json:
        return TraderHandler.get_trader(id)

    @decorator_json
    def get_traders(self, user_email: str = None, status: int = None) -> json:
        return TraderHandler.get_traders_by_email(user_email=user_email, status=status)

    @decorator_json
    def create_trader(self, trader_model: TraderModel) -> json:
        return TraderHandler.create_trader(trader_model)

    @decorator_json
    def update_trader(self, id: str, query: dict) -> json:
        return TraderHandler.update_trader(id=id, query=query)

    @decorator_json
    def delete_trader(self, id: str) -> json:
        if TraderHandler.delete_trader(id=id):
            return {"message": f"Trader {id} has been deleted"}
        else:
            raise Exception(f"Error during deletion of the trader id: {id}")

    @decorator_json
    def check_trader_status(self, id: str) -> str:
        return TraderHandler.check_status(id)

    @decorator_json
    def get_session(self, id: str) -> json:
        return SessionHandler.get_session(id)

    @decorator_json
    def get_session_leverages(self, id: str) -> json:
        return Robot().get_session_manager(session_id=id).get_positions()

    @decorator_json
    def get_sessions(self, user_email: str) -> json:
        sessions = []

        sessions_mdl = SessionHandler.get_sessions_by_email(user_email)

        for session_mdl in sessions_mdl:
            balance_mdl = BalanceHandler.get_balance_4_session(
                session_id=session_mdl.id
            )

            session = session_mdl.model_dump()
            session["balance"] = balance_mdl.model_dump()

            sessions.append(session)

        return sessions

    @decorator_json
    def create_session(
        self, session_mdl: SessionModel, balance_mdl: BalanceModel
    ) -> json:
        if session_mdl.session_type == SessionType.TRADING:
            # Check balance of the account
            total_balance = BalanceHandler.get_account_balance(
                account_id=balance_mdl.account_id,
                init_balance=balance_mdl.init_balance,
            )
            reserved_balance = total_balance + total_balance * 0.2

            exchange_handler = ExchangeHandler.get_handler(
                trader_id=session_mdl.trader_id
            )
            account = exchange_handler.get_account_info(
                account_id=balance_mdl.account_id
            )
            account_balance = (
                account[Const.API_FLD_ACCOUNT_FREE]
                + account[Const.API_FLD_ACCOUNT_LOCKED]
            )
            if account_balance < reserved_balance:
                raise Exception(
                    f"There are not enough funds in the account to create this session. Increase the balance or reduce the initial balance of the session."
                )

            # Check duplicates of entries
            existing_sessions = SessionHandler.get_sessions(
                user_id=session_mdl.user_id,
                trader_id=session_mdl.trader_id,
                symbol=session_mdl.symbol,
                session_type=SessionType.TRADING,
            )
            if existing_sessions:
                raise Exception(
                    f"There are a duplicate of session for symbol {session_mdl.symbol}"
                )

        session = SessionHandler.create_session(session_mdl)

        balance_mdl.session_id = session.id
        balance = BalanceHandler.create_balance(balance_mdl)

        return session

    @decorator_json
    def activate_session(self, session_id: str) -> json:
        if SessionHandler.update_session(
            id=session_id, query={"status": SessionStatus.active}
        ):
            return {"message": f"Session {session_id} has been activated"}
        else:
            raise Exception(f"Error during activation of the session id: {session_id}")

    @decorator_json
    def inactivate_session(self, session_id: str) -> json:
        if SessionHandler.update_session(
            id=session_id, query={"status": SessionStatus.closed}
        ):
            return {"message": f"Session {session_id} has been closed"}
        else:
            raise Exception(f"Error during closing of the session id: {session_id}")

    @decorator_json
    def delete_session(self, session_id: str) -> json:
        if SessionHandler.delete_session(id=session_id):
            return {"message": f"Session {session_id} has been deleted"}
        else:
            raise Exception(f"Error during deletion of the session id: {session_id}")

    @decorator_json
    def get_balance(self, id: str) -> json:
        return BalanceHandler.get_balance(id)

    @decorator_json
    def get_balances(self, session_id: str = None) -> json:
        return BalanceHandler.get_balances(session_id)

    @decorator_json
    def create_balance(self, balance_model: BalanceModel) -> json:
        return BalanceHandler.create_balance(balance_model)

    @decorator_json
    def get_order(self, id: str) -> json:
        return OrderHandler.get_order(id)

    @decorator_json
    def get_orders(self, session_id: str = None) -> json:
        return OrderHandler.get_orders(session_id)

    @decorator_json
    def create_order(self, order_model: OrderModel) -> json:
        return OrderHandler.create_order(order_model)

    @decorator_json
    def get_leverage(self, id: str) -> json:
        return LeverageHandler.get_leverage(id)

    @decorator_json
    def get_leverages(self, session_id: str = None) -> json:
        return LeverageHandler.get_leverages(session_id)

    @decorator_json
    def create_leverage(self, session_id: str, open_mdl: OrderOpenModel) -> json:
        session_manager: SessionManager = Robot().get_session_manager(session_id)
        return session_manager.open_position(open_mdl)

    @decorator_json
    def close_leverage(self, leverage_id: str) -> json:
        leverage_mdl = LeverageHandler.get_leverage(leverage_id)

        session_manager: SessionManager = Robot().get_session_manager(
            session_id=leverage_mdl.session_id
        )

        if session_manager.close_position():
            return {"message": f"Position {leverage_id} has been closed"}
        else:
            raise Exception(f"Error during closing of the position id: {leverage_id}")

    @decorator_json
    def get_transaction(self, id: str) -> json:
        return TransactionHandler.get_transaction(id)

    @decorator_json
    def get_transactions(
        self, user_id: str = None, session_id: str = None, local_order_id: str = None
    ) -> json:
        return TransactionHandler.get_transactions(
            user_id=user_id, session_id=session_id, local_order_id=local_order_id
        )

    @decorator_json
    def create_transaction(self, transaction_model: TransactionModel) -> json:
        return TransactionHandler.create_transaction(transaction_model)

    @decorator_json
    def get_accounts(self, trader_id: str) -> json:
        return ExchangeHandler.get_handler(trader_id=trader_id).get_accounts()

    @decorator_json
    def get_leverage_settings(self, trader_id: str, symbol: str) -> json:
        return ExchangeHandler.get_handler(trader_id=trader_id).get_leverage_settings(
            symbol=symbol
        )

    @decorator_json
    def get_trend(self, param: ParamSymbolIntervalLimit) -> json:
        return TrendCCI().calculate_trends(param)


class ResponserEmail(ResponserBase):
    def get_signals(
        self,
        symbols: list,
        intervals: list,
        strategies: list,
        signals_config: list,
        closed_bars: bool,
    ) -> Messages:
        signals_list = super().get_signals(
            symbols=symbols,
            intervals=intervals,
            strategies=strategies,
            signals_config=signals_config,
            closed_bars=closed_bars,
        )

        # Create the HTML table
        table_html = '<table border="1">'
        table_html += "<tr><th>DateTime</th><th>Symbol</th><th>Interval</th><th>Strategy</th><th>Signal</th></tr>"
        for signal_inst in signals_list:
            table_html += "<tr>"
            table_html += f"<td>{signal_inst.get_date_time().isoformat()}</td>"
            table_html += f"<td>{signal_inst.get_symbol()}</td>"
            table_html += f"<td>{signal_inst.get_interval()}</td>"
            table_html += f"<td>{signal_inst.get_strategy()}</td>"
            table_html += f"<td>{signal_inst.get_signal()}</td>"
            table_html += "</tr>"
        table_html += "</table>"

        # Create the email body as HTML
        message_text = (
            f"<h4>Alert signals for {signal_inst.get_interval()}</h4>{table_html}"
        )

        message_inst = MessageEmail(
            channel_id="None",
            subject=f"[TradingTool]: Alert signals for {intervals[0]}",
            message_text=message_text,
        )

        messages_inst = Messages()
        messages_inst.add_message(message_inst)

        return messages_inst


class ResponserBot(ResponserBase):
    def get_signals_for_alerts(self, alerts_db: dict) -> Messages:
        messages_inst = Messages()

        for alert_db in alerts_db:
            channel_id = alert_db[Const.DB_CHANNEL_ID]
            symbol = alert_db[Const.DB_SYMBOL]
            interval = alert_db[Const.DB_INTERVAL]
            strategies = alert_db[Const.DB_STRATEGIES]
            signals_config = alert_db[Const.DB_SIGNALS]
            comment = alert_db[Const.DB_COMMENT]

            comments_text = f" | {comment}" if comment else ""

            signals_list = super().get_signals(
                symbols=[symbol],
                intervals=[interval],
                strategies=strategies,
                signals_config=signals_config,
                closed_bars=True,
            )

            for signal_inst in signals_list:
                signal_text = f"<b>{signal_inst.get_signal()}</b>"
                message_text = f"{signal_inst.get_date_time().isoformat()} - <b>{signal_inst.get_symbol()} - {signal_inst.get_interval()}</b>: ({signal_inst.get_strategy()}) - {signal_text}{comments_text}\n\n"

                # Add header of the message before the first content
                if not messages_inst.check_message(channel_id):
                    message_text = (
                        f"<b>Local: Alert signals for {interval}: \n</b>{message_text}"
                    )

                messages_inst.add_message_text(channel_id=channel_id, text=message_text)

        return messages_inst

    def get_signals_for_orders(self, orders_db: dict) -> Messages:
        messages_inst = Messages()

        for order_db in orders_db:
            channel_id = "1658698044"
            order_type = order_db[Const.DB_ORDER_TYPE]
            symbol = order_db[Const.DB_SYMBOL]
            interval = order_db[Const.DB_INTERVAL]
            strategies = order_db[Const.DB_STRATEGIES]

            signals_list = super().get_signals(
                symbols=[symbol],
                intervals=[interval],
                strategies=strategies,
                signals_config=[],
                closed_bars=True,
            )

            for signal_inst in signals_list:
                signal_value = signal_inst.get_signal()
                signal_text = f"<b>{signal_value}</b>"
                comment_text = self.get_comment_of_order(order_type, signal_value)

                message_text = f"{signal_inst.get_date_time().isoformat()} - <b>{signal_inst.get_symbol()} - {signal_inst.get_interval()}</b>: ({signal_inst.get_strategy()}) - {signal_text}{comment_text}\n"

                # Add header of the message before the first content
                if not messages_inst.check_message(channel_id):
                    message_text = (
                        f"<b>Local: Order signals for {interval}: \n</b>{message_text}"
                    )

                messages_inst.add_message_text(channel_id=channel_id, text=message_text)

        return messages_inst

    def get_comment_of_order(self, order_type: str, signal_value: str) -> str:
        if order_type == Const.LONG:
            if signal_value in (Const.BUY, Const.STRONG_BUY):
                return f" | <b>You can open more LONG positions</b>"
            elif signal_value in (Const.SELL, Const.STRONG_SELL):
                return f" | <b>CLOSE all postions</b>"
        elif order_type == Const.SHORT:
            if signal_value in (Const.BUY, Const.STRONG_BUY):
                return f" | <b>CLOSE all postions</b>"
            elif signal_value in (Const.SELL, Const.STRONG_SELL):
                return f" | <b>You can open more SHORT positions</b>"
        else:
            return ""


class JobScheduler:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_._instance.init()
        return class_._instance

    def init(self) -> None:
        self.__db_inst = MongoJobs()
        self.__scheduler = BackgroundScheduler()
        self.__scheduler.start()
        self.__init_jobs()

    def get(self):
        return self.__scheduler

    def get_jobs(self):
        jobs = []

        # Get jobs from DB
        db_jobs = self.__db_inst.get_many()

        for db_job in db_jobs:
            job_id = str(db_job[Const.DB_ID])

            job_details = {
                Const.JOB_ID: job_id,
                Const.DB_JOB_TYPE: db_job[Const.DB_JOB_TYPE],
                Const.INTERVAL: db_job[Const.DB_INTERVAL],
                Const.DB_IS_ACTIVE: db_job[Const.DB_IS_ACTIVE],
                Const.DATETIME: "",
            }

            job = runtime_buffer.get_job_from_buffer(job_id)
            if job:
                job_details[Const.DATETIME] = job.next_run_time

            jobs.append(job_details)

        return jobs

    def create_job(self, job_type: str, interval: str) -> str:
        # Create job entry in the DB -> get job_id
        job_id = self.__db_inst.create_job(
            job_type=job_type, interval=interval, is_active=False
        )

        # Schedule and add job to the buffer
        self.__add_job(job_id=job_id, job_type=job_type, interval=interval)

        # Activate the job in the DB
        self.__db_inst.activate_job(job_id)

        return job_id

    def activate_job(self, job_id: str) -> bool:
        db_job = self.__db_inst.get_one(job_id)

        job_id = str(db_job[Const.DB_ID])
        job_type = db_job[Const.DB_JOB_TYPE]
        interval = db_job[Const.DB_INTERVAL]

        self.__add_job(job_id=job_id, job_type=job_type, interval=interval)

        return self.__db_inst.activate_job(job_id)

    def deactivate_job(self, job_id: str) -> bool:
        self.__scheduler.remove_job(job_id)
        runtime_buffer.remove_job_from_buffer(job_id)

        return self.__db_inst.deactivate_job(job_id)

    def remove_job(self, job_id: str) -> bool:
        try:
            self.__scheduler.remove_job(job_id)
            runtime_buffer.remove_job_from_buffer(job_id)
            return self.__db_inst.delete_job(job_id)
        except JobLookupError as error:
            logger.error(f"JOB: Error during remove job: {job_id} - {error}")
            raise Exception(f"JOB: Error during remove job: {job_id} - {error}")

    def __init_jobs(self):
        # Get jobs from the DB
        db_jobs = self.__db_inst.get_active_jobs()

        for item in db_jobs:
            job_id = str(item[Const.DB_ID])
            job_type = item[Const.DB_JOB_TYPE]
            interval = item[Const.DB_INTERVAL]

            self.__add_job(job_id=job_id, job_type=job_type, interval=interval)

    def __add_job(self, job_id: str, job_type: str, interval: str) -> Job:
        # Schedule a job based on a job type
        if job_type == Const.JOB_TYPE_BOT:
            job = self.__scheduler.add_job(
                job_func_send_bot_notification,
                self.__generateCronTrigger(interval),
                id=job_id,
                args=(interval,),
            )
        elif job_type == Const.JOB_TYPE_EMAIL:
            job = self.__scheduler.add_job(
                job_func_send_email_notification,
                self.__generateCronTrigger(interval),
                id=job_id,
                args=(interval,),
            )
        elif job_type == Const.JOB_TYPE_INIT:
            job = self.__scheduler.add_job(
                job_func_initialise_runtime_data,
                CronTrigger(day_of_week="mon-fri", hour="2", jitter=60, timezone="UTC"),
                id=job_id,
            )
        elif job_type == Const.JOB_TYPE_ROBOT:
            job = self.__scheduler.add_job(
                job_func_trading_robot,
                self.__generateCronTrigger(interval),
                id=job_id,
                args=(interval,),
            )
        else:
            raise Exception(f"Job type {job_type} can't be detected")

        # Add job to the runtime buffer
        runtime_buffer.set_job_to_buffer(job)

        if config.get_config_value(Const.CONFIG_DEBUG_LOG):
            logger.info(
                f"JOB: {job_type} is scheduled for interval: {interval} at {job.next_run_time}"
            )

        return job

    def __generateCronTrigger(self, interval) -> CronTrigger:
        day_of_week = "*"
        hour = None
        minute = "0"
        second = "40"

        if interval == Const.TA_INTERVAL_5M:
            minute = "*/5"
        elif interval == Const.TA_INTERVAL_15M:
            minute = "*/15"
        elif interval == Const.TA_INTERVAL_30M:
            minute = "*/30"
        elif interval == Const.TA_INTERVAL_1H:
            hour = "*"
            minute = "1"
        elif interval == Const.TA_INTERVAL_4H:
            hour = "0,4,8,12,16,20"
            minute = "1"
        elif interval == Const.TA_INTERVAL_1D:
            hour = "8"
            minute = "1"
        elif interval == Const.TA_INTERVAL_1WK:
            day_of_week = "mon"
            hour = "8"
            minute = "1"
        else:
            raise Exception("Incorrect interval for subscription")

        return CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            second=second,
            timezone="UTC",
        )


class NotificationBase:
    def send(self, messages_inst: Messages):
        pass


class NotificationEmail(NotificationBase):
    def send(self, messages_inst: Messages):
        # Email configuration
        sender_email = os.getenv("SMTP_USERNAME")

        # SMTP server configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        smtp_username = sender_email
        smtp_password = os.getenv("SMTP_PASSWORD")

        for message_inst in messages_inst.get_messages().values():
            # message_inst.get_channel_id()
            receiver_email = os.getenv("RECEIVER_EMAIL").split(";")

            # Create a MIME message object
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = ", ".join(receiver_email)
            msg["Subject"] = message_inst.get_subject()
            body = MIMEText(message_inst.get_message_text(), "html")
            msg.attach(body)

            try:
                # Create a secure connection with the SMTP server
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(smtp_username, smtp_password)

                # Send the email
                server.sendmail(sender_email, receiver_email, msg.as_string())
                if config.get_config_value(Const.CONFIG_DEBUG_LOG):
                    logger.info(
                        f"NOTIFICATION: EMAIL - Sent successfully to {receiver_email}."
                    )

            except Exception as e:
                logger.error(
                    "NOTIFICATION: EMAIL - An error occurred while sending the email:",
                    str(e),
                )

            finally:
                # Close the SMTP server connection
                server.quit()


class NotificationBot(NotificationBase):
    def send(self, messages_inst: Messages):
        bot_token = os.getenv("BOT_TOKEN")
        bot_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        if not bot_token:
            logger.error("Bot token is not maintained in the environment values")

        for message_inst in messages_inst.get_messages().values():
            channel_id = message_inst.get_channel_id()

            params = {
                "chat_id": channel_id,
                "text": message_inst.get_message_text(),
                "parse_mode": "HTML",
            }
            response = requests.post(bot_url, data=params)
            if response.ok:
                if config.get_config_value(Const.CONFIG_DEBUG_LOG):
                    logger.info(
                        f"NOTIFICATION: BOT - Sent successfully to chat bot: {channel_id}"
                    )
            else:
                logger.error(
                    f"NOTIFICATION: BOT - Failed to send message to chat bot: {channel_id} - {response.text}"
                )


# @decorator_json
# def getSimulate(symbols: list, intervals: list, strategyCodes: list):
#     return Simulator().simulateTrading(symbols, intervals, strategyCodes)


# @decorator_json
# def getSimulations(symbols: list, intervals: list, strategyCodes: list):
#     return Simulator().getSimulations(symbols, intervals, strategyCodes)


# @decorator_json
# def getSignalsBySimulation(symbols: list, intervals: list, strategyCodes: list):
#     return Simulator().getSignalsBySimulation(symbols, intervals, strategyCodes)


# def getLogs(start_date, end_date):
#     # date_format = "%Y-%m-%d"
#     # start_date = datetime.strptime(start_date, date_format)
#     # end_date = datetime.strptime(end_date, date_format) + datetime.timedelta(days=1)
#     # logs = []
#     # current_date = start_date
#     # while current_date < end_date:
#     try:
#         with open(log_file_name, "r") as log_file:
#             logs = log_file.read()
#     except FileNotFoundError:
#         pass
#         # current_date += datetime.timedelta(days=1)

#     logs = logs.replace('\n', '<br>')

#     return logs
