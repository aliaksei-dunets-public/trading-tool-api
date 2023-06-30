import json
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
from .core import logger, runtime_buffer, Symbol, Signal
from .model import model, Symbols
from .strategy import StrategyFactory, SignalFactory
# from .simulator import Simulator
from .mongodb import MongoJobs, MongoAlerts, MongoOrders

load_dotenv()


def decorator_json(func) -> str:
    def wrapper(*args, **kwargs):
        try:
            value = func(*args, **kwargs)

            if isinstance(value, list):
                if all(type(item) == dict for item in value):
                    return json.dumps(value)
                if all(isinstance(item, object) for item in value):
                    return json.dumps([item.__dict__ for item in value])
                else:
                    return json.dumps(value)
            elif isinstance(value, pd.DataFrame):
                return value.to_json(orient="table", index=True)
            elif isinstance(value, object):
                if '__dict__' in value:
                    return json.dumps(value.__dict__)
                else:
                    return json.dumps(value)
            else:
                return json.dumps(value)

        except Exception as error:
            return jsonify({"error": f'{error}'}), 500

    return wrapper


def job_func_initialise_runtime_data():
    logger.info(f"JOB: Refresh runtime buffer")

    runtime_buffer.clearSymbolsBuffer()
    runtime_buffer.clearTimeframeBuffer()
    runtime_buffer.clearHistoryDataBuffer()
    runtime_buffer.clear_signal_buffer()

    model.get_handler().getSymbols(from_buffer=False)


def job_func_send_bot_notification(interval):

    logger.info(
        f"JOB: Bot notification Job is triggered for interval - {interval}")

    responser = ResponserBot()
    notificator = NotificationBot()

    orders_db = MongoOrders().get_orders_by_interval(interval)
    order_messages = responser.get_signals_for_orders(orders_db)
    notificator.send(order_messages)

    alerts_db = MongoAlerts().get_alerts_by_interval(interval)
    alert_messages = responser.get_signals_for_alerts(alerts_db)
    notificator.send(alert_messages)


def job_func_send_email_notification(interval):

    logger.info(
        f"JOB: Email notification Job is triggered for interval - {interval}")

    messages = ResponserEmail().get_signals(symbols=[],
                                            intervals=[interval],
                                            strategies=[],
                                            signals_config=[],
                                            closed_bars=True)

    NotificationEmail().send(messages)


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
        MessageBase.__init__(self, channel_id=channel_id,
                             message_text=message_text)
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


class ResponserBase():
    def get_param_bool(self, param_value):
        return bool(param_value.lower() == 'true')

    def get_symbol(self, code: str) -> Symbol:
        return Symbols().get_symbol(code)

    def get_symbol_list(self, code: str, name: str, status: str, type: str, from_buffer: bool) -> list[Symbol]:
        return Symbols(from_buffer).get_symbol_list(code=code, name=name, status=status, type=type)

    def get_intervals(self, importances: list = None) -> list:
        return model.get_intervals_config(importances)

    def get_indicators(self) -> list:
        return model.get_indicators_config()

    def get_strategies(self) -> list:
        return model.get_strategies()

    def get_history_data(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> pd.DataFrame:
        history_data_inst = model.get_handler().getHistoryData(
            symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)
        return history_data_inst.getDataFrame()

    def get_strategy_data(self, code: str, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> pd.DataFrame:
        strategy_inst = StrategyFactory(code)
        return strategy_inst.get_strategy_data(symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)

    def get_signals(self, symbols: list, intervals: list, strategies: list, signals_config: list, closed_bars: bool) -> list[Signal]:
        return SignalFactory().get_signals(symbols=symbols, intervals=intervals, strategies=strategies, signals_config=signals_config, closed_bars=closed_bars)

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


class ResponserWeb(ResponserBase):
    @decorator_json
    def get_symbol(self, code: str) -> json:
        symbol = super().get_symbol(code)
        if symbol:
            return symbol
        else:
            raise Exception(f"Symbol: {code} can't be detected")

    @decorator_json
    def get_symbol_list(self, code: str, name: str, status: str, type: str, from_buffer: bool) -> json:
        return super().get_symbol_list(code=code, name=name, status=status, type=type, from_buffer=from_buffer)

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
    def get_history_data(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> json:
        return super().get_history_data(symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)

    @decorator_json
    def get_strategy_data(self, code: str, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> json:
        return super().get_strategy_data(code=code, symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)

    @decorator_json
    def get_signals(self, symbols: list, intervals: list, strategies: list, signals_config: list, closed_bars: bool) -> json:
        signals = []
        signals_list = super().get_signals(symbols=symbols, intervals=intervals,
                                           strategies=strategies, signals_config=signals_config, closed_bars=closed_bars)

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
            return {'message': f'Job {job_id} deleted'}
        else:
            raise Exception(f'Error during deletion of the job id: {job_id}')

    @decorator_json
    def activate_job(self, job_id) -> json:
        if super().activate_job(job_id):
            return {'message': f'Job {job_id} has been activated'}
        else:
            raise Exception(f'Error during activation of the job id: {job_id}')

    @decorator_json
    def deactivate_job(self, job_id) -> json:
        if super().deactivate_job(job_id):
            return {'message': f'Job {job_id} has been deactivated'}
        else:
            raise Exception(
                f'Error during deactivation of the job id: {job_id}')


class ResponserEmail(ResponserBase):
    def get_signals(self, symbols: list, intervals: list, strategies: list, signals_config: list, closed_bars: bool) -> Messages:
        signals_list = super().get_signals(symbols=symbols, intervals=intervals,
                                           strategies=strategies, signals_config=signals_config, closed_bars=closed_bars)

        # Create the HTML table
        table_html = '<table border="1">'
        table_html += '<tr><th>DateTime</th><th>Symbol</th><th>Interval</th><th>Strategy</th><th>Signal</th></tr>'
        for signal_inst in signals_list:
            table_html += '<tr>'
            table_html += f'<td>{signal_inst.get_date_time().isoformat()}</td>'
            table_html += f'<td>{signal_inst.get_symbol()}</td>'
            table_html += f'<td>{signal_inst.get_interval()}</td>'
            table_html += f'<td>{signal_inst.get_strategy()}</td>'
            table_html += f'<td>{signal_inst.get_signal()}</td>'
            table_html += '</tr>'
        table_html += '</table>'

        # Create the email body as HTML
        message_text = f'<h4>Alert signals for {signal_inst.get_interval()}</h4>{table_html}'

        message_inst = MessageEmail(
            channel_id='None', subject=f'[TradingTool]: Alert signals for {intervals[0]}', message_text=message_text)

        messages_inst = Messages()
        messages_inst.add_message(message_inst)

        return messages_inst


class ResponserBot(ResponserBase):
    def get_signals_for_alerts(self, alerts_db: dict) -> Messages:

        messages_inst = Messages()

        for alert_db in alerts_db:
            channel_id = alert_db[Const.DB_CHANNEL_ID]
            symbol = alert_db[Const.DB_SYMBOL]
            interval = alert_db[Const.DB_SYMBOL]
            strategies = alert_db[Const.DB_STRATEGIES]
            signals_config = alert_db[Const.DB_SIGNALS]
            comment = alert_db[Const.DB_COMMENT]

            comments_text = f' | {comment}' if comment else ''

            signals_list = super().get_signals(symbols=[symbol], intervals=[
                interval], strategies=strategies, signals_config=signals_config, closed_bars=True)

            for signal_inst in signals_list:
                signal_text = f'<b>{signal_inst.get_signal()}</b>'
                message_text = f'{signal_inst.get_date_time().isoformat()} - <b>{signal_inst.get_symbol()} - {signal_inst.get_interval()}</b>: ({signal_inst.get_strategy()}) - {signal_text}{comments_text}\n\n'

                # Add header of the message before the first content
                if not messages_inst.check_message(channel_id):
                    message_text = f'<b>Alert signals for {interval}: \n</b>{message_text}'

                messages_inst.add_message_text(
                    channel_id=channel_id, text=message_text)

        return messages_inst

    def get_signals_for_orders(self, orders_db: dict) -> Messages:

        def get_comment(self, order_type, signal_value):
            if order_type == Const.LONG:
                if signal_value in (Const.BUY, Const.STRONG_BUY):
                    return f' | <b>You can open more LONG positions</b>'
                elif signal_value in (Const.SELL, Const.STRONG_SELL):
                    return f' | <b>CLOSE all postions</b>'
            elif order_type == Const.SHORT:
                if signal_value in (Const.BUY, Const.STRONG_BUY):
                    return f' | <b>CLOSE all postions</b>'
                elif signal_value in (Const.SELL, Const.STRONG_SELL):
                    return f' | <b>You can open more SHORT positions</b>'
            else:
                return ''

        messages_inst = Messages()

        for order_db in orders_db:
            channel_id = '1658698044'
            order_type = order_db[Const.DB_ORDER_TYPE]
            symbol = order_db[Const.DB_SYMBOL]
            interval = order_db[Const.DB_SYMBOL]
            strategies = order_db[Const.DB_STRATEGIES]

            signals_list = super().get_signals(symbols=[symbol], intervals=[
                interval], strategies=strategies, signals_config=[], closed_bars=True)

            for signal_inst in signals_list:

                signal_value = signal_inst.get_signal()
                signal_text = f'<b>{signal_value}</b>'
                comment_text = get_comment(order_type, signal_value)

                message_text = f'{signal_inst.get_date_time().isoformat()} - <b>{signal_inst.get_symbol()} - {signal_inst.get_interval()}</b>: ({signal_inst.get_strategy()}) - {signal_text}{comment_text}\n'

                # Add header of the message before the first content
                if not messages_inst.check_message(channel_id):
                    message_text = f'<b>Order signals for {interval}: \n</b>{message_text}'

                messages_inst.add_message_text(
                    channel_id=channel_id, text=message_text)

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

            job_details = {Const.JOB_ID: job_id,
                           Const.DB_JOB_TYPE: db_job[Const.DB_JOB_TYPE],
                           Const.INTERVAL: db_job[Const.DB_INTERVAL],
                           Const.DB_IS_ACTIVE: db_job[Const.DB_IS_ACTIVE],
                           Const.DATETIME: ''}

            job = runtime_buffer.get_job_from_buffer(job_id)
            if job:
                job_details[Const.DATETIME] = job.next_run_time

            jobs.append(job_details)

        return jobs

    def create_job(self, job_type: str, interval: str) -> str:
        # Create job entry in the DB -> get job_id
        job_id = self.__db_inst.create_job(
            job_type=job_type, interval=interval, is_active=False)

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
            logger.error(f'JOB: Error during remove job: {job_id} - {error}')
            raise Exception(
                f'JOB: Error during remove job: {job_id} - {error}')

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
                job_func_send_bot_notification, self.__generateCronTrigger(interval), id=job_id, args=(interval,))
        elif job_type == Const.JOB_TYPE_EMAIL:
            job = self.__scheduler.add_job(
                job_func_send_email_notification, self.__generateCronTrigger(interval), id=job_id, args=(interval,))
        elif job_type == Const.JOB_TYPE_INIT:
            job = self.__scheduler.add_job(
                job_func_initialise_runtime_data, CronTrigger(day_of_week='mon-fri', hour='2', jitter=60, timezone='UTC'), id=job_id)

        # Add job to the runtime buffer
        runtime_buffer.set_job_to_buffer(job)

        logger.info(
            f"JOB: {job_type} is scheduled for interval: {interval} at {job.next_run_time}")

        return job

    def __generateCronTrigger(self, interval) -> CronTrigger:
        day_of_week = '*'
        hour = None
        minute = '0'
        second = '40'

        if interval == Const.TA_INTERVAL_5M:
            minute = '*/5'
        elif interval == Const.TA_INTERVAL_15M:
            minute = '*/15'
        elif interval == Const.TA_INTERVAL_30M:
            minute = '*/30'
        elif interval == Const.TA_INTERVAL_1H:
            hour = '*'
            minute = '1'
        elif interval == Const.TA_INTERVAL_4H:
            hour = '0,4,8,12,16,20'
            minute = '1'
        elif interval == Const.TA_INTERVAL_1D:
            hour = '8'
            minute = '1'
        elif interval == Const.TA_INTERVAL_1WK:
            day_of_week = 'mon'
            hour = '8'
            minute = '1'
        else:
            Exception('Incorrect interval for subscription')

        return CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute, second=second, timezone='UTC')


class NotificationBase:
    def send(self, messages_inst: Messages):
        pass


class NotificationEmail(NotificationBase):
    def send(self, messages_inst: Messages):

        # Email configuration
        sender_email = os.getenv("SMTP_USERNAME")

        # SMTP server configuration
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_username = sender_email
        smtp_password = os.getenv("SMTP_PASSWORD")

        for message_inst in messages_inst.get_messages().values():

            # message_inst.get_channel_id()
            receiver_email = os.getenv("RECEIVER_EMAIL").split(';')

            # Create a MIME message object
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(receiver_email)
            msg['Subject'] = message_inst.get_subject()
            body = MIMEText(message_inst.get_message_text(), 'html')
            msg.attach(body)

            try:
                # Create a secure connection with the SMTP server
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(smtp_username, smtp_password)

                # Send the email
                server.sendmail(sender_email, receiver_email, msg.as_string())

                logger.info(
                    f'NOTIFICATION: EMAIL - Sent successfully to {receiver_email}.')

            except Exception as e:
                logger.error(
                    'NOTIFICATION: EMAIL - An error occurred while sending the email:', str(e))

            finally:
                # Close the SMTP server connection
                server.quit()


class NotificationBot(NotificationBase):

    def send(self, messages_inst: Messages):
        bot_token = os.getenv("BOT_TOKEN")
        bot_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'

        if not bot_token:
            logger.error(
                'Bot token is not maintained in the environment values')

        for message_inst in messages_inst.get_messages().values():

            channel_id = message_inst.get_channel_id()

            params = {'chat_id': channel_id,
                      'text': message_inst.get_message_text(),
                      'parse_mode': 'HTML'}
            response = requests.post(bot_url, data=params)
            if response.ok:
                logger.info(
                    f"NOTIFICATION: BOT - Sent successfully to chat bot: {channel_id}")
            else:
                logger.error(
                    f"NOTIFICATION: BOT - Failed to send message to chat bot: {channel_id} - {response.text}")


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
