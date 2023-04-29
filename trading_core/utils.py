from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import requests
from dotenv import dotenv_values
import logging

import trading_core.mongodb as db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

config = dotenv_values(".env")


async def send_bot_notification(interval):
    try:
        if not config['BOT_TOKEN']:
            logging.error(
                'Bot token is not maintained in the environment values')
    except KeyError:
        logging.error('Bot token is not maintained in the environment values')

    url = f'https://api.telegram.org/bot{config["BOT_TOKEN"]}/sendMessage'
    params = {'chat_id': '1658698044', 'text': 'Ping'}
    response = requests.post(url, data=params)
    if not response.ok:
        logging.error(f"Failed to send message: {response.text}")


class Scheduler:
    def __init__(self) -> None:
        self.__scheduler = BackgroundScheduler()
        self.__initJobs()

    def __initJobs(self):
        # self.addJob()
        pass

    def addJob(self, interval):
        job = self.__scheduler.add_job(lambda: asyncio.run(send_bot_notification(interval)),
                                       CronTrigger(
                                           hour='0,4,8,12,16,20', minute='2', jitter=60, timezone='UTC')
                                       )
        
        return job
    
    def createJob(self, interval):
        job = self.addJob(interval)
        db.create_job(job, interval)
        return job
    
    def removeJob(self, jobId):
        self.__scheduler.remove_job(jobId)
        return db.delete_job(jobId)

    def get(self):
        return self.__scheduler

    def start(self):
        self.__scheduler.start()
