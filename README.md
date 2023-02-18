# Alephium stats

The purpose of this repo is to share the code and give some explanation about data published by the endpoints

Initial developpement was from [@capito27](https://github.com/capito27)

## Used in

- [alph-top.web.app](https://alph-top.web.app/) list the top 256 wallets

## Actual endpoints
   

- [https://alephium.ono.re/api/stats/addresses](https://alephium.ono.re/api/stats/addresses?top=21)
  
  **Options**
  - `human`: not in set representation
  - `top`: limit the number of wallet to show
  - `page`: page number
  - `size`: number of elements in the page
    
  Lists the wallets where an amount of ALPH had been received or withdrawed. Sorted by the largest to smallest wallet
   - total balance
   - total locked balance
   
  And there some global additionnal informations like:
   - `active_addresses` who count the number of wallet who had or made some transfers
   - `total_locked` total ALPH locked
   - `total_balance` total ALPH locked+unlocked

- [https://alephium.ono.re/api/stats/tx-history](https://alephium.ono.re/api/stats/tx-history)
   - list the first and last transactions for all of the active 1addresses
    
   It's possible to get tx history for one address: [https://alephium.ono.re/api/stats/tx-history/<address>](https://alephium.ono.re/api/stats/tx-history/<address>)

   **Options**
   - `page`: page number                   - `
   - `size`: number of elements in the page


- [https://alephium.ono.re/api/known-wallets/](https://alephium.ono.re/api/known-wallets/)
   - list the [known wallets addresses](https://github.com/sven-hash/address2name)
   
- [https://alephium.ono.re/api/stats/genesis](https://alephium.ono.re/api/stats/genesis)

  This is the wallet list of genesis addresses with the amount at the time of the genesis block and the current balance and locked balance

- [https://alephium.ono.re/api/ticker](https://alephium.ono.re/api/ticker)
  
  Price informations about ALPH ticker

## Run your own server


```bash
cp .env.example .env
docker-compose --build up -d
```
