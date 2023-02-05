from flask import Flask, jsonify, request

import trading_core.responser as resp

app = Flask(__name__)


@app.route("/")
def index():
    return "<h1>Hello World</h1>"

@app.route('/intervals', methods=['GET'])
def getIntervals():
    return resp.ResponseInterval().getIntervals()

@app.route('/symbols', methods=['GET'])
def getSymbols():
    code = request.args.get('code')
    name = request.args.get('name')
    status = request.args.get('status')
    type = request.args.get('type')

    return resp.ResponseSymbol().getSymbols(code=code,name=name, status=status, type=type)

@app.route('/historyData', methods=['GET'])
def getHistoryData():
    symbol = request.args.get('symbol')
    interval = request.args.get('interval')
    limit = request.args.get('limit')

    return resp.ResponseHistoryData().getData(symbol=symbol, interval=interval, limit=limit)

