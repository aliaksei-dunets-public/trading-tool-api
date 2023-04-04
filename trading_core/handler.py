from datetime import datetime
import requests
import json
import pandas as pd
import os
import logging

from .core import Symbol, HistoryData

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

class HandlerBase:
    def getHistoryData(self, symbol, interval, limit) -> HistoryData:
        pass

    def getSymbols(self, code: str = None, name: str = None, status: str = None, type: str = None, isBuffer: bool = True) -> list:
        pass

    def getIntervalsDetails(self) -> list:
        return []

    def _mapInterval(self, interval) -> str:
        return interval


class HandlerCurrencyCom(HandlerBase):
    def getHistoryData(self, symbol, interval, limit) -> HistoryData:

        logging.info(f'getHistoryData(symbol={symbol}, interval={interval}, limit={limit})')

        response = self.__getKlines(symbol, self._mapInterval(interval), limit)

        df = pd.DataFrame(response, columns=[
                          'DatetimeFloat', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Datetime'] = df.apply(lambda x: pd.to_datetime(
            datetime.fromtimestamp(x['DatetimeFloat'] / 1000.0)), axis=1)
        df.set_index('Datetime', inplace=True)
        df.drop(["DatetimeFloat"], axis=1, inplace=True)
        df = df.astype(float)

        return HistoryData(symbol, interval, limit, df)

    def getSymbols(self, code: str = None, name: str = None, status: str = None, type: str = None, isBuffer: bool = True) -> list:
        
        logging.info(f'getSymbols(code={code}, name={name}, status={status}, type={type}, isBuffer={isBuffer})')

        symbols = []
        tempSymbols = []

        file_path = f'{os.getcwd()}/static/symbols.json'

        if isBuffer and os.path.exists(file_path):
            with open(file_path, 'r') as reader:
                tempSymbols = json.load(reader)

        if not tempSymbols:
            response = requests.get(
                "https://api-adapter.backend.currency.com/api/v2/exchangeInfo")

            if response.status_code == 200:
                jsonResponse = json.loads(response.text)

                for obj in jsonResponse['symbols']:
                    if obj['quoteAssetId'] == 'USD' and obj['assetType'] in ['CRYPTOCURRENCY', 'EQUITY', 'COMMODITY'] and 'REGULAR' in obj['marketModes']:
                        tempSymbols.append({'code': obj['symbol'],
                                            'name': obj['name'],
                                            'status': obj['status'],
                                            'tradingTime': obj['tradingHours'],
                                            'type': obj['assetType']})
                    else:
                        continue

                with open(file_path, 'w') as writer:
                    writer.write(json.dumps(
                        sorted(tempSymbols, key=lambda i: i['code'])))

        for row in tempSymbols:
            if code and row['code'] != code:
                continue
            elif name and name.lower() not in row['name'].lower():
                continue
            elif status and row['status'] != status:
                continue
            elif type and row['assetType'] != type:
                continue
            else:
                symbols.append(Symbol(
                    code=row['code'], name=row['name'], status=row['status'], tradingTime=row['tradingTime'], type=row['type']))

        return symbols

    def __getKlines(self, symbol, interval, limit):
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        response = requests.get(
            "https://api-adapter.backend.currency.com/api/v2/klines", params=params)

        if response.status_code == 200:
            # if constant.WRITE_REQUEST_TO_FILE == True:
            #     with open(getFileName(self._symbol, tfId), 'w') as writer:
            #         writer.write(response.text)

            return json.loads(response.text)
        else:
            raise Exception(response.text)
