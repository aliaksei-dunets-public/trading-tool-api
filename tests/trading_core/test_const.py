from trading_core.constants import Const


def test_const_conf_properties():
    assert Const.CONF_PROPERTY_DEBUG_LOG == "DEBUG_LOG"
    assert Const.CONF_PROPERTY_CORE_LOG == "CORE_LOG"
    assert Const.CONF_PROPERTY_API_LOG == "API_LOG"
    assert Const.CONF_PROPERTY_HANDLER_LOG == "HANDLER_LOG"
    assert Const.CONF_PROPERTY_MONGODB_LOG == "MONGODB_LOG"
    assert Const.CONF_PROPERTY_RESPONSER_LOG == "RESPONSER_LOG"
    assert Const.CONF_PROPERTY_ROBOT_LOG == "ROBOT_LOG"
    assert Const.CONF_PROPERTY_HIST_SIMULATION_LOG == "HISTORY_SIMULATION_LOG"
    assert Const.CONF_PROPERTY_HS_TRADER_ID == "HS_TRADER_ID"


def test_const_database():
    assert Const.DATABASE_NAME == "ClusterShared"


def test_const_db_collections():
    assert Const.DB_COLLECTION_JOBS == "jobs"
    assert Const.DB_COLLECTION_ALERTS == "alerts"
    assert Const.DB_COLLECTION_SIMULATIONS == "simulations"
    assert Const.DB_COLLECTION_USERS == "users"
    assert Const.DB_COLLECTION_CHANNELS == "channels"
    assert Const.DB_COLLECTION_SESSIONS == "sessions"
    assert Const.DB_COLLECTION_TRADERS == "traders"
    assert Const.DB_COLLECTION_BALANCES == "balances"
    assert Const.DB_COLLECTION_ORDERS == "orders"
    assert Const.DB_COLLECTION_LEVERAGES == "leverages"
    assert Const.DB_COLLECTION_TRANSACTIONS == "transactions"


def test_const_db_fields():
    assert Const.DB_ID == "_id"
    assert Const.DB_USER_ID == "user_id"
    assert Const.DB_CHANNEL_ID == "channel_id"
    assert Const.DB_SESSION_ID == "session_id"
    assert Const.DB_ORDER_ID == "order_id"
    assert Const.DB_LOCAL_ORDER_ID == "local_order_id"
    assert Const.DB_POSITION_ID == "position_id"
    assert Const.DB_TRADER_ID == "trader_id"
    assert Const.DB_EXCHANGE_ID == "exchange_id"
    assert Const.DB_SYMBOL == "symbol"
    assert Const.DB_NAME == "name"
    assert Const.DB_STATUS == "status"
    assert Const.DB_TYPE == "type"
    assert Const.DB_SIDE == "side"
    assert Const.DB_SESSION_TYPE == "session_type"
    assert Const.DB_ACCOUNT_ID == "account_id"
    assert Const.DB_CURRENCY == "currency"
    assert Const.DB_QUANTITY == "quantity"
    assert Const.DB_FEE == "fee"
    assert Const.DB_OPEN_PRICE == "open_price"
    assert Const.DB_OPEN_DATETIME == "open_datetime"
    assert Const.DB_OPEN_REASON == "open_reason"
    assert Const.DB_CLOSE_ORDER_ID == "close_order_id"
    assert Const.DB_CLOSE_PRICE == "close_price"
    assert Const.DB_CLOSE_DATETIME == "close_datetime"
    assert Const.DB_CLOSE_REASON == "close_reason"
    assert Const.DB_TOTAL_PROFIT == "total_profit"
    assert Const.DB_LEVERAGE == "leverage"
    assert Const.DB_STOP_LOSS_RATE == "stop_loss_rate"
    assert Const.DB_TAKE_PROFIT_RATE == "take_profit_rate"
    assert Const.DB_STOP_LOSS == "stop_loss"
    assert Const.DB_IS_TRAILING_STOP == "is_trailing_stop"
    assert Const.DB_TAKE_PROFIT == "take_profit"
    assert Const.DB_HIGH_PRICE == "high_price"
    assert Const.DB_LOW_PRICE == "low_price"
    assert Const.DB_DATE_TIME == "date_time"
    assert Const.DB_INIT_BALANCE == "init_balance"
    assert Const.DB_TOTAL_BALANCE == "total_balance"
    assert Const.DB_CREATED_AT == "created_at"
    assert Const.DB_CREATED_BY == "created_by"
    assert Const.DB_CHANGED_AT == "changed_at"
    assert Const.DB_CHANGED_BY == "changed_by"
    assert Const.DB_TRANSACTION_DATA == "data"
    assert Const.DB_CHANNEL == "channel"


def test_const_fields():
    assert Const.FLD_SYMBOL == Const.DB_SYMBOL
    assert Const.FLD_ID == "id"
    assert Const.FLD_INTERVAL == "interval"
    assert Const.FLD_END_DATETIME == "end_datetime"
    assert Const.FLD_LIMIT == "limit"
    assert Const.FLD_IS_BUFFER == "is_buffer"
    assert Const.FLD_CLOSED_BARS == "closed_bars"
    assert Const.FLD_PRICE_TYPE == "price_type"
    assert Const.FLD_STOP_LOSS_VALUE == "stop_loss_value"
    assert Const.FLD_TAKE_PROFIT_VALUE == "take_profit_value"
    assert Const.FLD_CLOSE == "Close"
    assert Const.FLD_SIGNAL == "signal"
    assert Const.FLD_ATR == "ATR"
    assert Const.FLD_CCI == "CCI"
    assert Const.FLD_EMA_SHORT == "EMA_SHORT"
    assert Const.FLD_EMA_MEDIUM == "EMA_MEDIUM"
    assert Const.FLD_EMA_LONG == "EMA_LONG"
    assert Const.FLD_EMA_8 == "EMA_8"
    assert Const.FLD_EMA_30 == "EMA_30"
    assert Const.FLD_EMA_50 == "EMA_50"
    assert Const.FLD_EMA_100 == "EMA_100"
    assert Const.FLD_TREND == "trend"
    assert Const.FLD_TREND_UP_LEVEL == "trend_up_level"
    assert Const.FLD_BB_LOWER == "BB_LOWR"
    assert Const.FLD_BB_MID == "BB_MID"
    assert Const.FLD_BB_UPPER == "BB_UPPER"
    assert Const.FLD_BB_BANDWIDTH == "BB_BANDWIDTH"
    assert Const.FLD_BB_PERCENT == "BB_PERCENT"


def test_const_api_fields():
    assert Const.API_FLD_ID == Const.FLD_ID
    assert Const.API_FLD_ACCOUNT_ID == "accountId"
    assert Const.API_FLD_ORDER_ID == "orderId"
    assert Const.API_FLD_ORDER_LINK_ID == "orderLinkId"
    assert Const.API_FLD_POSITION_ID == "positionId"
    assert Const.API_FLD_SYMBOL == Const.DB_SYMBOL
    assert Const.API_FLD_INTERVAL == Const.FLD_INTERVAL
    assert Const.API_FLD_END_TIME == "endTime"
    assert Const.API_FLD_END == "end"
    assert Const.API_FLD_LIMIT == Const.FLD_LIMIT
    assert Const.API_FLD_PRICE == "price"
    assert Const.API_FLD_QUANTITY == "quantity"
    assert Const.API_FLD_EXECUTED_QUANTITY == "executedQty"
    assert Const.API_FLD_EXEC_QUANTITY == "execQuantity"
    assert Const.API_FLD_EXECUTED_PRICE == "execPrice"
    assert Const.API_FLD_EXECUTED_TIMESTAMP == "execTimestamp"
    assert Const.API_FLD_TRANSACT_TIME == "transactTime"
    assert Const.API_FLD_STATUS == "status"
    assert Const.API_FLD_TYPE == "type"
    assert Const.API_FLD_SIDE == "side"
    assert Const.API_FLD_MARGIN == "margin"
    assert Const.API_FLD_FEE == "fee"
    assert Const.API_FLD_PRICE_TYPE == "priceType"
    assert Const.API_FLD_TAKE_PROFIT == "takeProfit"
    assert Const.API_FLD_STOP_LOSS == "stopLoss"
    assert Const.API_FLD_OPEN_PRICE == "openPrice"
    assert Const.API_FLD_OPEN_QUANTITY == "openQuantity"
    assert Const.API_FLD_OPEN_TIMESTAMP == "openTimestamp"
    assert Const.API_FLD_RPL == "rpl"
    assert Const.API_FLD_SOURCE == "source"
    assert Const.API_FLD_ACCOUNT_FREE == "free"
    assert Const.API_FLD_ACCOUNT_LOCKED == "locked"
    assert Const.API_FLD_CATEGORY == "category"
    assert Const.API_FLD_RESULT == "result"
    assert Const.API_FLD_LIST == "list"
    assert Const.API_FLD_RET_CODE == "retCode"
    assert Const.API_FLD_RET_MESSAGE == "retMsg"
    assert Const.API_FLD_SIZE == "size"


def test_const_legacy_code():
    assert Const.DB_JOB_TYPE == "job_type"
    assert Const.DB_INTERVAL == "interval"
    assert Const.DB_IS_ACTIVE == "is_active"
    assert Const.DB_STRATEGIES == "strategies"
    assert Const.DB_STRATEGY == "strategy"
    assert Const.DB_SIGNALS == "signals"
    assert Const.DB_COMMENT == "comment"
    assert Const.DB_ORDER_TYPE == "order_type"
    assert Const.DB_OPEN_PRICE == "open_price"
    assert Const.DB_ALERT_TYPE == "alert_type"
    assert Const.DB_LIMIT == "limit"
    assert Const.DB_FEE_RATE == "fee_rate"
    assert Const.DB_PRICE == "price"
    assert Const.DB_BALANCE == "balance"
    assert Const.DB_PROFIT == "profit"
    assert Const.DB_TOTAL == "total"
    assert Const.DB_COUNT_PROFIT == "count_profit"
    assert Const.DB_COUNT_LOSS == "count_loss"
    assert Const.DB_SUM_PROFIT == "sum_profit"
    assert Const.DB_SUM_LOSS == "sum_loss"
    assert Const.DB_SUM_FEE_VALUE == "sum_fee_value"
    assert Const.DB_AVG_PERCENT_PROFIT == "avg_percent_profit"
    assert Const.DB_AVG_PERCENT_LOSS == "avg_percent_loss"
    assert Const.DB_AVG_MAX_PERCENT_PROFIT == "avg_max_percent_profit"
    assert Const.DB_AVG_MIN_PERCENT_LOSS == "avg_min_percent_loss"


def test_const_signal_values():
    assert Const.STRONG_BUY == "Strong Buy"
    assert Const.BUY == "Buy"
    assert Const.STRONG_SELL == "Strong Sell"
    assert Const.SELL == "Sell"


def test_const_direction_values():
    assert Const.LONG == "LONG"
    assert Const.SHORT == "SHORT"


def test_const_trend_values():
    assert Const.TREND_UP == "UpTrend"
    assert Const.TREND_DOWN == "DownTrend"
    assert Const.STRONG_TREND_UP == "StrongUpTrend"
    assert Const.STRONG_TREND_DOWN == "StrongDownTrend"


def test_const_statuses():
    assert Const.STATUS_OPEN == "Open"
    assert Const.STATUS_CLOSE == "Close"


def test_const_order_close_reason():
    assert Const.ORDER_CLOSE_REASON_STOP_LOSS == "STOP_LOSS"
    assert Const.ORDER_CLOSE_REASON_TAKE_PROFIT == "TAKE_PROFIT"
    assert Const.ORDER_CLOSE_REASON_SIGNAL == "SIGNAL"


def test_const_importance_levels():
    assert Const.IMPORTANCE_LOW == "LOW"
    assert Const.IMPORTANCE_MEDIUM == "MEDIUM"
    assert Const.IMPORTANCE_HIGH == "HIGH"


def test_const_job_types():
    assert Const.JOB_TYPE_INIT == "JOB_TYPE_INIT"
    assert Const.JOB_TYPE_BOT == "JOB_TYPE_BOT"
    assert Const.JOB_TYPE_EMAIL == "JOB_TYPE_EMAIL"
    assert Const.JOB_TYPE_ROBOT == "JOB_TYPE_ROBOT"


def test_const_alert_types():
    assert Const.ALERT_TYPE_BOT == "ALERT_TYPE_BOT"
    assert Const.ALERT_TYPE_EMAIL == "ALERT_TYPE_EMAIL"
    assert Const.ALERT_TYPE_SYSTEM == "ALERT_TYPE_SYSTEM"


def test_const_column_names():
    assert Const.COLUMN_DATETIME == "Datetime"
    assert Const.COLUMN_OPEN == "Open"
    assert Const.COLUMN_HIGH == "High"
    assert Const.COLUMN_LOW == "Low"
    assert Const.COLUMN_CLOSE == "Close"
    assert Const.COLUMN_VOLUME == "Volume"


def test_const_parameters():
    assert Const.PARAM_SIGNAL == "signal"
    assert Const.PARAM_SYMBOL == "symbol"
    assert Const.CODE == "code"
    assert Const.INTERVAL == "interval"
    assert Const.LIMIT == "limit"
    assert Const.STRATEGY == "strategy"
    assert Const.DATETIME == "date_time"
    assert Const.NAME == "name"
    assert Const.DESCR == "descr"
    assert Const.STATUS == "status"
    assert Const.START_TIME == "start_time"
    assert Const.END_TIME == "end_time"
    assert Const.START_DATE == "start_date"
    assert Const.END_DATE == "end_date"
    assert Const.CLOSED_BARS == "closed_bars"
    assert Const.IMPORTANCE == "importance"
    assert Const.LENGTH == "length"
    assert Const.VALUE == "value"
    assert Const.JOB_ID == "job_id"
    assert Const.TRADING_TIME == "tradingTime"
    assert Const.PARAM_SYMBOL_TYPE == "type"
    assert Const.PARAM_QUERY == "query"
    assert Const.PARAM_TREND == "trend"
    assert Const.PARAM_LOCAL_TREND == "local_trend"
    assert Const.PARAM_GLOBAL_TREND == "global_trend"
    assert Const.OPEN_VALUE == "open_value"
    assert Const.CLOSE_VALUE == "close_value"


def test_const_service_params():
    assert Const.SRV_LIMIT == "limit"
    assert Const.SRV_INIT_BALANCE == "init_balance"
    assert Const.SRV_STOP_LOSS_RATE == "stop_loss_rate"
    assert Const.SRV_IS_TRAILING_STOP_LOSS == "is_trailing_stop"
    assert Const.SRV_TAKE_PROFIT_RATE == "take_profit_rate"
    assert Const.SRV_FEE_RATE == "fee_rate"
