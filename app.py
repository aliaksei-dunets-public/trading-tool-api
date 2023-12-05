from flask import Flask, jsonify, request
import pandas as pd
import bson.json_util as json_util

import bot as Bot
from trading_core.core import logger
from trading_core.constants import Const
from trading_core.responser import (
    ResponserWeb,
    ParamSimulationList,
    ParamSymbolIntervalLimit,
    SimulateOptions,
    UserHandler,
    job_func_initialise_runtime_data,
    JobScheduler,
)
from trading_core.common import (
    BaseModel,
    UserModel,
    TraderModel,
    SessionModel,
    BalanceModel,
    OrderModel,
    OrderOpenModel,
    TransactionModel,
    TradingType,
    SessionType,
    StrategyType,
)

from trading_core.robot import SessionManager

app = Flask(__name__)

responser = ResponserWeb()

# Initialize runtime buffer
job_func_initialise_runtime_data()
# Initialize Job Scheduler
JobScheduler()


######################### User #############################
@app.route("/user/<id>", methods=["GET"])
def get_user(id):
    return responser.get_user(id)


@app.route("/user", methods=["GET"])
def get_user_by_email():
    user_email = request.headers.get("User-Email")
    return responser.get_user_by_email(user_email)


@app.route("/users", methods=["GET"])
def get_users():
    search = request.args.get("search")
    return responser.get_users(search)


@app.route("/user", methods=["POST"])
def create_user():
    user_data = request.get_json()
    user_model = UserModel(**user_data)
    return responser.create_user(user_model)


@app.route("/user/<user_id>", methods=["PATCH"])
def update_user(user_id):
    user_data = request.get_json()
    return responser.update_user(id=user_id, query=user_data)


@app.route("/user/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    return responser.delete_user(id=user_id)


######################### Trader ###########################
@app.route("/trader/<id>", methods=["GET"])
def get_trader(id):
    return responser.get_trader(id)


@app.route("/traders", methods=["GET"])
def get_traders():
    user_email = request.headers.get("User-Email")
    return responser.get_traders(user_email)


@app.route("/trader", methods=["POST"])
def create_trader():
    trader_data = request.get_json()
    trader_model = TraderModel(**trader_data)
    return responser.create_trader(trader_model)


@app.route("/trader/<trader_id>", methods=["PATCH"])
def update_trader(trader_id):
    trader_data = request.get_json()
    return responser.update_trader(id=trader_id, query=trader_data)


@app.route("/trader/<trader_id>", methods=["DELETE"])
def delete_trader(trader_id):
    return responser.delete_trader(trader_id)


@app.route("/trader_status/<trader_id>", methods=["GET"])
def check_trader_status(trader_id):
    return responser.check_trader_status(id=trader_id)


@app.route("/trader_accounts/<trader_id>", methods=["GET"])
def get_account_info(trader_id):
    return responser.get_account_info(trader_id)


@app.route("/trader_leverages/<trader_id>", methods=["GET"])
def get_leverage_settings(trader_id):
    symbol = request.args.get("symbol", None)
    return responser.get_leverage_settings(trader_id=trader_id, symbol=symbol)


######################### Session ###########################
@app.route("/session/<id>", methods=["GET"])
def get_session(id):
    return responser.get_session(id)


@app.route("/session/<id>/leverages", methods=["GET"])
def get_session_leverages(id):
    return responser.get_session_leverages(id)


@app.route("/sessions", methods=["GET"])
def get_sessions():
    user_email = request.headers.get("User-Email")
    return responser.get_sessions(user_email)


@app.route("/session", methods=["POST"])
def create_session():
    session_data = request.get_json()
    session_model = SessionModel(**session_data)
    return responser.create_session(session_model)


@app.route("/session/<session_id>/activate", methods=["POST"])
def activate_session(session_id):
    return responser.activate_session(session_id)


@app.route("/session/<session_id>/inactivate", methods=["POST"])
def stop_session(session_id):
    return responser.inactivate_session(session_id)


@app.route("/session/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    return responser.delete_session(session_id)


######################### Balance ###########################
@app.route("/balance/<id>", methods=["GET"])
def get_balance(id):
    return responser.get_balance(id)


@app.route("/balances", methods=["GET"])
def get_balances():
    session_id = request.args.get("session_id")
    return responser.get_balances(session_id)


@app.route("/balance", methods=["POST"])
def create_balance():
    balance_data = request.get_json()
    balance_model = BalanceModel(**balance_data)
    return responser.create_balance(balance_model)


######################### Order ###########################
@app.route("/order/<id>", methods=["GET"])
def get_order(id):
    return responser.get_order(id)


@app.route("/orders", methods=["GET"])
def get_orders():
    session_id = request.args.get("session_id")
    return responser.get_orders(session_id)


@app.route("/order", methods=["POST"])
def create_order():
    order_data = request.get_json()
    order_model = OrderModel(**order_data)
    return responser.create_order(order_model)


######################### Leverage ###########################
@app.route("/leverage/<id>", methods=["GET"])
def get_leverage(id):
    return responser.get_leverage(id)


@app.route("/leverages", methods=["GET"])
def get_leverages():
    session_id = request.args.get("session_id")
    return responser.get_leverages(session_id)


@app.route("/leverage", methods=["POST"])
def create_leverage():
    open_data = request.get_json()
    open_mdl = OrderOpenModel(**open_data)
    return responser.create_leverage(
        session_id=open_data[Const.DB_SESSION_ID], open_mdl=open_mdl
    )


@app.route("/leverage/<id>/close", methods=["POST"])
def close_leverage(id):
    return responser.close_leverage(leverage_id=id)


######################### Transaction ###########################
@app.route("/transaction/<id>", methods=["GET"])
def get_transaction(id):
    return responser.get_transaction(id)


@app.route("/transactions", methods=["GET"])
def get_transactions():
    order_id = request.args.get("order_id")
    return responser.get_transactions(order_id)


@app.route("/transaction", methods=["POST"])
def create_transaction():
    transaction_data = request.get_json()
    transaction_model = TransactionModel(**transaction_data)
    return responser.create_transaction(transaction_model)


########################### Legacy code ####################################


# ----------------------------------
# Telegram Webhook functionality
# ----------------------------------
@app.route(Bot.WEBHOOK_PATH, methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = Bot.telebot.types.Update.de_json(json_string)
        Bot.bot.process_new_updates([update])
        return ""
    else:
        return jsonify({"error": "Telegram Bot response is failed"}), 404


@app.route("/getwebhookinfo", methods=["GET"])
def get_webhook_info():
    return jsonify(Bot.get_webhook_info())


@app.route("/setwebhook", methods=["GET", "POST"])
def set_webhook():
    return Bot.set_webhook()


@app.route("/removewebhook", methods=["GET", "POST"])
def remove_webhook():
    return Bot.remove_webhook()


# ----------------------------------
# Telegram Webhook functionality
# ----------------------------------


@app.after_request
def add_content_type(response):
    response.headers["Content-Type"] = "application/json"
    return response


@app.route("/")
def index():
    return "<h1>This is the Trading tool API</h1>"


@app.route("/intervals", methods=["GET"])
def get_intervals():
    importances = request.args.getlist(Const.IMPORTANCE, None)
    return responser.get_intervals(importances=importances)


@app.route("/symbols", methods=["GET"])
def get_symbols():
    trader_id = request.args.get(Const.DB_TRADER_ID, None)
    symbol = request.args.get(Const.DB_SYMBOL, None)
    name = request.args.get(Const.DB_NAME, None)
    status = request.args.get(Const.DB_STATUS, None)
    type = request.args.get(Const.DB_TYPE, None)
    currency = request.args.get(Const.DB_CURRENCY, None)

    return responser.get_symbol_list(
        trader_id=trader_id,
        symbol=symbol,
        name=name,
        status=status,
        type=type,
        currency=currency,
    )


@app.route("/indicators", methods=["GET"])
def get_indicators():
    return responser.get_indicators()


@app.route("/strategies", methods=["GET"])
def get_strategies():
    return responser.get_strategies()


@app.route("/historyData", methods=["GET"])
def get_history_data():
    symbol = request.args.get("symbol")
    interval = request.args.get("interval")
    limit = int(request.args.get("limit"))
    from_buffer = responser.get_param_bool(request.args.get("from_buffer", "false"))
    closed_bars = responser.get_param_bool(request.args.get("closed_bars", "false"))

    return responser.get_history_data(
        symbol=symbol,
        interval=interval,
        limit=limit,
        from_buffer=from_buffer,
        closed_bars=closed_bars,
    )


@app.route("/strategyData", methods=["GET"])
def get_strategy_data():
    code = request.args.get("code")
    symbol = request.args.get("symbol")
    interval = request.args.get("interval")
    limit = int(request.args.get("limit"))
    from_buffer = responser.get_param_bool(request.args.get("from_buffer", "false"))
    closed_bars = responser.get_param_bool(request.args.get("closed_bars", "false"))

    return responser.get_strategy_data(
        code=code,
        symbol=symbol,
        interval=interval,
        limit=limit,
        from_buffer=from_buffer,
        closed_bars=closed_bars,
    )


@app.route("/signals", methods=["GET"])
def get_signals():
    symbols = request.args.getlist("symbol", None)
    intervals = request.args.getlist("interval", None)
    strategies = request.args.getlist("strategy", None)
    signals_config = request.args.getlist("signal", None)
    closed_bars = responser.get_param_bool(request.args.get("closed_bars", "false"))

    return responser.get_signals(
        symbols=symbols,
        intervals=intervals,
        strategies=strategies,
        signals_config=signals_config,
        closed_bars=closed_bars,
    )


@app.route("/jobs", methods=["GET"])
def get_jobs():
    return responser.get_jobs()


@app.route("/job_status", methods=["GET"])
def get_job_status():
    return responser.get_job_status()


# Define endpoints for creating, reading, updating, and deleting background jobs
@app.route("/jobs", methods=["POST"])
def create_job():
    job_type = request.json.get(Const.DB_JOB_TYPE)
    interval = request.json.get(Const.DB_INTERVAL)
    return responser.create_job(job_type=job_type, interval=interval)


@app.route("/jobs/<job_id>/activate", methods=["POST"])
def activate_job(job_id):
    return responser.activate_job(job_id)


@app.route("/jobs/<job_id>/deactivate", methods=["POST"])
def deactivate_job(job_id):
    return responser.deactivate_job(job_id)


@app.route("/jobs/<job_id>", methods=["DELETE"])
def remove_jobs(job_id):
    return responser.remove_job(job_id)


@app.route("/alerts", methods=["GET"])
def get_alerts():
    alert_type = request.args.get(Const.DB_ALERT_TYPE)
    symbol = request.args.get(Const.DB_SYMBOL)
    interval = request.args.get(Const.DB_INTERVAL)

    return responser.get_alerts(alert_type=alert_type, symbol=symbol, interval=interval)


@app.route("/alerts", methods=["POST"])
def create_alert():
    alert_type = request.json.get(Const.DB_ALERT_TYPE)
    channel_id = request.json.get(Const.DB_CHANNEL_ID)
    symbol = request.json.get(Const.DB_SYMBOL)
    interval = request.json.get(Const.DB_INTERVAL)
    strategies = request.json.get(Const.DB_STRATEGIES)
    signals = request.json.get(Const.DB_SIGNALS)
    comment = request.json.get(Const.DB_COMMENT)

    return responser.create_alert(
        alert_type=alert_type,
        channel_id=channel_id,
        symbol=symbol,
        interval=interval,
        strategies=strategies,
        signals=signals,
        comment=comment,
    )


@app.route("/alerts/<_id>", methods=["PUT"])
def update_alert(_id):
    interval = request.json.get(Const.DB_INTERVAL)
    strategies = request.json.get(Const.DB_STRATEGIES)
    signals = request.json.get(Const.DB_SIGNALS)
    comment = request.json.get(Const.DB_COMMENT)

    return responser.update_alert(
        id=_id,
        interval=interval,
        strategies=strategies,
        signals=signals,
        comment=comment,
    )


@app.route("/alerts/<_id>", methods=["DELETE"])
def remove_alert(_id):
    return responser.remove_alert(_id)


# @app.route("/orders", methods=["GET"])
# def get_orders():
#     symbol = request.args.get(Const.DB_SYMBOL)
#     interval = request.args.get(Const.DB_INTERVAL)

#     return responser.get_orders(symbol=symbol, interval=interval)


# @app.route("/orders", methods=["POST"])
# def create_order():
#     order_type = request.json.get(Const.DB_ORDER_TYPE)
#     open_date_time = request.json.get(Const.DB_OPEN_DATE_TIME)
#     symbol = request.json.get(Const.DB_SYMBOL)
#     interval = request.json.get(Const.DB_INTERVAL)
#     price = request.json.get(Const.DB_PRICE)
#     quantity = request.json.get(Const.DB_QUANTITY)
#     strategies = request.json.get(Const.DB_STRATEGIES)

#     return responser.create_order(
#         order_type=order_type,
#         open_date_time=open_date_time,
#         symbol=symbol,
#         interval=interval,
#         price=price,
#         quantity=quantity,
#         strategies=strategies,
#     )


# @app.route("/orders/<_id>", methods=["DELETE"])
# def remove_order(_id):
#     return responser.remove_order(_id)


@app.route("/simulations", methods=["GET"])
def get_simulations():
    symbols = request.args.getlist("symbol", None)
    intervals = request.args.getlist("interval", None)
    strategies = request.args.getlist("strategy", None)

    return responser.get_simulations(
        symbols=symbols, intervals=intervals, strategies=strategies
    )


@app.route("/simulate", methods=["GET"])
def get_simulate():
    symbols = request.args.getlist("symbol", None)
    intervals = request.args.getlist("interval", None)
    strategies = request.args.getlist("strategy", None)
    init_balance = request.args.get(Const.SRV_INIT_BALANCE)
    limit = request.args.get(Const.LIMIT)
    stop_loss_rate = request.args.get(Const.SRV_STOP_LOSS_RATE)
    take_profit_rate = request.args.get(Const.SRV_TAKE_PROFIT_RATE)
    fee_rate = request.args.get(Const.SRV_FEE_RATE)

    try:
        simulate_options = SimulateOptions(
            init_balance=init_balance,
            limit=limit,
            stop_loss_rate=stop_loss_rate,
            take_profit_rate=take_profit_rate,
            fee_rate=fee_rate,
        )

        params = ParamSimulationList(
            symbols=symbols,
            intervals=intervals,
            strategies=strategies,
            simulation_options_list=[simulate_options],
        )

    except Exception as error:
        return jsonify({"error": error}), 500

    return responser.get_simulate(params)


@app.route("/history_simulation", methods=["GET"])
def get_history_simulation():
    trader_id = request.args.get("trader_id", None)
    trading_type = request.args.get("trading_type", None)
    symbol = request.args.get("symbol", None)
    interval = request.args.get("interval", "5m")
    strategy = request.args.get("strategy", StrategyType.CCI_20_TREND_100)
    stop_loss_rate = request.args.get(Const.SRV_STOP_LOSS_RATE, 0)
    is_trailing_stop = responser.get_param_bool(
        request.args.get(Const.SRV_IS_TRAILING_STOP_LOSS, "false")
    )
    take_profit_rate = request.args.get(Const.SRV_TAKE_PROFIT_RATE, 0)

    try:
        user_email = request.headers.get("User-Email")
        user_data = UserHandler().get_user_by_email(user_email)

        session_data = {
            "trader_id": trader_id,
            "user_id": user_data.id,
            # "status": "",
            "trading_type": trading_type,
            "session_type": SessionType.HISTORY,
            "symbol": symbol,
            "interval": interval,
            "strategy": strategy,
            "take_profit_rate": take_profit_rate,
            "stop_loss_rate": stop_loss_rate,
            "is_trailing_stop": is_trailing_stop,
        }

        session_mdl = SessionModel(**session_data)
        session_mng = SessionManager(session_mdl)
        session_mng.run()

        balance_mdl = session_mng.get_balance_manager().get_balance_model()
        posistions = [item.model_dump() for item in session_mng.get_positions()]

        session_response = session_mdl.model_dump()
        session_response["balance"] = balance_mdl.model_dump()
        session_response["positions"] = posistions

        response = [session_response]

    except Exception as error:
        return jsonify({"error": error}), 500

    return jsonify(response), 200


@app.route("/create_simulations", methods=["POST"])
def create_simulations():
    pass


@app.route("/delete_simulations", methods=["POST"])
def delete_simulations():
    pass


@app.route("/dashboard", methods=["GET"])
def get_dashboard():
    symbol = request.json.get(Const.DB_SYMBOL)
    return responser.get_dashboard(symbol=symbol)


@app.route("/trend", methods=["GET"])
def get_trend():
    symbol = request.args.get("symbol", None)
    interval = request.args.get("interval", None)
    limit = int(request.args.get(Const.LIMIT))

    try:
        param = ParamSymbolIntervalLimit(
            symbol=symbol, interval=interval, limit=limit, consistency_check=False
        )

    except Exception as error:
        return jsonify({"error": error}), 500

    return responser.get_trend(param)


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
#     return responser.getLogs(start_date_str, end_date_str)

# @app.route('/signalsBySimulation', methods=['GET'])
# def getSignalsBySimulation():
#     symbols = request.args.getlist('symbol', None)
#     intervals = request.args.getlist('interval', None)
#     codes = request.args.getlist('code', None)

#     return responser.getSignalsBySimulation(symbols, intervals, codes)
