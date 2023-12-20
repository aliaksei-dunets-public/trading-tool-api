from unittest.mock import patch
import json
import os

from trading_core.model import model


def getHistoryDataTest(symbol, interval, limit, from_buffer, closed_bars):
    file_path = f'{os.getcwd()}/static/tests/{symbol}_{interval}.json'
    with open(file_path, 'r') as reader:
        testHistoryData = json.load(reader)

    with patch('trading_core.handler.CurrencyComApi.get_api_klines') as mock_getKlines:
        mock_response = testHistoryData
        mock_getKlines.return_value = mock_response

        history_data = model.get_handler().getHistoryData(
            symbol, interval, limit, from_buffer, closed_bars)
        return history_data
