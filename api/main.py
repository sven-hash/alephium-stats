from stats.blockchain import *
from stats.db import *

if __name__ == '__main__':
    log_file_format = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
    main_logger = logging.getLogger('db')
    main_logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_file_format))
    main_logger.addHandler(console_handler)

    create_tables()
    db = BaseModel()
    #db.getTxAddressWithFirst()
    #db.getTxAddressWithFirst()
    #asyncio.run(get_tx_history())

    for i in range(3):
        asyncio.run(get_tx_history())
        asyncio.run(get_all_balances())

        i+=1

    """
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
        print(f"Total balance amount: {humanFormat(totalBalance / (10**18))} ALPH")
        print(f"Total locked amount: {humanFormat(totalLocked / (10**18))} ALPH")
        print(f"Total non-locked amount: {humanFormat((totalBalance-totalLocked) / (10**18))} ALPH")
    """
