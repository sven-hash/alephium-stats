import time
import humanize
from datetime import datetime
from requests import Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects


class CoingeckoAPI():

    def __init__(self, apiUrl, symbols, fiats=None):
        self.apiURL = apiUrl
        self.fiats = fiats
        self.symbols = symbols

    def getPriceTokens(self):
        headers = {
            'accept': 'application/json',
        }

        for symbol in self.symbols:
            session = Session()
            session.headers.update(headers)

            try:
                response = session.get(f"{self.apiURL}/coins/{symbol}?community_data=false")
                try:
                    data = response.json()['market_data']
                except KeyError:
                    return {'coingecko':response.json()}

                if response.ok:
                    allData = {'coingecko':self.selectData(data,symbol)}
                else:
                    return {'coingecko':response.json()}

                return allData
            except (ConnectionError, Timeout, TooManyRedirects) as e:
                print(e)


    def selectData(self,data,symbol):
        cleanData = {}
        fiats = ['usd', 'eur', 'gbp', 'chf']

        ath = self.athCurrencies(data['ath'],fiats)

        athDate = datetime.strptime(data.get('ath_date')['usd'], '%Y-%m-%dT%H:%M:%S.%fZ')

        athRelativeDate = humanize.naturaltime(athDate)

        currentPrices = self.currentPriceCurrencies(data.get('current_price'),fiats)

        cleanData[symbol] = {'ath':ath}
        cleanData[symbol].update({'ath_relative_date':athRelativeDate})
        cleanData[symbol].update({'ath_date': data.get('ath_date')['usd']})
        cleanData[symbol].update({'current_prices':currentPrices})
        cleanData[symbol].update({'change_24':data['price_change_24h']})
        cleanData[symbol].update({'market_cap':data['market_cap']['usd']})
        cleanData[symbol].update({'market_cap_change_24': data['market_cap_change_24h']})

        return cleanData

    def currentPriceCurrencies(self,currentPrices,fiats):
        data = {}
        for fiat in fiats:
            try:
                data.update({fiat:currentPrices[fiat]})
            except KeyError:
                data = 0

        return data

    def athCurrencies(self,aths,fiats):
        data = {}
        for fiat in fiats:
            try:
                data.update({fiat:aths[fiat]})
            except KeyError:
                data = 0

        return data

