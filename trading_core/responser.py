import json
import bson.json_util as json_util
import pandas as pd
import numpy as np
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
import logging

from .constants import Const
from .core import config
from .mongodb import MongoJobs, MongoSimulations
from .handler import ExchangeHandler, AlertHandler
from .trend import TrendCCI

from trading_core.common import (
    ExchangeId,
    IntervalType,
    ChannelType,
    AlertType,
    HistoryDataParamModel,
    StrategyParamModel,
    SymbolIntervalLimitModel,
    BaseModel,
    UserModel,
    ChannelModel,
    AlertModel,
    TraderModel,
    SessionModel,
    SessionType,
    BalanceModel,
    OrderModel,
    TransactionModel,
    SessionStatus,
    OrderOpenModel,
    OrderSideType,
)
from trading_core.strategy import StrategyFactory, SignalFactory
from trading_core.handler import (
    UserHandler,
    ChannelHandler,
    AlertHandler,
    SessionHandler,
    BalanceHandler,
    OrderHandler,
    LeverageHandler,
    TransactionHandler,
    buffer_runtime_handler,
)
from trading_core.robot import Robot, SessionManager

load_dotenv()

logger = logging.getLogger("responser")


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

    buffer_runtime_handler.clear_buffer()
    # buffer_runtime_handler.get_symbol_handler().get_symbols()


def job_func_send_bot_notification(interval):
    if config.get_config_value(Const.CONFIG_DEBUG_LOG):
        logger.info(f"JOB: {Const.JOB_TYPE_BOT} is triggered for interval - {interval}")

    responser = ResponserBot()
    notificator = NotificationBot()

    channels = ChannelHandler.get_channels(type=ChannelType.TELEGRAM_BOT)
    channel_ids = [channel_mdl.id for channel_mdl in channels]

    if channel_ids:
        alerts = AlertHandler.get_alerts(interval=interval, channel_ids=channel_ids)

    if alerts:
        alert_messages = responser.get_signals_for_alerts(
            alert_mdls=alerts, interval=interval
        )
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

    robot_errors = Robot().run_job(interval)

    if robot_errors:
        responser = ResponserBot()
        notificator = NotificationBot()
        message_inst = responser.get_error_messages(robot_errors=robot_errors)
        notificator.send(message_inst)


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

    def get_symbol_list(**kwargs) -> list:
        symbol_handler = buffer_runtime_handler.get_symbol_handler()

        return symbol_handler.get_symbol_list(**kwargs)

    def get_intervals(
        self, trader_id: str = None, user_id: str = None, importances: list = None
    ) -> list:
        return buffer_runtime_handler.get_interval_handler(
            trader_id=trader_id, user_id=user_id
        ).get_interval_models(importances)

    def get_strategies(self) -> list:
        return StrategyFactory.get_strategy_config_list_vh()

    def get_history_data(
        self, trader_id: str, param: HistoryDataParamModel
    ) -> pd.DataFrame:
        return (
            buffer_runtime_handler.get_history_data_handler(trader_id)
            .get_history_data(param)
            .data
        )

    def get_strategy_data(self, param: StrategyParamModel) -> pd.DataFrame:
        return StrategyFactory.get_strategy_data(param)

    def get_signals(
        self,
        trader_id: str,
        symbols: list,
        intervals: list,
        strategies: list,
        signal_types: list,
        closed_bars: bool,
    ) -> list:
        return SignalFactory().get_signals_by_list(
            trader_id=trader_id,
            symbols=symbols,
            intervals=intervals,
            strategies=strategies,
            signal_types=signal_types,
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

    def get_simulations(self, symbols: list, intervals: list, strategies: list) -> list:
        return MongoSimulations().get_simulations(
            symbols=symbols, intervals=intervals, strategies=strategies
        )

    def get_user(self, id: str):
        return UserHandler.get_user_by_id(id)

    def get_users(self, search: str):
        return UserHandler.get_users(search)

    def create_user(self, user_model: UserModel):
        return UserHandler.create_user(user_model)


class ResponserWeb(ResponserBase):
    @decorator_json
    def get_config(self) -> json:
        return config.get_config_values()

    @decorator_json
    def update_config(self, config_payload: dict) -> json:
        result = config.update_config(config_payload)
        if result:
            return {"message": f"Config has been updated"}
        else:
            raise Exception(f"Error during update of the config")

    @decorator_json
    def get_symbol_list(*args, **kwargs) -> json:
        symbol_handler = buffer_runtime_handler.get_symbol_handler(
            trader_id=kwargs.get(Const.DB_TRADER_ID)
        )
        return symbol_handler.get_symbol_list(**kwargs)

    @decorator_json
    def get_intervals(
        self, trader_id: str = None, user_id: str = None, importances: list = None
    ) -> json:
        return super().get_intervals(
            trader_id=trader_id, user_id=user_id, importances=importances
        )

    @decorator_json
    def get_strategies(self) -> json:
        return super().get_strategies()

    @decorator_json
    def get_history_data(self, trader_id: str, param: HistoryDataParamModel) -> json:
        return super().get_history_data(trader_id=trader_id, param=param)

    @decorator_json
    def get_strategy_data(self, param: StrategyParamModel) -> json:
        return super().get_strategy_data(param)

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
    def get_dashboard(self, symbol: str):
        pass
        # response = {}

        # response["symbol"] = (
        #     Symbols(from_buffer=True).get_symbol(code=symbol).get_symbol_json()
        # )
        # response["history_data"] = []
        # response["strategy_data"] = []
        # response["signals"] = []
        # response["trends"] = []

        # signals_list = super().get_signals(
        #     symbols=[symbol],
        #     intervals=[],
        #     strategies=[],
        #     signals_config=[Const.STRONG_BUY, Const.STRONG_SELL],
        #     closed_bars=True,
        # )

        # for signal_inst in signals_list:
        #     response["signals"].append(signal_inst.get_signal_dict())

        # return response

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
    def get_channels(self, user_email: str) -> json:
        return ChannelHandler.get_channels_by_email(user_email)

    @decorator_json
    def create_channel(self, channel_mdl: ChannelModel) -> json:
        return ChannelHandler.create_channel(channel_mdl)

    @decorator_json
    def update_channel(self, channel_id: str, query: dict) -> json:
        return ChannelHandler.update_channel(id=channel_id, query=query)

    @decorator_json
    def delete_channel(self, channel_id: str) -> json:
        if ChannelHandler.delete_channel(id=channel_id):
            return {"message": f"Channel {channel_id} has been deleted"}
        else:
            raise Exception(f"Error during deletion of the channel id: {channel_id}")

    @decorator_json
    def get_alerts(self, user_email: str) -> json:
        return AlertHandler.get_alerts_by_email(user_email)

    @decorator_json
    def create_alert(self, alert_mdl: AlertModel) -> json:
        return AlertHandler.create_alert(alert_mdl)

    @decorator_json
    def update_alert(self, alert_id: str, query: dict) -> json:
        return AlertHandler.update_alert(id=alert_id, query=query)

    @decorator_json
    def delete_alert(self, alert_id: str) -> json:
        if AlertHandler.delete_alert(id=alert_id):
            return {"message": f"Alert {alert_id} has been deleted"}
        else:
            raise Exception(f"Error during deletion of the alert id: {alert_id}")

    @decorator_json
    def get_exchanges(self) -> json:
        return [
            {"name": item.name, "value": item.value, "descr": item.__doc__}
            for item in ExchangeId
        ]

    @decorator_json
    def get_trader(self, id: str) -> json:
        return buffer_runtime_handler.get_trader_handler().get_trader(id)

    @decorator_json
    def get_traders(self, user_email: str = None, status: int = None) -> json:
        return buffer_runtime_handler.get_trader_handler().get_traders_by_email(
            user_email=user_email, status=status
        )

    @decorator_json
    def create_trader(self, trader_model: TraderModel) -> json:
        return buffer_runtime_handler.get_trader_handler().create_trader(trader_model)

    @decorator_json
    def update_trader(self, id: str, query: dict) -> json:
        return buffer_runtime_handler.get_trader_handler().update_trader(
            id=id, query=query
        )

    @decorator_json
    def delete_trader(self, id: str) -> json:
        if buffer_runtime_handler.get_trader_handler().delete_trader(id=id):
            return {"message": f"Trader {id} has been deleted"}
        else:
            raise Exception(f"Error during deletion of the trader id: {id}")

    @decorator_json
    def check_trader_status(self, id: str) -> str:
        return buffer_runtime_handler.get_trader_handler().check_status(id)

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
            session = session_mdl.model_dump()

            balance_mdl = BalanceHandler.get_balance_4_session(
                session_id=session_mdl.id
            )

            session["balance"] = balance_mdl.model_dump()

            if session_mdl.status == SessionStatus.active:
                session["has_open_order"] = LeverageHandler.has_open_leverages(
                    session_id=session_mdl.id
                )

            trader_mdl = buffer_runtime_handler.get_trader_handler().get_trader(
                id=session_mdl.trader_id
            )
            session[Const.DB_EXCHANGE_ID] = trader_mdl.exchange_id

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

        session = SessionHandler.create_session(session_mdl)

        balance_mdl.session_id = session.id
        BalanceHandler.create_balance(balance_mdl)

        return session

    @decorator_json
    def activate_session(self, session_id: str) -> json:
        session_mdl = SessionHandler.get_session(id=session_id)

        # Check duplicates of active session
        existing_sessions = SessionHandler.get_sessions(
            user_id=session_mdl.user_id,
            trader_id=session_mdl.trader_id,
            symbol=session_mdl.symbol,
            session_type=SessionType.TRADING,
            status=SessionStatus.active,
        )
        if existing_sessions:
            raise Exception(
                f"Only one session for symbol {session_mdl.symbol} can be active"
            )

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
    def get_trend(self, param: SymbolIntervalLimitModel) -> json:
        return TrendCCI().calculate_trends(param)

    @decorator_json
    def get_history_simulation(
        self,
        trader_id: str,
        trading_type: str,
        symbol: str,
        intervals: list,
        strategies: list,
        stop_loss_rate: float,
        is_trailing_stop: bool,
        take_profit_rate: float,
        init_balance: float,
        limit: int,
    ) -> json:
        response = []

        sessions = Robot().run_history_simulation(
            trader_id=trader_id,
            trading_type=trading_type,
            symbol=symbol,
            intervals=intervals,
            strategies=strategies,
            stop_loss_rate=stop_loss_rate,
            is_trailing_stop=is_trailing_stop,
            take_profit_rate=take_profit_rate,
            init_balance=init_balance,
            limit=limit,
        )

        for session_mng in sessions:
            positions = []
            high_rates = []
            low_rates = []

            balance_mdl = session_mng.get_balance_manager().get_balance_model()
            transactions = [
                item.model_dump() for item in session_mng.get_transactions()
            ]

            for position in session_mng.get_positions():
                positions.append(position.model_dump())

                if position.side == OrderSideType.buy:
                    high_rates.append(position.high_percent)
                    low_rates.append(-1 * position.low_percent)
                else:
                    high_rates.append(-1 * position.low_percent)
                    low_rates.append(position.high_percent)

            session_response = session_mng.get_session().model_dump()
            session_response["optimal_take_profit_rate"] = np.percentile(high_rates, 80)
            session_response["optimal_stop_loss_rate"] = np.percentile(low_rates, 80)
            session_response["balance"] = balance_mdl.model_dump()
            session_response["positions"] = positions
            session_response["transactions"] = transactions

            response.append(session_response)

        return response


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
    def get_signals_for_alerts(
        self, alert_mdls: list[AlertModel], interval: IntervalType = None
    ) -> Messages:
        messages_inst = Messages()

        for alert_mdl in alert_mdls:
            trader_id = alert_mdl.trader_id
            channel_id = alert_mdl.channel_id
            symbols = alert_mdl.symbols
            if interval:
                intervals = [interval]
            else:
                intervals = alert_mdl.intervals
            strategies = alert_mdl.strategies
            signal_types = alert_mdl.signals

            signals_mdls = super().get_signals(
                trader_id=trader_id,
                symbols=symbols,
                intervals=intervals,
                strategies=strategies,
                signal_types=signal_types,
                closed_bars=True,
            )

            for signal_mdl in signals_mdls:
                signal_text = f"<b>{signal_mdl.signal.value}</b>"
                message_text = f"{signal_mdl.date_time.isoformat()} - <b>{signal_mdl.symbol} - {signal_mdl.interval.value}</b>: ({signal_mdl.strategy.value}) - {signal_text}\n\n"

                # Add header of the message before the first content
                if not messages_inst.check_message(channel_id):
                    message_text = f"<b>Alert signals for {signal_mdl.interval.value}: \n</b>{message_text}"

                messages_inst.add_message_text(channel_id=channel_id, text=message_text)

        return messages_inst

    def get_error_messages(self, robot_errors: dict) -> Messages:
        messages_inst = Messages()

        alert_mdls = AlertHandler().get_alerts(type=AlertType.ERROR)

        for alert_mdl in alert_mdls:
            channel_id = alert_mdl.channel_id

            for session_id, error_text in robot_errors.items():
                message_text = f"<b>{session_id}</b>: - {error_text}\n\n"

                # Add header of the message before the first content
                if not messages_inst.check_message(channel_id):
                    message_text = f"<b>Robot Error Alerts: \n</b>{message_text}"

                messages_inst.add_message_text(channel_id=channel_id, text=message_text)

        return messages_inst


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

            job = buffer_runtime_handler.get_job_handler().get_buffer(key=job_id)
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
        buffer_runtime_handler.get_job_handler().remove_from_buffer(key=job_id)

        return self.__db_inst.deactivate_job(job_id)

    def remove_job(self, job_id: str) -> bool:
        try:
            self.__scheduler.remove_job(job_id)
            buffer_runtime_handler.get_job_handler().remove_from_buffer(key=job_id)
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
        buffer_runtime_handler.get_job_handler().set_buffer(key=job.id, data=job)

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
        jitter = 20

        if interval == IntervalType.MIN_1:
            minute = "*"
            second = "20"
            jitter = 5
        elif interval == IntervalType.MIN_5:
            minute = "*/5"
            jitter = 10
        elif interval == IntervalType.MIN_15:
            minute = "*/15"
        elif interval == IntervalType.MIN_30:
            minute = "*/30"
        elif interval == IntervalType.HOUR_1:
            hour = "*"
            minute = "1"
        elif interval == IntervalType.HOUR_4:
            hour = "0,4,8,12,16,20"
            minute = "1"
        elif interval == IntervalType.DAY_1:
            hour = "8"
            minute = "1"
        elif interval == IntervalType.WEEK_1:
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
            jitter=jitter,
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

            channel_mdl = ChannelHandler.get_channel(id=channel_id)

            params = {
                "chat_id": channel_mdl.channel,
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
