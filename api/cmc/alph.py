from requests import Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects


class CmcAPI():

    def __init__(self, apiUrl, fiats, symbols, apiKey):
        self.apiURL = apiUrl
        self.fiats = fiats
        self.symbols = symbols
        self.apiKey = apiKey

    def getPriceTokens(self):
        allData = {}
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.apiKey,
        }

        for fiat in self.fiats:
            parameters = {
                'convert': fiat,
                'symbol': ','.join(map(str,self.symbols))
            }

            session = Session()
            session.headers.update(headers)

            try:
                response = session.get(f"{self.apiURL}/cryptocurrency/quotes/latest", params=parameters)
                try:
                    data = response.json()['data']
                except KeyError as e:
                    return {'cmc':response.json()}

                for symbol in self.symbols:
                    if data[symbol]['is_active'] == 1:
                        allData.update({'cmc':data})
                    else:
                        return f"{symbol} is not active"

                return allData
            except (ConnectionError, Timeout, TooManyRedirects) as e:
                print(e)


if __name__ == "__main__":
    CONVERT_FIAT = ['CHF', 'USD']
    SYMBOLS = ['ALPH']
    BASE_URL = 'https://pro-api.coinmarketcap.com/v1'

    price = CmcAPI(BASE_URL, CONVERT_FIAT, SYMBOLS, '876631df-bae8-4b55-bc71-7ab92ff63f96')
    print(price.getPriceTokens())
