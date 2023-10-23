import logging
import os
from dotenv import load_dotenv

from flask import Flask, jsonify, request
import telegram

import trading_core.responser as resp
import trading_core.utils as utils

app = Flask(__name__)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logging.error('Bot token is not maintained in the environment values')

HEROKU_APP_NAME = os.getenv('HEROKU_APP_NAME')

# webhook settings
WEBHOOK_HOST = f'https://{HEROKU_APP_NAME}.herokuapp.com'
WEBHOOK_PATH = f'/webhook/{BOT_TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'

# webserver settings
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(os.getenv('PORT'))

bot = telegram.Bot(token=BOT_TOKEN)

scheduler = utils.JobScheduler()


@app.route("/")
def index():
    return "<h1>This is the Trading tool API</h1>"


# ----------------------------------
# Our public Webhook URL
# ----------------------------------
@app.route(WEBHOOK_PATH, methods=['POST'])
def respond():
    # retrieve the message in JSON and then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    chat_id = update.message.chat.id
    msg_id = update.message.message_id

    # Telegram understands UTF-8, so encode text for unicode compatibility
    text = update.message.text.encode('utf-8').decode()
    logging.info(f'BOT: got the message - {text}')

    # response = get_response(text)
    bot.sendMessage(chat_id=chat_id, text=f'Hello {chat_id}')

    return 'ok'


# ----------------------------------
# Our Private to 'set' our webhook URL (you should protect this URL)
# ----------------------------------
@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    s = bot.setWebhook(f'{WEBHOOK_URL}')
    if s:
        logging.info(f'{WEBHOOK_URL} is succesfully activated')
        return f'{WEBHOOK_URL} is succesfully activated'
    else:
        logging.error(f'{WEBHOOK_URL} is failed')
        return f'{WEBHOOK_URL} is failed'


@app.route('/intervals', methods=['GET'])
def getIntervals():
    importance = request.args.get('importance')

    return resp.getIntervals(importance)


@app.route('/symbols', methods=['GET'])
def getSymbols():
    code = request.args.get('code')
    name = request.args.get('name')
    status = request.args.get('status')
    type = request.args.get('type')
    isBuffer = request.args.get('isBuffer')
    isBuffer = True if isBuffer == None else isBuffer

    return resp.getSymbols(code=code, name=name, status=status, type=type, isBuffer=isBuffer)


@app.route('/indicators', methods=['GET'])
def getIndicators():
    return resp.getIndicators()


@app.route('/strategies', methods=['GET'])
def getStrategies():
    return resp.getStrategies()


@app.route('/historyData', methods=['GET'])
def getHistoryData():
    symbol = request.args.get('symbol')
    interval = request.args.get('interval')
    limit = request.args.get('limit')

    return resp.getHistoryData(symbol=symbol, interval=interval, limit=limit)


@app.route('/indicatorData', methods=['GET'])
def getIndicatorData():
    code = request.args.get('code')
    length = int(request.args.get('length'))
    symbol = request.args.get('symbol')
    interval = request.args.get('interval')
    limit = int(request.args.get('limit'))

    return resp.getIndicatorData(code=code, length=length, symbol=symbol, interval=interval, limit=limit)


@app.route('/strategyData', methods=['GET'])
def getStrategyData():
    code = request.args.get('code')
    symbol = request.args.get('symbol')
    interval = request.args.get('interval')
    limit = int(request.args.get('limit'))

    return resp.getStrategyData(code=code, symbol=symbol, interval=interval, limit=limit)


@app.route('/signals', methods=['GET'])
def getSignals():
    symbols = request.args.getlist('symbol', None)
    intervals = request.args.getlist('interval', None)
    codes = request.args.getlist('code', None)
    closedBar = bool(request.args.get('closedBar', '').lower() == 'true')

    if symbols == []:
        return jsonify({"error": "Symbol is missed", }), 500

    return resp.getSignals(symbols, intervals, codes, closedBar)


@app.route('/simulate', methods=['GET'])
def getSimulate():
    symbols = request.args.getlist('symbol', None)
    intervals = request.args.getlist('interval', None)
    codes = request.args.getlist('code', None)

    if symbols == []:
        return jsonify({"error": "Symbol is missed", }), 500

    return resp.getSimulate(symbols, intervals, codes)


@app.route('/simulations', methods=['GET'])
def getSimulations():
    symbols = request.args.getlist('symbol', None)
    intervals = request.args.getlist('interval', None)
    codes = request.args.getlist('code', None)

    return resp.getSimulations(symbols, intervals, codes)


@app.route('/signalsBySimulation', methods=['GET'])
def getSignalsBySimulation():
    symbols = request.args.getlist('symbol', None)
    intervals = request.args.getlist('interval', None)
    codes = request.args.getlist('code', None)

    return resp.getSignalsBySimulation(symbols, intervals, codes)

# Define endpoints for creating, reading, updating, and deleting background jobs


@app.route('/jobs', methods=['POST'])
def create_job():
    jobType = request.json.get('jobType')
    interval = request.json.get('interval')
    job = scheduler.createJob(jobType, interval)
    return jsonify({'job_id': job.id}), 201


@app.route('/jobs', methods=['GET'])
def get_jobs():
    jobs = scheduler.getJobs()
    if jobs:
        return jsonify(jobs), 200
    else:
        return jsonify({'error': 'Jobs not found'}), 404


@app.route('/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    pass
    # job = jobs.get(job_id)
    # if job:
    #     return jsonify({'job_id': job_id, 'interval': job.trigger.fields_as_string()}), 200
    # else:
    #     return jsonify({'error': 'Job not found'}), 404


@app.route('/jobs/<job_id>', methods=['PUT'])
def update_job(job_id):
    pass
    # job = jobs.get(job_id)
    # if job:
    #     interval = request.json.get('interval')
    #     job.reschedule(trigger='interval', **interval)
    #     return jsonify({'job_id': job_id, 'interval': job.trigger.fields_as_string()}), 200
    # else:
    #     return jsonify({'error': 'Job not found'}), 404


@app.route('/jobs/<job_id>', methods=['DELETE'])
def delete_job(job_id):
    if scheduler.removeJob(job_id):
        return jsonify({'message': 'Job deleted'}), 200
    else:
        return jsonify({'error': 'Job not found'}), 404


@app.route("/logs")
def get_logs():
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    return resp.getLogs(start_date_str, end_date_str)
