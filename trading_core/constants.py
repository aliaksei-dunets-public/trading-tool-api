class Const:
    # Stock Exchanges
    STOCK_EXCH_CURRENCY_COM = 'CURRENCY.COM'

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
    TA_STRATEGY_CCI_20_TREND_100 = "CCI_20_TREND_100"
    TA_STRATEGY_CCI_50_TREND_0 = "CCI_50_TREND_0"

    # Collections name
    DB_COLLECTION_JOBS = 'jobs_temp'
    DB_COLLECTION_ALERTS = 'alerts_temp'
    DB_COLLECTION_ORDERS = 'orders_temp'

    # DB fields
    DB_ID = "_id"
    DB_JOB_TYPE = 'job_type'
    DB_INTERVAL = 'interval'
    DB_IS_ACTIVE = 'is_active'
    DB_CREATED_AT = "created_at"
    DB_CREATED_BY = "created_by"
    DB_CHANGED_AT = "changed_at"
    DB_CHANGED_BY = "changed_by"
    DB_CHANNEL_ID = 'channel_id'
    DB_SYMBOL = 'symbol'
    DB_STRATEGIES = 'strategies'
    DB_STRATEGY = 'strategy'
    DB_SIGNALS = 'signals'
    DB_COMMENT = 'comment'
    DB_ORDER_TYPE = 'order_type'
    DB_OPEN_DATE_TIME = 'open_date_time'
    DB_OPEN_PRICE = 'open_price'
    DB_CLOSE_DATE_TIME = 'close_date_time'
    DB_CLOSE_PRICE = 'close_price'
    DB_ALERT_TYPE = 'alert_type'
    DB_INIT_BALANCE = 'init_balance'
    DB_LIMIT = 'limit'
    DB_STOP_LOSS_RATE = 'stop_loss_rate'
    DB_TAKE_PROFIT_RATE = 'take_profit_rate'
    DB_FEE_RATE = 'fee_rate'
    DB_PRICE = 'price'
    DB_QUANTITY = 'quantity'
    DB_BALANCE = 'balance'
    DB_PROFIT = 'profit'

    # Config properties
    CONFIG_DEBUG_LOG = 'DEBUG_LOG'

    # Signal Values
    STRONG_BUY = 'Strong Buy'
    BUY = 'Buy'
    STRONG_SELL = 'Strong Sell'
    SELL = 'Sell'
    DEBUG_SIGNAL = 'Debug'

    # Direction Values
    LONG = 'LONG'
    SHORT = 'SHORT'

    # Statuses
    STATUS_OPEN = 'Open'
    STATUS_CLOSE = 'Close'

    # Order Close Reason
    ORDER_CLOSE_REASON_STOP_LOSS = 'Stop Loss'
    ORDER_CLOSE_REASON_TAKE_PROFIT = 'Take Profit'
    ORDER_CLOSE_REASON_SIGNAL = 'Signal'

    # Importance
    IMPORTANCE_LOW = 'LOW'
    IMPORTANCE_MEDIUM = 'MEDIUM'
    IMPORTANCE_HIGH = 'HIGH'

    # Job types
    JOB_TYPE_INIT = 'JOB_TYPE_INIT'
    JOB_TYPE_BOT = 'JOB_TYPE_BOT'
    JOB_TYPE_EMAIL = 'JOB_TYPE_EMAIL'

    # Alert types
    ALERT_TYPE_BOT = 'ALERT_TYPE_BOT'
    ALERT_TYPE_EMAIL = 'ALERT_TYPE_EMAIL'
    ALERT_TYPE_SYSTEM = 'ALERT_TYPE_SYSTEM'

    # Column Names
    COLUMN_DATETIME = 'Datetime'
    COLUMN_OPEN = 'Open'
    COLUMN_HIGH = 'High'
    COLUMN_LOW = 'Low'
    COLUMN_CLOSE = 'Close'
    COLUMN_VOLUME = 'Volume'

    # Parameters
    PARAM_SIGNAL = 'signal'
    PARAM_SYMBOL = 'symbol'
    CODE = 'code'
    INTERVAL = 'interval'
    LIMIT = 'limit'
    STRATEGY = 'strategy'
    DATETIME = 'date_time'
    NAME = 'name'
    DESCR = 'descr'
    STATUS = 'status'
    START_TIME = 'start_time'
    END_TIME = 'end_time'
    START_DATE = 'start_date'
    END_DATE = 'end_date'
    CLOSED_BARS = 'closed_bars'
    IMPORTANCE = 'importance'
    LENGTH = "length"
    VALUE = "value"
    JOB_ID = "job_id"
    TRADING_TIME = "tradingTime"
    PARAM_SYMBOL_TYPE = "type"

    # API fields
    END_TIME = 'endTime'
