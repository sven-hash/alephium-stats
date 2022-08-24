# Alephium stats

The purpose of this repo is to share the code and give some explanation about data published by the endpoints

[alph-top.web.app](https://alph-top.web.app/) use the API to list the top 256 wallets

## Actual endpoints

- [https://alephium.ono.re/api/stats/peers](https://alephium.ono.re/api/stats/peers)

   Fullnodes that are seen by node-alephium.ono.re with information: 
   - IP (not activated for privacy reasons)
   - Physical location
   - First and last connection
   - Synched or not
   - Reacheable or not
   

- [https://alephium.ono.re/api/stats/addresses](https://alephium.ono.re/api/stats/addresses)
  
  **Options**
  - `human`: not in set representation
  - `top`: limit the number of wallet to show
    
  Lists the wallets where an amount of ALPH had been received or withdrawed. Sorted by the largest to smallest wallet
   - total balance
   - total locked balance
   
  And there some global additionnal informations like:
   - `active_addresses` who count the number of wallet who had or made some transfers
   - `total_locked` total ALPH locked
   - `total_balance` total ALPH locked+unlocked

- https://alephium.ono.re/api/stats/genesis

  This is the wallet list of genesis addresses with the amount at the time of the genesis block and the current balance and locked balance


## Run your own server


```bash
cp .env.example .env
docker-compose --build up -d
```
