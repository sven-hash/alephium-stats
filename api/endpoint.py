import logging
import os
import threading
import time
from datetime import datetime, date, timedelta

import schedule
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_restful import Resource, Api
from cachetools import cached, TTLCache

from cmc.alph import CmcAPI
from coingecko.alph import CoingeckoAPI
from gateio.alph import GateIoAPI
from stats.blockchain import updateStats
from stats.db import BaseModel, create_tables
from utils import Utils

app = Flask(__name__)
api = Api(app)

BASE_URL = "https://api.gateio.ws/api/v4"
CMC_BASE_URL = "https://pro-api.coinmarketcap.com/v1"
COIN_GECKO_BASE_URL = "https://api.coingecko.com/api/v3"

MAINNET_START = datetime(2021, 11, 8)

load_dotenv()

CMC_API_KEY = os.getenv('CMC_API_KEY')

cache = TTLCache(maxsize=10 ** 9, ttl=120)
log_file_format = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
main_logger = logging.getLogger('db')
main_logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_file_format))
main_logger.addHandler(console_handler)


class TickerPrice(Resource):

    def get(self):
        gateio = GateIoAPI(BASE_URL)
        coingecko = CoingeckoAPI(COIN_GECKO_BASE_URL, symbols=['alephium'])

        data = gateio.getPriceTokensFixedPairs(['ALPH_USDT'])
        data.update(coingecko.getPriceTokens())

        if CMC_API_KEY is not None:
            cmc = CmcAPI(CMC_BASE_URL, ['USD'], ['ALPH'], CMC_API_KEY)
            data.update(cmc.getPriceTokens())

        return jsonify(data)


class AddressesStats(Resource):
    def get(self):
        topAddresses = request.args.get('top', type=int, default=0)
        page = request.args.get('page', type=int, default=None)
        size = request.args.get('size', type=int, default=10)
        humanFormat = True if request.args.get('human') is not None else False

        if page is not None:
            data = self.read_data(topAddresses, humanFormat, page, size)
        elif topAddresses > 0:
            data = self.read_data(topAddresses, humanFormat)
        else:
            data = self.read_data(topAddresses, humanFormat)

        response = jsonify(data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    @cached(cache={})
    def read_data(self, topAddresses, hint, page=None, size=None):
        data = {}
        human = {}
        db = BaseModel()

        totalLocked = db.getTotalLocked()
        totalBalance = db.getTotalBalance()
        data.update({
            "active_addresses": db.countAddresses(),
            "total_locked": totalLocked,
            "total_balance": totalBalance,
            "last_update": datetime.fromtimestamp(db.getTimeLastInsert()),
        })

        if hint:
            human.update({
                "total_locked": f"{Utils.humanFormat(totalLocked / (10 ** 18))} ALPH",
                "total_balance": f"{Utils.humanFormat(totalBalance / (10 ** 18))} ALPH"
            })
            data.update({"hint": human})

        allAddresses = db.getOrderedBalanceAddresses(topAddresses, page, size)

        for addr in allAddresses:
            addr.update({'balanceHint': f"{Utils.humanFormat(addr['balance'] / (10 ** 18))} ALPH"})
            addr.update({'lockedHint': f"{Utils.humanFormat(addr['locked'] / (10 ** 18))} ALPH"})

        data.update({"addresses": allAddresses})
        return data


class GenesisStats(Resource):
    def get(self):

        data = self.read_data()
        response = jsonify(data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    @cached(cache={})
    def read_data(self):

        startDate = MAINNET_START
        while startDate + timedelta(days=90) <= datetime.utcnow():
            startDate = startDate + timedelta(days=91)

        startDate = startDate + timedelta(days=90)

        db = BaseModel()
        data = {"next_vesting_release": startDate}

        data.update({"genesis_addresses": db.getGenesis()})

        for addr in data["genesis_addresses"]:
            addr.update({'balanceHint': f"{Utils.humanFormat(addr['balance'] / (10 ** 18))} ALPH"})
            addr.update({'balanceGenesisHint': f"{Utils.humanFormat(addr['balanceGenesis'] / (10 ** 18))} ALPH"})
            addr.update({'lockedHint': f"{Utils.humanFormat(addr['locked'] / (10 ** 18))} ALPH"})

        return data


class TxHistoryStats(Resource):
    def get(self,address=None):
        page = request.args.get('page', type=int, default=None)
        size = request.args.get('size', type=int, default=10)
        data = self.read_data(page, size, address)
        response = jsonify(data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    @cached(cache={})
    def read_data(self,page, size, address=None):
        db = BaseModel()

        return db.getTxAddress(page, size, address)


class PeersStats(Resource):
    def get(self):
        data = self.read_data()
        response = jsonify(data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    @cached(cache={})
    def read_data(self):
        db = BaseModel()

        return db.getPeers()


class Name(Resource):
    def get(self):
        data = self.read_data()
        response = jsonify(data)
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    @cached(cache={})
    def read_data(self):
        db = BaseModel()

        return db.getNames()


def update():
    create_tables()
    main_logger.info('Start DB update thread')
    schedule.every().minutes.do(updateStats)
    while True:
        schedule.run_pending()
        time.sleep(60)


th = threading.Thread(target=update)
th.start()

api.add_resource(TickerPrice, '/api/ticker')
api.add_resource(AddressesStats, '/api/stats/addresses')
api.add_resource(GenesisStats, '/api/stats/genesis')
# api.add_resource(PeersStats, '/api/stats/peers')
api.add_resource(Name, '/api/known-wallets/')
api.add_resource(TxHistoryStats, '/api/stats/tx-history','/api/stats/tx-history/<string:address>')

if __name__ == '__main__':
    host = '0.0.0.0'

    app.run(debug=False, port='8080', host=host)
