from flask import Flask, jsonify, request
import pandas as pd
import bson.json_util as json_util

import bot as Bot
from trading_core.core import logger
from trading_core.constants import Const
from trading_core.responser import (
    ResponserWeb,
    UserHandler,
    job_func_initialise_runtime_data,
    JobScheduler,
)
from trading_core.common import (
    HistoryDataParamModel,
    StrategyParamModel,
    TraderSymbolIntervalLimitModel,
    TransactionModel,
    UserModel,
    ChannelModel,
    AlertModel,
    TraderModel,
    SessionModel,
    BalanceModel,
    OrderModel,
    OrderOpenModel,
    TransactionModel,
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


######################### Channel ###########################
@app.route("/channels", methods=["GET"])
def get_channels():
    user_email = request.headers.get("User-Email")
    return responser.get_channels(user_email)


@app.route("/channel", methods=["POST"])
def create_channel():
    channel_data = request.get_json()
    channel_model = ChannelModel(**channel_data)
    return responser.create_channel(channel_model)


@app.route("/channel/<channel_id>", methods=["PATCH"])
def update_channel(channel_id):
    channel_data = request.get_json()
    return responser.update_channel(id=channel_id, query=channel_data)


@app.route("/channel/<channel_id>", methods=["DELETE"])
def delete_channel(channel_id):
    return responser.delete_channel(channel_id)


######################### Alert ###########################
@app.route("/alerts", methods=["GET"])
def get_alerts():
    user_email = request.headers.get("User-Email")
    return responser.get_alerts(user_email)


@app.route("/alert", methods=["POST"])
def create_alert():
    alert_data = request.get_json()
    alert_model = AlertModel(**alert_data)
    return responser.create_alert(alert_model)


@app.route("/alert/<alert_id>", methods=["PATCH"])
def update_alert(alert_id):
    alert_data = request.get_json()
    return responser.update_alert(alert_id=alert_id, query=alert_data)


@app.route("/alert/<alert_id>", methods=["DELETE"])
def delete_alert(alert_id):
    return responser.delete_alert(alert_id)


######################### Trader ###########################
@app.route("/trader/<id>", methods=["GET"])
def get_trader(id):
    return responser.get_trader(id)


@app.route("/traders", methods=["GET"])
def get_traders():
    user_email = request.headers.get("User-Email")
    status = request.args.get("status", None)
    return responser.get_traders(user_email=user_email, status=status)


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
def get_accounts(trader_id):
    return responser.get_accounts(trader_id)


@app.route("/trader_leverages/<trader_id>", methods=["GET"])
def get_leverage_settings(trader_id):
    symbol = request.args.get("symbol", None)
    return responser.get_leverage_settings(trader_id=trader_id, symbol=symbol)


@app.route("/exchanges", methods=["GET"])
def get_exchanges():
    return responser.get_exchanges()


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

    balance_data = request.get_json()
    balance_data[Const.DB_SESSION_ID] = "temp_session_id"
    balance_model = BalanceModel(**balance_data)

    session = responser.create_session(session_model, balance_model)

    return session


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
    local_order_id = request.args.get(Const.DB_LOCAL_ORDER_ID, None)
    user_id = request.args.get(Const.DB_USER_ID, None)
    session_id = request.args.get(Const.DB_SESSION_ID, None)

    return responser.get_transactions(
        user_id=user_id, session_id=session_id, local_order_id=local_order_id
    )


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
    trader_id = request.args.get(Const.DB_TRADER_ID, None)
    user_id = request.args.get(Const.DB_USER_ID, None)
    importances = request.args.getlist(Const.IMPORTANCE, None)
    return responser.get_intervals(
        trader_id=trader_id, user_id=user_id, importances=importances
    )


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


@app.route("/strategies", methods=["GET"])
def get_strategies():
    return responser.get_strategies()


@app.route("/history_data", methods=["GET"])
def get_history_data():
    trader_id = request.args.get(Const.DB_TRADER_ID, None)
    param = HistoryDataParamModel(**request.args)

    return responser.get_history_data(trader_id=trader_id, param=param)


@app.route("/strategyData", methods=["GET"])
def get_strategy_data():
    strategy_param = StrategyParamModel(**request.args)
    return responser.get_strategy_data(strategy_param)


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


@app.route("/simulations", methods=["GET"])
def get_simulations():
    symbols = request.args.getlist("symbol", None)
    intervals = request.args.getlist("interval", None)
    strategies = request.args.getlist("strategy", None)

    return responser.get_simulations(
        symbols=symbols, intervals=intervals, strategies=strategies
    )


@app.route("/history_simulation", methods=["GET"])
def get_history_simulation():
    trader_id = request.args.get("trader_id", None)
    trading_type = request.args.get("trading_type", None)
    symbol = request.args.get("symbol", None)
    intervals = request.args.getlist("interval", None)
    strategies = request.args.getlist("strategy", None)
    stop_loss_rate = request.args.get(Const.SRV_STOP_LOSS_RATE, 0)
    is_trailing_stop = responser.get_param_bool(
        request.args.get(Const.SRV_IS_TRAILING_STOP_LOSS, "false")
    )
    take_profit_rate = request.args.get(Const.SRV_TAKE_PROFIT_RATE, 0)
    init_balance = float(request.args.get(Const.SRV_INIT_BALANCE, 1000))
    limit = int(request.args.get(Const.SRV_LIMIT, 400))

    return responser.get_history_simulation(
        trader_id=trader_id,
        trading_type=trading_type,
        symbol=symbol,
        intervals=intervals,
        strategies=strategies,
        stop_loss_rate=stop_loss_rate,
        is_trailing_stop=is_trailing_stop,
        take_profit_rate=take_profit_rate,
        init_balance=init_balance,
        limit=limit,
    )


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
    param = TraderSymbolIntervalLimitModel(**request.args)
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
