from flask import Flask, jsonify, request

from trading_core.core import Const
import trading_core.responser as resp
import trading_core.utils as utils

from trading_core.responser import ResponserWeb

app = Flask(__name__)

scheduler = utils.JobScheduler()
responser = ResponserWeb()


@app.route("/")
def index():
    return "<h1>This is the Trading tool API</h1>"


@app.route('/intervals', methods=['GET'])
def get_intervals():
    importances = request.args.getlist(Const.IMPORTANCE, None)
    return responser.get_intervals(importances=importances)


@app.route('/symbols', methods=['GET'])
def get_symbols():
    code = request.args.get('code')
    name = request.args.get('name')
    status = request.args.get('status')
    type = request.args.get('type')
    from_buffer = responser.get_param_bool(request.args.get('from_buffer', 'false'))

    return responser.get_symbol_list(code=code, name=name, status=status, type=type, from_buffer=from_buffer)


@app.route('/indicators', methods=['GET'])
def get_indicators():
    return responser.get_indicators()


@app.route('/strategies', methods=['GET'])
def get_strategies():
    return responser.get_strategies()


@app.route('/historyData', methods=['GET'])
def get_history_data():
    symbol = request.args.get('symbol')
    interval = request.args.get('interval')
    limit = int(request.args.get('limit'))
    from_buffer = responser.get_param_bool(request.args.get('from_buffer', 'false'))
    closed_bars = responser.get_param_bool(request.args.get('closed_bars', 'false'))

    return responser.get_history_data(symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)


@app.route('/strategyData', methods=['GET'])
def get_strategy_data():
    code = request.args.get('code')
    symbol = request.args.get('symbol')
    interval = request.args.get('interval')
    limit = int(request.args.get('limit'))
    from_buffer = responser.get_param_bool(request.args.get('from_buffer', 'false'))
    closed_bars = responser.get_param_bool(request.args.get('closed_bars', 'false'))

    return responser.get_strategy_data(code=code, symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)


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
