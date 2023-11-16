class Const:
    # Stock Exchanges
    STOCK_EXCH_CURRENCY_COM = "CURRENCY.COM"
    STOCK_EXCH_DEMO_CURRENCY_COM = "DEMO_CURRENCY.COM"
    STOCK_EXCH_LOCAL_CURRENCY_COM = "LOCAL_CURRENCY.COM"

    # Intervals
    TA_INTERVAL_5M = "5m"
    TA_INTERVAL_15M = "15m"
    TA_INTERVAL_30M = "30m"
    TA_INTERVAL_1H = "1h"
    TA_INTERVAL_4H = "4h"
    TA_INTERVAL_1D = "1d"
    TA_INTERVAL_1WK = "1w"

    # Indicators
    TA_INDICATOR_CCI = "CCI"

    # Strategies
    TA_STRATEGY_CCI_14_TREND_100 = "CCI_14_TREND_100"
    TA_STRATEGY_CCI_14_BASED_TREND_100 = "CCI_14_BASED_TREND_100"
    TA_STRATEGY_CCI_14_TREND_170_165 = "CCI_14_TREND_170_165"
    TA_STRATEGY_CCI_20_TREND_100 = "CCI_20_TREND_100"
    TA_STRATEGY_CCI_50_TREND_0 = "CCI_50_TREND_0"

    # Database Name
    DATABASE_NAME = "ClusterShared"

    # DB Collections name
    DB_COLLECTION_JOBS = "jobs"
    DB_COLLECTION_ALERTS = "alerts"
    DB_COLLECTION_SIMULATIONS = "simulations"
    DB_COLLECTION_USERS = "users"
    DB_COLLECTION_CHANNELS = "channels"
    DB_COLLECTION_SESSIONS = "sessions"
    DB_COLLECTION_TRADERS = "traders"
    DB_COLLECTION_BALANCES = "balances"
    DB_COLLECTION_ORDERS = "orders"
    DB_COLLECTION_LEVERAGES = "leverages"
    DB_COLLECTION_TRANSACTIONS = "transactions"

    # DB fields
    DB_ID = "_id"
    DB_USER_ID = "user_id"
    DB_CHANNEL_ID = "channel_id"
    DB_SESSION_ID = "session_id"
    DB_ORDER_ID = "order_id"
    DB_SYMBOL = "symbol"
    DB_NAME = "name"
    DB_STATUS = "status"
    DB_TYPE = "type"
    DB_SIDE = "side"
    DB_ACCOUNT_ID = "account_id"
    DB_CURRENCY = "currency"
    DB_QUANTITY = "quantity"
    DB_FEE = "fee"
    DB_OPEN_PRICE = "open_price"
    DB_OPEN_DATETIME = "open_datetime"
    DB_CLOSE_PRICE = "close_price"
    DB_CLOSE_DATETIME = "close_datetime"
    DB_CLOSE_REASON = "close_reason"
    DB_TOTAL_PROFIT = "total_profit"
    DB_LEVERAGE = "leverage"
    DB_STOP_LOSS_RATE = "stop_loss_rate"
    DB_TAKE_PROFIT_RATE = "take_profit_rate"
    DB_STOP_LOSS = "stop_loss"
    DB_TAKE_PROFIT = "take_profit"
    DB_DATE_TIME = "date_time"
    DB_CREATED_AT = "created_at"
    DB_CREATED_BY = "created_by"
    DB_CHANGED_AT = "changed_at"
    DB_CHANGED_BY = "changed_by"

    # Fields
    FLD_SYMBOL = DB_SYMBOL
    FLD_ID = "id"
    FLD_INTERVAL = "interval"
    FLD_END_DATETIME = "end_datetime"
    FLD_LIMIT = "limit"
    FLD_IS_BUFFER = "is_buffer"
    FLD_CLOSED_BAR = "closed_bar"

    # API fields
    API_FLD_SYMBOL = DB_SYMBOL
    API_FLD_INTERVAL = FLD_INTERVAL
    API_FLD_END_TIME = "endTime"
    API_FLD_LIMIT = FLD_LIMIT

    ########################### Legacy code ####################################

    DB_JOB_TYPE = "job_type"
    DB_INTERVAL = "interval"
    DB_IS_ACTIVE = "is_active"

    DB_STRATEGIES = "strategies"
    DB_STRATEGY = "strategy"
    DB_SIGNALS = "signals"
    DB_COMMENT = "comment"
    DB_ORDER_TYPE = "order_type"
    DB_OPEN_DATE_TIME = "open_date_time"
    DB_OPEN_PRICE = "open_price"
    DB_CLOSE_DATE_TIME = "close_date_time"
    # DB_CLOSE_PRICE = "close_price"
    DB_ALERT_TYPE = "alert_type"
    DB_INIT_BALANCE = "init_balance"
    DB_LIMIT = "limit"
    DB_FEE_RATE = "fee_rate"
    DB_PRICE = "price"
    # DB_QUANTITY = "quantity"
    DB_BALANCE = "balance"
    DB_PROFIT = "profit"
    DB_TOTAL = "total"
    DB_COUNT_PROFIT = "count_profit"
    DB_COUNT_LOSS = "count_loss"
    DB_SUM_PROFIT = "sum_profit"
    DB_SUM_LOSS = "sum_loss"
    DB_SUM_FEE_VALUE = "sum_fee_value"
    DB_AVG_PERCENT_PROFIT = "avg_percent_profit"
    DB_AVG_PERCENT_LOSS = "avg_percent_loss"
    DB_AVG_MAX_PERCENT_PROFIT = "avg_max_percent_profit"
    DB_AVG_MIN_PERCENT_LOSS = "avg_min_percent_loss"

    # Config properties
    CONFIG_DEBUG_LOG = "DEBUG_LOG"

    # Signal Values
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    STRONG_SELL = "Strong Sell"
    SELL = "Sell"
    DEBUG_SIGNAL = "Debug"
    TREND_CHANGED = "Trend Changed"

    # Direction Values
    LONG = "LONG"
    SHORT = "SHORT"

    # Trend values
    TREND_UP = "UpTrend"
    TREND_DOWN = "DownTrend"

    # Statuses
    STATUS_OPEN = "Open"
    STATUS_CLOSE = "Close"

    # Order Close Reason
    ORDER_CLOSE_REASON_STOP_LOSS = "STOP_LOSS"
    ORDER_CLOSE_REASON_TAKE_PROFIT = "TAKE_PROFIT"
    ORDER_CLOSE_REASON_SIGNAL = "SIGNAL"

    # Importance
    IMPORTANCE_LOW = "LOW"
    IMPORTANCE_MEDIUM = "MEDIUM"
    IMPORTANCE_HIGH = "HIGH"

    # Job types
    JOB_TYPE_INIT = "JOB_TYPE_INIT"
    JOB_TYPE_BOT = "JOB_TYPE_BOT"
    JOB_TYPE_EMAIL = "JOB_TYPE_EMAIL"
    JOB_TYPE_ROBOT = "JOB_TYPE_ROBOT"

    # Alert types
    ALERT_TYPE_BOT = "ALERT_TYPE_BOT"
    ALERT_TYPE_EMAIL = "ALERT_TYPE_EMAIL"
    ALERT_TYPE_SYSTEM = "ALERT_TYPE_SYSTEM"

    # Column Names
    COLUMN_DATETIME = "Datetime"
    COLUMN_OPEN = "Open"
    COLUMN_HIGH = "High"
    COLUMN_LOW = "Low"
    COLUMN_CLOSE = "Close"
    COLUMN_VOLUME = "Volume"

    # Parameters
    PARAM_SIGNAL = "signal"
    PARAM_SYMBOL = "symbol"
    CODE = "code"
    INTERVAL = "interval"
    LIMIT = "limit"
    STRATEGY = "strategy"
    DATETIME = "date_time"
    NAME = "name"
    DESCR = "descr"
    STATUS = "status"
    START_TIME = "start_time"
    END_TIME = "end_time"
    START_DATE = "start_date"
    END_DATE = "end_date"
    CLOSED_BARS = "closed_bars"
    IMPORTANCE = "importance"
    LENGTH = "length"
    VALUE = "value"
    JOB_ID = "job_id"
    TRADING_TIME = "tradingTime"
    PARAM_SYMBOL_TYPE = "type"
    PARAM_QUERY = "query"
    PARAM_TREND = "trend"
    OPEN_VALUE = "open_value"
    CLOSE_VALUE = "close_value"

    # Service params
    SRV_INIT_BALANCE = "init_balance"
    SRV_STOP_LOSS_RATE = "stop_loss_rate"
    SRV_TAKE_PROFIT_RATE = "take_profit_rate"
    SRV_FEE_RATE = "fee_rate"
