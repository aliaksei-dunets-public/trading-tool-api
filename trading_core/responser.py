import json
import pandas as pd
from flask import jsonify

from .core import log_file_name, Const, Symbol, Signal
from .model import model, Symbols
from .strategy import StrategyFactory, SignalFactory
from .simulator import Simulator


def decorator_json(func) -> str:
    def wrapper(*args, **kwargs):
        try:
            value = func(*args, **kwargs)

            if isinstance(value, list):
                if all(type(item) == dict for item in value):
                    return json.dumps(value)
                if all(isinstance(item, object) for item in value):
                    return json.dumps([item.__dict__ for item in value])
                else:
                    return json.dumps(value)
            elif isinstance(value, pd.DataFrame):
                return value.to_json(orient="table", index=True)
            elif isinstance(value, object):
                return json.dumps(value.__dict__)
            else:
                return json.dumps(value)

        except Exception as error:
            return jsonify({"error": error, }), 500

    return wrapper


class MessageBase:
    def __init__(self, channel_id: str, message_text: str) -> None:
        self._channel_id = channel_id
        self._message_text = message_text

    def get_channel_id(self) -> str:
        return self._channel_id

    def get_message_text(self) -> str:
        return self._message_text

    def set_message_text(self, text: str) -> None:
        self._message_text = text

    def add_message_text(self, text: str) -> None:
        self._message_text += text


class MessageEmail(MessageBase):
    def __init__(self, channel_id: str, subject: str, message_text: str) -> None:
        MessageBase.__init__(self, channel_id=channel_id,
                             message_text=message_text)
        self._subject = subject

    def get_subject(self) -> str:
        return self._subject


class Messages:
    def __init__(self):
        self._messages = {}

    def check_message(self, channel_id: str) -> bool:
        if channel_id in self._messages:
            return True
        else:
            return False

    def get_message(self, channel_id: str) -> MessageBase:
        if self.check_message(channel_id):
            return self._messages[channel_id]
        else:
            None

    def get_messages(self) -> dict:
        return self._messages

    def add_message_text(self, channel_id: str, text: str) -> MessageBase:
        message = self.get_message(channel_id)
        if message:
            message.add_message_text(text)
        else:
            message = self.create_message(channel_id=channel_id, text=text)

        return message

    def set_message_text(self, channel_id: str, text: str) -> MessageBase:
        message = self.get_message(channel_id)
        if message:
            message.set_message_text(text)
        else:
            message = self.create_message(channel_id=channel_id, text=text)

        return message

    def add_message(self, message: MessageBase) -> None:
        self._messages[message.get_channel_id()] = message

    def create_message(self, channel_id: str, text: str) -> MessageBase:
        message = MessageBase(channel_id=channel_id, message_text=text)
        self.add_message(message)
        return message


class ResponserBase():
    def get_param_bool(self, param_value):
        return bool(param_value.lower() == 'true')

    def get_symbol(self, code: str) -> Symbol:
        return Symbols().get_symbol(code)

    def get_symbol_list(self, code: str, name: str, status: str, type: str, from_buffer: bool) -> list[Symbol]:
        return Symbols(from_buffer).get_symbol_list(code=code, name=name, status=status, type=type)

    def get_intervals(self, importances: list = None) -> list:
        return model.get_intervals_config(importances)

    def get_indicators(self) -> list:
        return model.get_indicators_config()

    def get_strategies(self) -> list:
        return model.get_strategies()

    def get_history_data(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> pd.DataFrame:
        history_data_inst = model.get_handler().getHistoryData(
            symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)
        return history_data_inst.getDataFrame()

    def get_strategy_data(self, code: str, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> pd.DataFrame:
        strategy_inst = StrategyFactory(code)
        return strategy_inst.get_strategy_data(symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)

    def get_signals(self, symbols: list, intervals: list, strategies: list, signals_config: list, closed_bars: bool) -> list[Signal]:
        return SignalFactory().get_signals(symbols=symbols, intervals=intervals, strategies=strategies, signals_config=signals_config, closed_bars=closed_bars)


class ResponserWeb(ResponserBase):
    @decorator_json
    def get_symbol(self, code: str) -> json:
        symbol = super().get_symbol(code)
        if symbol:
            return symbol
        else:
            raise Exception(f"Symbol: {code} can't be detected")

    @decorator_json
    def get_symbol_list(self, code: str, name: str, status: str, type: str, from_buffer: bool) -> json:
        return super().get_symbol_list(code=code, name=name, status=status, type=type, from_buffer=from_buffer)

    @decorator_json
    def get_intervals(self, importances: list = None) -> json:
        return super().get_intervals(importances=importances)

    @decorator_json
    def get_indicators(self) -> json:
        return super().get_indicators()

    @decorator_json
    def get_strategies(self) -> json:
        return super().get_strategies()

    @decorator_json
    def get_history_data(self, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> json:
        return super().get_history_data(symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)

    @decorator_json
    def get_strategy_data(self, code: str, symbol: str, interval: str, limit: int, from_buffer: bool, closed_bars: bool) -> json:
        return super().get_strategy_data(code=code, symbol=symbol, interval=interval, limit=limit, from_buffer=from_buffer, closed_bars=closed_bars)

    @decorator_json
    def get_signals(self, symbols: list, intervals: list, strategies: list, signals_config: list, closed_bars: bool) -> json:
        signals = []
        signals_list = super().get_signals(symbols=symbols, intervals=intervals,
                                           strategies=strategies, signals_config=signals_config, closed_bars=closed_bars)

        for signal_inst in signals_list:
            signals.append(signal_inst.get_signal_dict())

        return signals


class ResponserEmail(ResponserBase):
    def get_signals(self, symbols: list, intervals: list, strategies: list, signals_config: list, closed_bars: bool) -> Messages:
        signals_list = super().get_signals(symbols=symbols, intervals=intervals,
                                           strategies=strategies, signals_config=signals_config, closed_bars=closed_bars)

        # Create the HTML table
        table_html = '<table border="1">'
        table_html += '<tr><th>DateTime</th><th>Symbol</th><th>Interval</th><th>Strategy</th><th>Signal</th></tr>'
        for signal_inst in signals_list:
            table_html += '<tr>'
            table_html += f'<td>{signal_inst.get_date_time().isoformat()}</td>'
            table_html += f'<td>{signal_inst.get_symbol()}</td>'
            table_html += f'<td>{signal_inst.get_interval()}</td>'
            table_html += f'<td>{signal_inst.get_strategy()}</td>'
            table_html += f'<td>{signal_inst.get_signal()}</td>'
            table_html += '</tr>'
        table_html += '</table>'

        # Create the email body as HTML
        message_text = f'<h4>Alert signals for {signal_inst.get_interval()}</h4>{table_html}'

        message_inst = MessageEmail(
            channel_id='None', subject=f'[TradingTool]: Alert signals for {intervals[0]}', message_text=message_text)

        messages_inst = Messages()
        messages_inst.add_message(message_inst)

        return messages_inst


class ResponserBot(ResponserBase):
    def get_signals_for_alerts(self, alerts_db: dict) -> Messages:

        messages_inst = Messages()

        for alert_db in alerts_db:
            channel_id = alert_db[Const.DB_CHANNEL_ID]
            symbol = alert_db[Const.DB_SYMBOL]
            interval = alert_db[Const.DB_SYMBOL]
            strategies = alert_db[Const.DB_STRATEGIES]
            signals_config = alert_db[Const.DB_SIGNALS]
            comment = alert_db[Const.DB_COMMENT]

            comments_text = f' | {comment}' if comment else ''

            signals_list = super().get_signals(symbols=[symbol], intervals=[
                interval], strategies=strategies, signals_config=signals_config, closed_bars=True)

            for signal_inst in signals_list:
                signal_text = f'<b>{signal_inst.get_signal()}</b>'
                message_text = f'{signal_inst.get_date_time().isoformat()} - <b>{signal_inst.get_symbol()} - {signal_inst.get_interval()}</b>: ({signal_inst.get_strategy()}) - {signal_text}{comments_text}\n\n'

                # Add header of the message before the first content
                if not messages_inst.check_message(channel_id):
                    message_text = f'<b>Alert signals for {interval}: \n</b>{message_text}'

                messages_inst.add_message_text(
                    channel_id=channel_id, text=message_text)

        return messages_inst

    def get_signals_for_orders(self, orders_db: dict) -> Messages:

        def get_comment(self, order_type, signal_value):
            if order_type == Const.LONG:
                if signal_value in (Const.BUY, Const.STRONG_BUY):
                    return f' | <b>You can open more LONG positions</b>'
                elif signal_value in (Const.SELL, Const.STRONG_SELL):
                    return f' | <b>CLOSE all postions</b>'
            elif order_type == Const.SHORT:
                if signal_value in (Const.BUY, Const.STRONG_BUY):
                    return f' | <b>CLOSE all postions</b>'
                elif signal_value in (Const.SELL, Const.STRONG_SELL):
                    return f' | <b>You can open more SHORT positions</b>'
            else:
                return ''

        messages_inst = Messages()

        for order_db in orders_db:
            channel_id = '1658698044'
            order_type = order_db[Const.DB_ORDER_TYPE]
            symbol = order_db[Const.DB_SYMBOL]
            interval = order_db[Const.DB_SYMBOL]
            strategies = order_db[Const.DB_STRATEGIES]

            signals_list = super().get_signals(symbols=[symbol], intervals=[
                interval], strategies=strategies, signals_config=[], closed_bars=True)

            for signal_inst in signals_list:

                signal_value = signal_inst.get_signal()
                signal_text = f'<b>{signal_value}</b>'
                comment_text = get_comment(order_type, signal_value)

                message_text = f'{signal_inst.get_date_time().isoformat()} - <b>{signal_inst.get_symbol()} - {signal_inst.get_interval()}</b>: ({signal_inst.get_strategy()}) - {signal_text}{comment_text}\n'

                # Add header of the message before the first content
                if not messages_inst.check_message(channel_id):
                    message_text = f'<b>Order signals for {interval}: \n</b>{message_text}'

                messages_inst.add_message_text(
                    channel_id=channel_id, text=message_text)

        return messages_inst


@decorator_json
def getSimulate(symbols: list, intervals: list, strategyCodes: list):
    return Simulator().simulateTrading(symbols, intervals, strategyCodes)


@decorator_json
def getSimulations(symbols: list, intervals: list, strategyCodes: list):
    return Simulator().getSimulations(symbols, intervals, strategyCodes)


@decorator_json
def getSignalsBySimulation(symbols: list, intervals: list, strategyCodes: list):
    return Simulator().getSignalsBySimulation(symbols, intervals, strategyCodes)


def getLogs(start_date, end_date):
    # date_format = "%Y-%m-%d"
    # start_date = datetime.strptime(start_date, date_format)
    # end_date = datetime.strptime(end_date, date_format) + datetime.timedelta(days=1)
    # logs = []
    # current_date = start_date
    # while current_date < end_date:
    try:
        with open(log_file_name, "r") as log_file:
            logs = log_file.read()
    except FileNotFoundError:
        pass
        # current_date += datetime.timedelta(days=1)

    logs = logs.replace('\n', '<br>')

    return logs
