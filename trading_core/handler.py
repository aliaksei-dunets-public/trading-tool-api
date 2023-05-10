from datetime import datetime, timedelta
import requests
import json
import pandas as pd
import os
import logging
import math

from .core import Symbol, HistoryData

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class HandlerBase:
    def getHistoryData(self, symbol, interval, limit, closedBar: bool = False) -> HistoryData:
        pass

    def getSymbols(self, code: str = None, name: str = None, status: str = None, type: str = None, isBuffer: bool = True) -> list:
        pass

    def getSymbolsDictionary(self, isBuffer: bool = True) -> dict:

        dictSymbols = {}
        listSymbols = []

        file_path = f'{os.getcwd()}/static/symbolsDictionary.json'

        if isBuffer and os.path.exists(file_path):
            with open(file_path, 'r') as reader:
                dictSymbols = json.load(reader)

        if not dictSymbols:
            listSymbols = self.getSymbols(isBuffer=isBuffer)

            for symbol in listSymbols:
                dictSymbols[symbol.code] = symbol.__dict__

            with open(file_path, 'w') as writer:
                writer.write(json.dumps(dictSymbols))

        return dictSymbols

    def getIntervalsDetails(self) -> list:
        return []

    def _mapInterval(self, interval) -> str:
        return interval


class HandlerCurrencyCom(HandlerBase):
    def getHistoryData(self, symbol, interval, limit, closedBar) -> HistoryData:

        logging.info(
            f'getHistoryData(symbol={symbol}, interval={interval}, limit={limit})')

        response = self.__getKlines(
            symbol, self._mapInterval(interval), limit, closedBar)

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
        tempSymbols = []

        file_path = f'{os.getcwd()}/static/symbols.json'

        if isBuffer and os.path.exists(file_path):
            with open(file_path, 'r') as reader:
                tempSymbols = json.load(reader)

        if not tempSymbols:

            logging.info(
                f'getSymbols(code={code}, name={name}, status={status}, type={type}, isBuffer={isBuffer})')

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

    def __getKlines(self, symbol, interval, limit, closedBar: bool):
        params = {"symbol": symbol, "interval": interval, "limit": limit}

        if closedBar:
            params["endTime"] = self.__getCompletedUnixTimeMs(interval)

        response = requests.get(
            "https://api-adapter.backend.currency.com/api/v2/klines", params=params)

        if response.status_code == 200:
            # if constant.WRITE_REQUEST_TO_FILE == True:
            #     with open(getFileName(self._symbol, tfId), 'w') as writer:
            #         writer.write(response.text)

            return json.loads(response.text)
        else:
            raise Exception(response.text)
    
    def getOffsetDateTimeByInterval(self, interval, current_datetime: datetime = datetime.now()):

        if not isinstance(current_datetime, datetime):
            raise ValueError("Input parameter must be a datetime.datetime object.")
        
        if interval in ['5m', '15m', '30m']:
            current_minute = current_datetime.minute
            
            if interval == '5m':
                offset_value = 5
            elif interval == '15m':
                offset_value = 15
            elif interval == '30m':
                offset_value = 30

            delta_minutes = current_minute % offset_value + offset_value
            
            offset_date_time = current_datetime - timedelta(minutes=delta_minutes)
            offset_date_time = offset_date_time.replace(second=0, microsecond=0)

        elif interval == '1h':

            compared_datetime = current_datetime.replace(hour=0, minute=0, second=30, microsecond=0)
            
            if current_datetime > compared_datetime:
                offset_date_time = current_datetime - timedelta(hours=1)
            else:
                offset_date_time = current_datetime
            
            offset_date_time = offset_date_time.replace(minute=0, second=0, microsecond=0)

        elif interval == '4h':
            
            local_time = datetime.now()
            utc_time = datetime.utcnow() 

            delta = local_time - utc_time
            hours_difference = math.ceil( delta.total_seconds() / 3600 )

            current_hour = current_datetime.hour - hours_difference
            
            offset_value = 4
            
            delta_hours = current_hour % offset_value + offset_value
            offset_date_time = current_datetime - timedelta(hours=delta_hours)
            
            offset_date_time = offset_date_time.replace(minute=0, second=0, microsecond=0)

        elif interval == '1d':

            local_time = datetime.now()
            utc_time = datetime.utcnow() 

            delta = local_time - utc_time
            hours_difference = math.ceil( delta.total_seconds() / 3600 )

            compared_datetime = current_datetime.replace(hour=0, minute=0, second=30, microsecond=0)

            if current_datetime > compared_datetime:
                offset_date_time = current_datetime - timedelta(days=1)
            else:
                offset_date_time = current_datetime
            
            offset_date_time = offset_date_time.replace(hour=hours_difference, minute=0, second=0, microsecond=0)

        elif interval == '1w':

            compared_datetime = current_datetime.replace(hour=0, minute=0, second=30, microsecond=0)
            
            offset_value = 7

            delta_days_until_monday = current_datetime.weekday() % 7 + offset_value
            offset_date_time = current_datetime - timedelta(days=delta_days_until_monday)
            
            offset_date_time = offset_date_time.replace(hour=0, minute=0, second=0, microsecond=0)

        logging.info(f'Closed Bar time - {offset_date_time} for Current Time - {current_datetime}, interval - {interval}')

        return offset_date_time

    def __getCompletedUnixTimeMs(self, interval):
        offset_date_time = self.getOffsetDateTimeByInterval(interval)
        return int(offset_date_time.timestamp() * 1000)
