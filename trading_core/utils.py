from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
import requests
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import trading_core.mongodb as db
from .core import config, Const
from .model import model, Symbols, RuntimeBuffer
from .simulator import Simulator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()


def initialise_master_data():
    logging.info(f"JOB: Refresh runtime buffer")
    model.get_handler().refresh_runtime_buffer()


def send_bot_notification(interval):
    logging.info(
        f"Bot notification Job is triggered for interval - {interval}")
    NotifyTelegramBotOrders().send(interval)
    NotifyTelegramBotAlerts().send(interval)
    RuntimeBuffer().buffer_signals.clear()


def send_email_notification(interval):
    logging.info(
        f"Email notification Job is triggered for interval - {interval}")
    NotificationEmail().send(interval)
    RuntimeBuffer().buffer_signals.clear()


class JobScheduler:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_._instance.init()
        return class_._instance

    def init(self) -> None:

        self.__scheduler = BackgroundScheduler()
        self.__scheduler.start()
        self.__localJobs = {}
        self.__initJobs()

        # Init master data during start server
        initialise_master_data()

    def __initJobs(self):
        dbJobs = db.get_jobs()

        for job in dbJobs:
            jobId = str(job['_id'])
            jobType = job['jobType']
            interval = job['interval']

            if jobType == Const.JOB_TYPE_BOT:
                job = self.__scheduler.add_job(
                    send_bot_notification, self.__generateCronTrigger(interval), id=jobId, args=(interval,))
            elif jobType == Const.JOB_TYPE_EMAIL:
                job = self.__scheduler.add_job(
                    send_email_notification, self.__generateCronTrigger(interval), id=jobId, args=(interval,))
            elif jobType == Const.JOB_TYPE_INIT:
                job = self.__scheduler.add_job(
                    initialise_master_data, CronTrigger(day_of_week='mon-fri', hour='2', jitter=60, timezone='UTC'), id=jobId)

            self.__localJobs[jobId] = job

            logging.info(
                f"Job - {jobType} for interval - {interval} is scheduled firstly at {job.next_run_time}")

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

    def createJob(self, jobType, interval):
        if jobType == Const.JOB_TYPE_BOT:
            job = self.__scheduler.add_job(
                send_bot_notification, self.__generateCronTrigger(interval), args=(interval,))
        elif jobType == Const.JOB_TYPE_EMAIL:
            job = self.__scheduler.add_job(
                send_email_notification, self.__generateCronTrigger(interval), args=(interval,))
        elif jobType == Const.JOB_TYPE_INIT:
            job = self.__scheduler.add_job(
                initialise_master_data, CronTrigger(day_of_week='mon-fri', hour='2', jitter=60, timezone='UTC'))
        db.create_job(job.id, jobType, interval)
        self.__localJobs[job.id] = job

        logging.info(
            f"Job - {jobType} for interval - {interval} is scheduled at {job.next_run_time}")

        return job

    def removeJob(self, jobId):
        try:
            self.__scheduler.remove_job(jobId)
        except JobLookupError as error:
            logging.error(error)

        return db.delete_job(jobId)

    def get(self):
        return self.__scheduler

    def getJobs(self):
        jobs = []
        dbJobs = db.get_jobs()

        for dbJob in dbJobs:
            job_id = dbJob['_id']
            for job in self.__localJobs.values():
                if job_id == job.id:
                    job = {'job_id': job_id,
                           'jobType': dbJob['jobType'],
                           'interval': dbJob['interval'],
                           'isActive': dbJob['isActive'],
                           'nextRunTime': self.__localJobs[job_id].next_run_time}

                    jobs.append(job)

        return jobs


class NotificationBase:
    def __init__(self) -> None:
        self.messages = {}
        self.buffer = RuntimeBuffer()

    def send(self):
        pass

    def getSignals(self, symbol, interval, strategies, signalCodes):

        try:
            oSymbol = Symbols(from_buffer=True).get_symbol(symbol)
        except Exception as SymbolError:
            logging.error(SymbolError)
            return []

        if not oSymbol:
            return []

        if not model.get_handler().is_trading_open(interval, oSymbol.tradingTime):
            return []

        signals = Simulator().determineSignals(
            [symbol], [interval], strategies, signalCodes, closedBar=True)

        return signals


class NotificationEmail(NotificationBase):
    def send(self, interval):

        if interval not in [Const.TA_INTERVAL_4H, Const.TA_INTERVAL_1D, Const.TA_INTERVAL_1WK]:
            return

        logging.info(
            f"Email notification for interval - {interval}")

        symbolsCode = []

        # Email configuration
        sender_email = os.getenv("SMTP_USERNAME")
        receiver_email = os.getenv("RECEIVER_EMAIL").split(';')
        subject = f'[TradingTool]: Alert signals for {interval}'

        oSymbols = Symbols(from_buffer=True).get_symbol_list()

        for oSymbol in oSymbols:
            if model.get_handler().is_trading_open(interval, oSymbol.tradingTime):
                symbolsCode.append(oSymbol.code)

        signals = Simulator().determineSignals(symbols=symbolsCode, intervals=[
            interval], signals=[Const.STRONG_BUY, Const.STRONG_SELL], closedBar=True)

        if not signals:
            return

        # Create the HTML table
        table_html = '<table border="1">'
        table_html += '<tr><th>DateTime</th><th>Symbol</th><th>Interval</th><th>Strategy</th><th>Signal</th></tr>'
        for row in signals:
            table_html += '<tr>'
            table_html += f'<td>{row["dateTime"]}</td>'
            table_html += f'<td>{row["symbol"]}</td>'
            table_html += f'<td>{row["interval"]}</td>'
            table_html += f'<td>{row["strategy"]}</td>'
            table_html += f'<td>{row["signal"]}</td>'
            table_html += '</tr>'
        table_html += '</table>'

        # Create the email body as HTML
        message = MIMEText(
            f'<h2>Alert signals for {interval}</h2>{table_html}', 'html')

        # Create a MIME message object
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ', '.join(receiver_email)
        msg['Subject'] = subject
        msg.attach(message)

        # SMTP server configuration
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_username = sender_email
        smtp_password = os.getenv("SMTP_PASSWORD")

        try:
            # Create a secure connection with the SMTP server
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)

            # Send the email
            server.sendmail(sender_email, receiver_email, msg.as_string())
            logging.info(f'Sent email successfully to {receiver_email}!')

        except Exception as e:
            logging.error('An error occurred while sending the email:', str(e))

        finally:
            # Close the SMTP server connection
            server.quit()


class NotifyTelegramBot(NotificationBase):

    def send(self, interval):
        bot_token = os.getenv("BOT_TOKEN")
        bot_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'

        if not bot_token:
            logging.error(
                'Bot token is not maintained in the environment values')

        for channelId, message in self.messages.items():
            params = {'chat_id': channelId,
                      'text': message, 'parse_mode': 'HTML'}
            response = requests.post(bot_url, data=params)
            if response.ok:
                logging.info(f"Send message to chat bot: {channelId}")
            else:
                logging.error(f"Failed to send message: {response.text}")


class NotifyTelegramBotAlerts(NotifyTelegramBot):

    def send(self, interval):
        logging.info(
            f"Alerts Bot notification for interval - {interval}")
        self.getAlertMessages(interval)
        super().send(interval)

    def getAlertMessages(self, interval):

        dbAlerts = db.get_alerts(interval)

        for alert in dbAlerts:
            dbSymbolCode = alert['symbol']
            dbComments = alert['comments'] if 'comments' in alert else None
            dbStrategies = alert['strategies'] if 'strategies' in alert else None
            dbSignals = alert['signals'] if 'signals' in alert else None

            signals = self.getSignals(
                dbSymbolCode, interval, dbStrategies, dbSignals)

            for signal in signals:

                signal_text = f'<b>{signal["signal"]}</b>'
                comments_text = f' | {dbComments}' if dbComments else ''

                message_text = f'{signal["dateTime"]}  -  <b>{signal["symbol"]} - {signal["interval"]}</b>: ({signal["strategy"]}) - {signal_text}{comments_text}\n\n'

                if alert['chatId'] in self.messages:
                    self.messages[alert['chatId']] += message_text
                else:
                    self.messages[alert['chatId']
                                  ] = f'<b>Alert signals for {interval}: \n</b>{message_text}'


class NotifyTelegramBotOrders(NotifyTelegramBot):

    def send(self, interval):
        logging.info(
            f"Orders Bot notification for interval - {interval}")
        self.getOrderMessages(interval)
        super().send(interval)

    def getOrderMessages(self, interval):

        dbOrders = db.get_orders(interval)

        for order in dbOrders:
            dbOrderType = order['type']
            dbSymbolCode = order['symbol']
            dbStrategies = order['strategy'] if 'strategy' in order else None

            signals = self.getSignals(dbSymbolCode, interval, dbStrategies, [])

            for signal in signals:

                signal_value = signal["signal"]
                signal_text = f'<b>{signal_value}</b>'
                comments_text = self.getComments(dbOrderType, signal_value)

                message_text = f'{signal["dateTime"]}  -  <b>{signal["symbol"]} - {signal["interval"]}</b>: ({signal["strategy"]}) - {signal_text}{comments_text}\n'

                if '1658698044' in self.messages:
                    self.messages['1658698044'] += message_text
                else:
                    self.messages['1658698044'] = f'<b>Order signals for {interval}: \n</b>{message_text}'

    def getComments(self, order_type, signal_value):

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
