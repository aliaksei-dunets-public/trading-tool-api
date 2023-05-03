from flask import Flask, jsonify, request

import trading_core.responser as resp
import trading_core.utils as utils

app = Flask(__name__)
# api = Api(app, version='1.0', title='Trading Tool API', description='Trading Tool API for getting symbols, history data, indicators, signals, simulations')

scheduler = utils.JobScheduler()

@app.route("/")
def index():
    return "<h1>This is the Trading tool API</h1>"


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

    if symbols == []:
        return jsonify({"error": "Symbol is missed", }), 500

    return resp.getSignals(symbols, intervals, codes)


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
    interval = request.json.get('interval')
    job = scheduler.createJob(interval)
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
