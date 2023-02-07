from flask import Flask, jsonify, request

import trading_core.responser as resp

app = Flask(__name__)


@app.route("/")
def index():
    return "<h1>Hello World</h1>"


@app.route('/intervals', methods=['GET'])
def getIntervals():
    return resp.getIntervals()


@app.route('/symbols', methods=['GET'])
def getSymbols():
    code = request.args.get('code')
    name = request.args.get('name')
    status = request.args.get('status')
    type = request.args.get('type')

    return resp.getSymbols(code=code, name=name, status=status, type=type)

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

    return resp.getIndicatorData(code=code,length=length, symbol=symbol, interval=interval, limit=limit)

@app.route('/strategyData', methods=['GET'])
def getStrategyData():
    code = request.args.get('code')
    symbol = request.args.get('symbol')
    interval = request.args.get('interval')
    limit = int(request.args.get('limit'))

    return resp.getStrategyData(code=code, symbol=symbol, interval=interval, limit=limit)
