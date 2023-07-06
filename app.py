from flask import Flask, request

from trading_core.constants import Const
from trading_core.responser import ResponserWeb, job_func_initialise_runtime_data, JobScheduler

app = Flask(__name__)

responser = ResponserWeb()


@app.route("/")
def index():
    return "<h1>This is the Trading tool API</h1>"


@app.after_request
def add_content_type(response):
    response.headers['Content-Type'] = 'application/json'
    return response


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
    from_buffer = responser.get_param_bool(
        request.args.get('from_buffer', 'false'))

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
    from_buffer = responser.get_param_bool(
        request.args.get('from_buffer', 'false'))
    closed_bars = responser.get_param_bool(
        request.args.get('closed_bars', 'false'))

    return responser.get_history_data(symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)


@app.route('/strategyData', methods=['GET'])
def get_strategy_data():
    code = request.args.get('code')
    symbol = request.args.get('symbol')
    interval = request.args.get('interval')
    limit = int(request.args.get('limit'))
    from_buffer = responser.get_param_bool(
        request.args.get('from_buffer', 'false'))
    closed_bars = responser.get_param_bool(
        request.args.get('closed_bars', 'false'))

    return responser.get_strategy_data(code=code, symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)


@app.route('/signals', methods=['GET'])
def get_signals():
    symbols = request.args.getlist('symbol', None)
    intervals = request.args.getlist('interval', None)
    strategies = request.args.getlist('strategy', None)
    signals_config = request.args.getlist('signal', None)
    closed_bars = responser.get_param_bool(
        request.args.get('closed_bars', 'false'))

    return responser.get_signals(symbols=symbols, intervals=intervals, strategies=strategies, signals_config=signals_config, closed_bars=closed_bars)


@app.route('/jobs', methods=['GET'])
def get_jobs():
    return responser.get_jobs()


@app.route('/jobs', methods=['POST'])
def create_job():
    job_type = request.json.get(Const.DB_JOB_TYPE)
    interval = request.json.get(Const.DB_INTERVAL)
    return responser.create_job(job_type=job_type, interval=interval)


@app.route('/jobs/<job_id>/activate', methods=['POST'])
def activate_job(job_id):
    return responser.activate_job(job_id)


@app.route('/jobs/<job_id>/deactivate', methods=['POST'])
def deactivate_job(job_id):
    return responser.deactivate_job(job_id)


@app.route('/jobs/<job_id>', methods=['DELETE'])
def remove_jobs(job_id):
    return responser.remove_job(job_id)


@app.route('/alerts', methods=['GET'])
def get_alerts():
    alert_type = request.args.get(Const.DB_ALERT_TYPE)
    symbol = request.args.get(Const.DB_SYMBOL)
    interval = request.args.get(Const.DB_INTERVAL)

    return responser.get_alerts(alert_type=alert_type,
                                symbol=symbol,
                                interval=interval)


@app.route('/alerts', methods=['POST'])
def create_alert():
    alert_type = request.json.get(Const.DB_ALERT_TYPE)
    channel_id = request.json.get(Const.DB_CHANNEL_ID)
    symbol = request.json.get(Const.DB_SYMBOL)
    interval = request.json.get(Const.DB_INTERVAL)
    strategies = request.json.get(Const.DB_STRATEGIES)
    signals = request.json.get(Const.DB_SIGNALS)
    comment = request.json.get(Const.DB_COMMENT)

    return responser.create_alert(alert_type=alert_type,
                                  channel_id=channel_id,
                                  symbol=symbol,
                                  interval=interval,
                                  strategies=strategies,
                                  signals=signals,
                                  comment=comment
                                  )


@app.route('/alerts/<_id>', methods=['PUT'])
def update_alert(_id):
    interval = request.json.get(Const.DB_INTERVAL)
    strategies = request.json.get(Const.DB_STRATEGIES)
    signals = request.json.get(Const.DB_SIGNALS)
    comment = request.json.get(Const.DB_COMMENT)

    return responser.update_alert(id=_id,
                                  interval=interval,
                                  strategies=strategies,
                                  signals=signals,
                                  comment=comment
                                  )


@app.route('/alerts/<_id>', methods=['DELETE'])
def remove_alert(_id):
    return responser.remove_alert(_id)


@app.route('/orders', methods=['GET'])
def get_orders():
    symbol = request.args.get(Const.DB_SYMBOL)
    interval = request.args.get(Const.DB_INTERVAL)

    return responser.get_orders(symbol=symbol,
                                interval=interval)


@app.route('/orders', methods=['POST'])
def create_order():
    order_type = request.json.get(Const.DB_ORDER_TYPE)
    open_date_time = request.json.get(Const.DB_OPEN_DATE_TIME)
    symbol = request.json.get(Const.DB_SYMBOL)
    interval = request.json.get(Const.DB_INTERVAL)
    price = request.json.get(Const.DB_PRICE)
    quantity = request.json.get(Const.DB_QUANTITY)
    strategies = request.json.get(Const.DB_STRATEGIES)

    return responser.create_order(order_type=order_type,
                                  open_date_time=open_date_time,
                                  symbol=symbol,
                                  interval=interval,
                                  price=price,
                                  quantity=quantity,
                                  strategies=strategies)


@app.route('/orders/<_id>', methods=['DELETE'])
def remove_order(_id):
    return responser.remove_order(_id)


@app.route('/dashboard', methods=['GET'])
def get_dashboard():
    symbol = request.json.get(Const.DB_SYMBOL)
    return responser.get_dashboard(symbol=symbol)


# @app.route('/simulate', methods=['GET'])
# def getSimulate():
#     symbols = request.args.getlist('symbol', None)
#     intervals = request.args.getlist('interval', None)
#     codes = request.args.getlist('code', None)

#     if symbols == []:
#         return jsonify({"error": "Symbol is missed", }), 500

#     return resp.getSimulate(symbols, intervals, codes)


# @app.route('/simulations', methods=['GET'])
# def getSimulations():
#     symbols = request.args.getlist('symbol', None)
#     intervals = request.args.getlist('interval', None)
#     codes = request.args.getlist('code', None)

#     return resp.getSimulations(symbols, intervals, codes)


# @app.route('/signalsBySimulation', methods=['GET'])
# def getSignalsBySimulation():
#     symbols = request.args.getlist('symbol', None)
#     intervals = request.args.getlist('interval', None)
#     codes = request.args.getlist('code', None)

#     return resp.getSignalsBySimulation(symbols, intervals, codes)

# @app.route("/logs")
# def get_logs():
#     start_date_str = request.args.get("start_date")
#     end_date_str = request.args.get("end_date")
#     return resp.getLogs(start_date_str, end_date_str)
