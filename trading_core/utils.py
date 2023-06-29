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

from .mongodb import MongoJobs, MongoAlerts, MongoOrders
from .core import logger, runtime_buffer, Const
from .model import model, RuntimeBuffer
from .responser import Messages, ResponserEmail, ResponserBot


load_dotenv()


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
            job_id = db_job[Const.DB_ID]

            job_details = {Const.JOB_ID: job_id,
                           Const.DB_JOB_TYPE: db_job[Const.DB_JOB_TYPE],
                           Const.INTERVAL: db_job[Const.DB_INTERVAL],
                           Const.DB_IS_ACTIVE: db_job[Const.DB_IS_ACTIVE]}

            job = runtime_buffer.get_job_from_buffer(job_id)
            if job:
                job_details[Const.DATETIME] = job.next_run_time

            jobs.append(job)

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


class NotifyTelegramBotAlerts(NotificationBot):

    def send(self, interval):
        logger.info(
            f"Alerts Bot notification for interval - {interval}")
        self.getAlertMessages(interval)
        super().send(interval)

    def getAlertMessages(self, interval):
        pass

        # dbAlerts = db.get_alerts(interval)

        # for alert in dbAlerts:
        #     dbSymbolCode = alert['symbol']
        #     dbComments = alert['comments'] if 'comments' in alert else None
        #     dbStrategies = alert['strategies'] if 'strategies' in alert else None
        #     dbSignals = alert['signals'] if 'signals' in alert else None

        #     signals = self.getSignals(
        #         dbSymbolCode, interval, dbStrategies, dbSignals)

        #     for signal in signals:

        #         signal_text = f'<b>{signal["signal"]}</b>'
        #         comments_text = f' | {dbComments}' if dbComments else ''

        #         message_text = f'{signal["dateTime"]}  -  <b>{signal["symbol"]} - {signal["interval"]}</b>: ({signal["strategy"]}) - {signal_text}{comments_text}\n\n'

        #         if alert['chatId'] in self.messages:
        #             self.messages[alert['chatId']] += message_text
        #         else:
        #             self.messages[alert['chatId']
        #                           ] = f'<b>Alert signals for {interval}: \n</b>{message_text}'


class NotifyTelegramBotOrders(NotificationBot):

    def send(self, interval):
        logger.info(
            f"Orders Bot notification for interval - {interval}")
        self.getOrderMessages(interval)
        super().send(interval)

    def getOrderMessages(self, interval):
        pass
        # dbOrders = db.get_orders(interval)

        # for order in dbOrders:
        #     dbOrderType = order['type']
        #     dbSymbolCode = order['symbol']
        #     dbStrategies = order['strategy'] if 'strategy' in order else None

        #     signals = self.getSignals(dbSymbolCode, interval, dbStrategies, [])

        #     for signal in signals:

        #         signal_value = signal["signal"]
        #         signal_text = f'<b>{signal_value}</b>'
        #         comments_text = self.getComments(dbOrderType, signal_value)

        #         message_text = f'{signal["dateTime"]}  -  <b>{signal["symbol"]} - {signal["interval"]}</b>: ({signal["strategy"]}) - {signal_text}{comments_text}\n'

        #         if '1658698044' in self.messages:
        #             self.messages['1658698044'] += message_text
        #         else:
        #             self.messages['1658698044'] = f'<b>Order signals for {interval}: \n</b>{message_text}'

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
