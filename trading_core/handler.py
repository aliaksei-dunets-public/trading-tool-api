from datetime import datetime
import requests
import json
import pandas as pd
import os

from .core import Symbol, HistoryData


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

        symbols = []
        symbols_df = pd.DataFrame()

        file_path = f'{os.getcwd()}\static\symbols_df.json'

        if isBuffer and os.path.exists(file_path):
            symbols_df = pd.read_json(file_path)

        if symbols_df.empty:
            response = requests.get(
                "https://api-adapter.backend.currency.com/api/v2/exchangeInfo")

            if response.status_code == 200:
                jsonResponse = json.loads(response.text)

                df = pd.DataFrame(jsonResponse['symbols'])
                df_cleared = df.query(
                    "quoteAssetId == 'USD' and assetType in ('CRYPTOCURRENCY','EQUITY','COMMODITY')")
                symbols_df = df_cleared[['symbol', 'name',
                                         'tradingHours', 'assetType', 'status']]
                symbols_df.set_index('symbol', inplace=True)

                symbols_df.to_json(file_path, orient="records")

        for index, row in symbols_df.iterrows():
            if code and index != code:
                continue
            if name and name.lower() not in row['name'].lower():
                continue
            if status and row['status'] != status:
                continue
            elif type and row['assetType'] != type:
                continue

            symbols.append(Symbol(
                code=index, name=row['name'], status=row['status'], tradingTime=row['tradingHours'], type=row['assetType']))

        return symbols

    def __getKlines(self, symbol, interval, limit):
        params = {"symbol": symbol,
                  "interval": interval,
                  "limit": limit}
        response = requests.get(
            "https://api-adapter.backend.currency.com/api/v2/klines", params=params)

        if response.status_code == 200:
            # if constant.WRITE_REQUEST_TO_FILE == True:
            #     with open(getFileName(self._symbol, tfId), 'w') as writer:
            #         writer.write(response.text)

            return json.loads(response.text)
        else:
            raise Exception(response.text)
