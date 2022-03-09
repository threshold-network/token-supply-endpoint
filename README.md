# token-supply-endpoint

This repository hosts google cloud functions for estimating circulating token
supply, one per top-level folder.

To test locally: 

+ set `WEB3_PROVIDER_URI=https://eth-mainnet.alchemyapi.io/v2/<secret>` (or
  whatever mainnet provider you want - I used
  [alchemy](https://www.alchemy.com/)) in the command line.
  [direnv](https://direnv.net/) is fantastic for this and is ignored in
  `.gitignore`.
+ modify main.py to call `print(main({}))`
+ run `$ pip install -r requirements.txt`
+ run `$ python main.py`
