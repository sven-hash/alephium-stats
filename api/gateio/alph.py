import requests
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from pprint import pprint
from dotenv import load_dotenv
import os



class GateIoAPI():

    def __init__(self, apiUrl, symbols=[], apiKey="", secretKey=""):
        self.apiURL = apiUrl
        self.symbols = symbols
        self.apiKey = apiKey
        self.secretKey = secretKey
        self.session = Session()

        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        self.session.headers.update(headers)

    def getCurrencyPairs(self):

        pairsSelect = []
        url = f'spot/currency_pairs'

        try:
            r = self.session.get(f"{self.apiURL}/{url}")
            allPairs = r.json()
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            print(e)

        pairs = (list((filter(lambda x: x['base'] == self.symbols[0], allPairs))))
        for pair in pairs:
            pairsSelect.append(pair['id'])
        return pairsSelect


    def getPriceTokensFixedPairs(self,pairs):

        pairTickerPrice = {}
        url = f'spot/tickers'
        pairsData = dict()

        try:
            for pair in pairs:
                query_param = f'currency_pair={pair}'
                r = self.session.get(f"{self.apiURL}/{url}", params=query_param)
                tickers = r.json()

                if type(tickers) == list:
                    pairsData.update({pair:tickers[0]})
                elif tickers.get('label') == 'INVALID_CURRENCY_PAIR':
                    pairTickerPrice[pair] = f'Error {tickers.get("message")}'
                else:
                    pairTickerPrice[pair] = f'Error {tickers}'

        except (ConnectionError, Timeout, TooManyRedirects) as e:
            print(e)

        return pairsData

    def getPriceTokens(self, pairs):

        pairTickerPrice = {}
        url = f'spot/tickers'
        query_param = f''

        try:
            r = self.session.get(f"{self.apiURL}/{url}", params=query_param)
            tickers = r.json()

        except (ConnectionError, Timeout, TooManyRedirects) as e:
            print(e)

        for pair in pairs:
            data = list(filter(lambda x: x['currency_pair'] == pair, tickers))
            if len(data) > 1:
                pairTickerPrice[data[0]['currency_pair']] = float(data[0]['last'])
            else:
                return {'Error':f"{pairs} not exist"}

        return pairTickerPrice


if __name__ == "__main__":
    SYMBOLS = ['ETH']
    BASE_URL = "https://api.gateio.ws/api/v4"

    price = GateIoAPI(BASE_URL, SYMBOLS, os.getenv('apiKey'), os.getenv('secretKey'))
    pairs = price.getCurrencyPairs()
    print(price.getPriceTokens(['ALPH_USDT']))
