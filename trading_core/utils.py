from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger
import asyncio
import requests
import os
from dotenv import load_dotenv
import logging

import trading_core.mongodb as db
from .model import config
from .simulator import Simulator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()


def send_bot_notification(interval):

    logging.info(f"Bot notification Job is triggered for interval - {interval}")

    responses = {}

    bot_token = os.getenv("BOT_TOKEN")
    bot_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'

    if not bot_token:
        logging.error('Bot token is not maintained in the environment values')

    dbAlerts = db.get_alerts(interval)

    symbols = set(map(lambda x: x['symbol'], dbAlerts))

    signals = Simulator().determineSignals(list(symbols), [interval])

    for alert in dbAlerts:
        for signal in signals:
            if alert['symbol'] == signal['symbol'] and alert['interval'] == signal['interval']:
                signal_text = f'{signal["dateTime"]}  -  <b>{signal["symbol"]} - {signal["interval"]}</b>: ({signal["strategy"]}) - <b>{signal["signal"]}</b>\n'
                if alert['chatId'] in responses:
                    responses[alert['chatId']] += signal_text
                else:
                    responses[alert['chatId']] = signal_text

    for chatId, message in responses.items():
        params = {'chat_id': chatId, 'text': message, 'parse_mode': 'HTML'}
        response = requests.post(bot_url, data=params)
        if response.ok:
            logging.info(f"Send message: {response.text} to chat: {chatId}")
        else:
            logging.error(f"Failed to send message: {response.text}")


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

    def __initJobs(self):
        dbJobs = db.get_jobs()

        for job in dbJobs:
            jobId = str(job['_id'])
            interval = job['interval']

            job = self.__scheduler.add_job(send_bot_notification, self.__generateCronTrigger(interval), id=jobId, args=(interval,))

            self.__localJobs[jobId] = job

    def __generateCronTrigger(self, interval) -> CronTrigger:
        day_of_week = None
        hour = None
        minute = None
        second = None

        day_of_week = 'mon-fri'

        if interval == config.TA_INTERVAL_5M:
            minute = '*/5'
            second = '30'
        elif interval == config.TA_INTERVAL_15M:
            minute = '*/15'
            second = '30'
        elif interval == config.TA_INTERVAL_30M:
            minute = '*/30'
            second = '59'
        elif interval == config.TA_INTERVAL_1H:
            hour = '*'
            minute = '1'
        elif interval == config.TA_INTERVAL_4H:
            hour = '0,4,8,12,16,20'
            minute = '2'
        elif interval == config.TA_INTERVAL_1D:
            hour = '10'
        elif interval == config.TA_INTERVAL_1WK:
            day_of_week = 'mon'
            hour = '10'
        else:
            Exception('Incorrect interval for subscription')

        return CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute, second=second, jitter=60, timezone='UTC')

    def createJob(self, interval):
        job = self.__scheduler.add_job(send_bot_notification, self.__generateCronTrigger(interval), args=(interval,))
        db.create_job(job.id, interval)
        self.__localJobs[job.id] = job
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
                           'interval': dbJob['interval'],
                           'isActive': dbJob['isActive'],
                           'nextRunTime': self.__localJobs[job_id].next_run_time }

                    jobs.append(job)

        return jobs
