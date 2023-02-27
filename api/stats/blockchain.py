# From https://github.com/capito27
import asyncio
import codecs
import csv
import json
import logging
import math
import os
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta
from os.path import join
import csv
import aiohttp
import backoff
import requests
from aiohttp import ClientTimeout
from dotenv import load_dotenv

import utils
from stats.db import BaseModel
from tqdm import tqdm
import aiostream

###### CONFIG

load_dotenv(dotenv_path=join(".env"))

IPINFO_TOKEN = os.getenv('IPINFO_TOKEN')
FULLNODE_ENDPOINT = os.getenv('FULLNODE_ENDPOINT', "node-alephium.ono.re")
# Base path of an Alephium full node
API_BASE = f"http://{FULLNODE_ENDPOINT}"
API_MAINNET = "https://backend.mainnet.alephium.org"
# API_MAINNET = "https://alephium-backend.ono.re"

# Speeds up the initial address dump phase
SAVE_KNOWN_ADDRESSES = True

# Ignores mining wallets when dumping the known addresses
IGNORE_MINING_ADDRESSES = False

###### END CONFIG

GENESIS_TS = 1231006504
FIRST_BLOCK_TS = 1636383298

LOCKED_INCLUDED = True
SOFT_CAP = 140. * 10 ** 6
HARD_CAP = 1 * 10 ** 9
ALPH = '\u2135'

db = BaseModel()

main_logger = logging.getLogger('db')

addressToBalance = {}
addressToBalanceWithoutLocked = {}
addressToBalanceLocked = {}
addressBlacklist = set()
circulating_supply = 0


def humanFormat(num, round_to=2):
    # From https://stackoverflow.com/questions/579310/formatting-long-numbers-as-strings-in-python
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num = round(num / 1000.0, round_to)
    return '{:.{}f} {}'.format(num, round_to, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])


def get_txs(s, addr, depth=0):
    max_depth = 2

    destinations = {}

    if depth >= max_depth:
        return
    depth += 1
    try:

        response = s.get(f"{API_MAINNET}/addresses/{addr}/transactions")
        if response.ok:
            data = response.json()

            for tx in data:
                for input in tx['inputs']:
                    addressIn = input['address']

                if len(tx['inputs']) > 0 and addressIn == addr:
                    for output in tx['outputs']:
                        addressOut = output['address']
                        if addressIn != addressOut:
                            amount = float(output['amount']) / (10. ** 18)
                            try:
                                destinations[addressOut] += amount
                            except KeyError:
                                destinations[addressOut] = amount

                            # send_tx = get_txs(s,addressOut,depth=depth)
                            # if send_tx is not None:
                            #    destinations.update(send_tx)

            return destinations
        else:
            return destinations

    except requests.RequestException as e:
        print(e)
        return None


def get_known_addresses():
    CSV_URL = "https://raw.githubusercontent.com/sven-hash/address2name/main/known-wallets.txt"
    VERIFIED_STRING = "verified"

    s = requests.Session()
    data = s.get(CSV_URL, stream=True)
    reader = csv.reader(codecs.iterdecode(data.iter_lines(), 'utf-8'), delimiter=';')

    for row in reader:
        address = row[0]
        name = row[1]
        state = row[2]

        if VERIFIED_STRING in state:
            state = row[2].split("#")[0]

        exchangeName = None
        if len(row) >= 4:
            exchangeName = row[3]

        type = None
        if len(row) >= 5:
            type = row[4]

        db.insertName(address, name, exchangeName, state, type)


def get_peers():
    main_logger.info('Start Peers update process')
    s = requests.Session()
    ipPeers = dict()
    try:
        response = s.get(f"{API_BASE}/infos/discovered-neighbors")
        peer_clique_info = s.get(f"{API_BASE}/infos/inter-clique-peer-info").json()
        unreachablePeers = s.get(f"{API_BASE}/infos/unreachable").json()

        if response.ok:
            for peer in response.json():
                ip = peer['address']['addr']

                ipinfos = utils.Utils.getCountry(ip, s, IPINFO_TOKEN)
                if ipinfos:
                    peer_version = next(
                        (item['clientVersion'] for item in peer_clique_info if item["cliqueId"] == peer['cliqueId']),
                        None)
                    isSynced = next(
                        (item['isSynced'] for item in peer_clique_info if item["cliqueId"] == peer['cliqueId']),
                        False)
                    unreachable = True if ip in unreachablePeers else False

                    ipPeers.update({ip: [
                        ipinfos,
                        {'version': peer_version},
                        {'isSynced': isSynced},
                        {'unreachable': unreachable}
                    ]})

        else:
            return None
    except requests.RequestException as e:
        print(e)
        return None

    if ipPeers:
        db.insertManyPeer(ipPeers)


def get_genesis_initial_amount():
    main_logger.info('Start genesis update')
    with open("stats/mainnet_genesis.conf") as json_file:
        data = json.load(json_file)

    genesis_initial = dict()

    for addr in data:
        try:
            genesis_initial[addr['address']] += float(addr['amount'].split(" ")[0]) * (10. ** 18)
        except KeyError:
            genesis_initial[addr['address']] = float(addr['amount'].split(" ")[0]) * (10. ** 18)

    for addr, amount in genesis_initial.items():
        db.insertGenesis(addr, amount)


@backoff.on_exception(backoff.expo, (requests.exceptions.ConnectionError, requests.exceptions.Timeout), max_tries=15)
def get_circulating_supply():
    if circulating_supply > 0:
        return circulating_supply

    s = requests.Session()
    try:
        response = s.get(f"{API_MAINNET}/infos/supply/circulating-alph")

        if response.ok:
            return float(response.content)
        else:
            return None
    except requests.RequestException as e:
        print(e)
        return None


def dump_address_from_TS_range(start, end, s):
    response = s.get(f"{API_BASE}/blockflow/blocks?fromTs={start * 1000}&toTs={end * 1000}")
    for inner_blocks in response.json()['blocks']:
        for block in inner_blocks:
            for tx in block['transactions']:
                # if we're ignoring mining addresses, blacklist all output addresses and continue
                if IGNORE_MINING_ADDRESSES and len(tx['unsigned']['inputs']) == 0:
                    for out in tx['unsigned']['fixedOutputs']:
                        addressBlacklist.add(out['address'])
                    continue
                for out in tx['unsigned']['fixedOutputs']:
                    addressToBalance.setdefault(out['address'], 0)


def scrape_all_addresses():
    # use session to speedup requests
    s = requests.Session()
    # manually dump the genesis addresses
    dump_address_from_TS_range(GENESIS_TS, GENESIS_TS + 5, s)
    for ts_start in range(FIRST_BLOCK_TS, int(time.time()), 60 * 60):  # only supports ranges of 30 minutes or less
        print(ts_start, ts_start + 60 * 60)
        dump_address_from_TS_range(ts_start, ts_start + 60 * 60, s)


def scrape_new_addresses(start_point):
    # use session to speedup requests
    s = requests.Session()

    for ts_start in range(start_point, int(time.time()), 60 * 30):  # only supports ranges of 30 minutes or less
        dump_address_from_TS_range(ts_start, ts_start + 60 * 30, s)


def get_addresses():
    # If we're supposed to save the known addresses, check if there is already a saved file and load it
    start_point = db.getTimeLastInsert()
    print(start_point)
    main_logger.info('Start addresses update')
    if start_point is not None:
        scrape_new_addresses(start_point)
    else:
        scrape_all_addresses()

    # In all cases, remove any blacklisted addresses
    for address in addressBlacklist:
        addressToBalance.pop(address, None)


# from https://stackoverflow.com/questions/62294385/synchronous-generator-in-asyncio
def async_wrap_iter(it):
    """Wrap blocking iterator into an asynchronous one"""
    loop = asyncio.get_event_loop()
    q = asyncio.Queue(1)
    exception = None
    _END = object()

    async def yield_queue_items():
        while True:
            next_item = await q.get()
            if next_item is _END:
                break
            yield next_item
        if exception is not None:
            # the iterator has raised, propagate the exception
            raise exception

    def iter_to_queue():
        nonlocal exception
        try:
            for item in it:
                # This runs outside the event loop thread, so we
                # must use thread-safe API to talk to the queue.
                asyncio.run_coroutine_threadsafe(q.put(item), loop).result()
        except Exception as e:
            exception = e
        finally:
            asyncio.run_coroutine_threadsafe(q.put(_END), loop).result()

    threading.Thread(target=iter_to_queue).start()
    return yield_queue_items()


def find_historical_tx(txs, address):
    tx_send = None
    tx_recv = None

    for tx in txs:

        if len(tx.get('inputs')) <= 0:
            if tx_recv is None:
                tx_recv = tx['timestamp'] / 1000

        for input in tx.get('inputs'):

            if input['address'] == address and tx_send is None:
                tx_send = tx['timestamp'] / 1000

            if input['address'] != address and tx_recv is None:
                tx_recv = tx['timestamp'] / 1000

    return tx_send, tx_recv


def get_number_page(s, address, limit):
    try:
        num_tx = s.get(f"{API_MAINNET}/addresses/{address}/total-transactions").json()
    except requests.RequestException as e:
        traceback.print_exc()
        return 0

    return math.ceil(num_tx / limit)


async def fetch(session, url, timeout=30, reverse=False):
    async with session.get(url, allow_redirects=True, timeout=timeout) as resp:
        try:
            data = await resp.json()
            # time.sleep(2 / 1000)

            if resp.ok:

                if reverse:
                    data.reverse()

                addr = url.split('/')[4]
                return {addr: find_historical_tx(data, addr)}

            else:
                return None
        except (requests.RequestException, asyncio.TimeoutError) as e:
            return None


async def worker(queue, session, results, timeout=30, reverse=False):
    while True:
        url = await queue.get()
        try:
            results.append(await fetch(session, url, timeout=timeout, reverse=reverse))
        except asyncio.CancelledError as err:
            pass
        finally:
            # Mark the item as processed, allowing queue.join() to keep
            # track of remaining work and know when everything is done.
            queue.task_done()


async def get_last_txs(addressesList, urls=None, reverse=False):
    addrTxUrl = list()
    for addr in addressesList:
        address = addr['address']
        if urls is None:
            addrTxUrl.append(f"{API_MAINNET}/addresses/{address}/transactions?page=1&limit=100")
        else:
            addrTxUrl = urls

    WORKER = 300
    queue = asyncio.Queue(WORKER)
    results = []
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=WORKER)) as session:
        workers = [asyncio.create_task(worker(queue, session, results, timeout=10, reverse=reverse)) for _ in
                   range(WORKER)]

        async for batch in async_wrap_iter(addrTxUrl):
            await queue.put(batch)

        # Wait for all enqueued items to be processed.
        main_logger.info("done")
        await queue.join()
        main_logger.info("done")

        # The workers are now idly waiting for the next queue item and we
        # no longer need them.
        for runningWorker in workers:
            runningWorker.cancel()

    return results


async def get_tx_history():
    s = requests.Session()
    allAddresses = db.getTxAddressToUpdate(datetime.utcnow() - timedelta(minutes=120))

    if len(allAddresses) <= 0:
        allAddresses = db.getAllAddresses()

    main_logger.info(f'Start last txs update. Number to update: {len(allAddresses)}')
    count = 0

    allTxs = await get_last_txs(addressesList=allAddresses)
    addressesTxs = list()

    for addresses in allTxs:
        if type(addresses) == dict:
            for address, tx in addresses.items():
                addressesTxs.append(
                    {'address': address, 'first_tx_send': None, 'first_tx_recv': None, 'last_tx_send': tx[0],
                     'last_tx_recv': tx[1], 'updated_on': datetime.utcnow()})
        else:
            count += 1
    main_logger.info(f"tx error: {count}")
    db.insertTxHistory(addressesTxs)

    urls = list()
    addressesTxs = list()

    allAddresses = db.getTxAddressWithoutFirst()
    main_logger.info(f'Start first txs update. Number to update: {len(allAddresses)}')

    for addr in allAddresses:
        address = addr['address']
        page = get_number_page(s, address, 100)
        urls.append(f"{API_MAINNET}/addresses/{address}/transactions?page={page}&limit=100")

    allTxs = await get_last_txs(addressesList=allAddresses, urls=urls, reverse=True)

    count = 0

    for addresses in allTxs:
        if type(addresses) == dict:
            for address, tx in addresses.items():
                addressesTxs.append(
                    {'address': address, 'first_tx_send': tx[0],
                     'first_tx_recv': tx[1], 'last_tx_send': None,
                     'last_tx_recv': None, 'updated_on': datetime.utcnow()})
        else:
            count += 1
    main_logger.info(f"tx error: {count}")

    db.insertTxHistory(addressesTxs)


async def getBalances(urls):
    main_logger.info("Get balances")

    WORKER = 50
    queue = asyncio.Queue(WORKER)
    results = []

    async with aiohttp.ClientSession() as session:
        workers = [asyncio.create_task(workerBalance(queue, session, results, timeout=10)) for _ in
                   range(WORKER)]

        async for url in async_wrap_iter(urls):
            await queue.put(url)

        main_logger.info("done")

        # Wait for all enqueued items to be processed.
        await queue.join()
        #await asyncio.gather(*workers)
        #
        main_logger.info("done")
        # The workers are now idly waiting for the next queue item and we
        # no longer need them.
        for runningWorker in workers:
            runningWorker.cancel()

    return results


async def fetchBalance(session, url, timeout=30):
    response = await session.get(url, allow_redirects=True, timeout=timeout)

    try:
        if response.ok:
            data = await response.json()

            addr = url.split('/')[4]
            return {addr: data}

        else:
            return None

    except (requests.RequestException, asyncio.TimeoutError) as e:
        return None


async def workerBalance(queue, session, results, timeout=30):
    while True:
        url = await queue.get()
        try:
            results.append(await fetchBalance(session, url, timeout=timeout))
        except asyncio.CancelledError as err:
            pass
        finally:
            # Mark the item as processed, allowing queue.join() to keep
            # track of remaining work and know when everything is done.
            queue.task_done()



async def get_all_balances():
    # use session to speedup requests

    allAddresses = db.getAddressByDate(datetime.now() - timedelta(minutes=30))
    addressBalances = list()
    main_logger.info(f'Start balances update. Number to update: {len(allAddresses)}')

    urls = []
    for v in allAddresses:
        address = v['address']

        urls.append(f"{API_MAINNET}/addresses/{address}/balance")

    allBalances = await getBalances(urls)
    count = 0
    for data in allBalances:
        if type(data) == dict:
            for address, balanceData in data.items():
                balance = float(balanceData['balance'])
                locked = float(balanceData['lockedBalance'])

                addressBalances.append(
                    {'address': address, 'balance': balance, 'locked': locked, "updated_on": datetime.now()})

        else:
            count += 1
    main_logger.info(f"balance error: {count}")

    db.updateBalance(addressBalances)
    main_logger.info('Balances update done')


def print_top_whales(count=100):
    idx = 1

    print(f"current top-{count} whales in as of {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    for k, v in sorted(addressToBalance.items(), key=lambda item: -item[1])[:count]:
        print(f"{idx}: {k} with {v:.3f} ALPH (locked amount {addressToBalanceLocked[k]} ALPH)")
        idx += 1


def updateStats():
    main_logger.info('Start DB update process')
    try:
        # get_peers()
        get_addresses()
        db.insertManyAddress(addressToBalance.keys())
        get_known_addresses()
        asyncio.run(get_all_balances())
        asyncio.run(get_tx_history())
    except Exception as e:
        main_logger.exception(e)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print(
        f"Alephium network Whale Watch. Ignore mining wallets : {IGNORE_MINING_ADDRESSES}. Locked token removed from address balance: {LOCKED_INCLUDED}")

    get_addresses()

    db.insertManyAddress(addressToBalance.keys())

    get_all_balances()

    # get_genesis_initial_amount()
    # get_pool_miner()
    # circulating_supply = get_circulating_supply()
    totalBalance = db.getTotalBalance()
    totalLocked = db.getTotalLocked()
    print(
        f"There are currently {db.countAddresses()} {'non-mining wallets' if IGNORE_MINING_ADDRESSES else 'wallets'} in the blockchain")
    if LOCKED_INCLUDED:
        print(f"Total balance amount: {humanFormat(totalBalance / (10 ** 18))} ALPH")
        print(f"Total locked amount: {humanFormat(totalLocked / (10 ** 18))} ALPH")
        print(f"Total non-locked amount: {humanFormat((totalBalance - totalLocked) / (10 ** 18))} ALPH")
