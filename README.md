# token-supply-endpoint

This repository hosts google cloud functions for estimating circulating token
supply, one per top-level folder.

To deploy:

+ Choose "Allow unauthenticated invocations" when given the choice since it's a
  public api.
+ The google cloud function needs to have an environment variabable set:
  `WEB3_PROVIDER_URI=https://eth-mainnet.alchemyapi.io/v2/<secret>`. It doesn't
  have to be alchemy, but this is hard-coded for mainnet.
+ Copy all the files to the google cloud function source and set the entry
  point to `main`.

To test locally: 

+ set `WEB3_PROVIDER_URI=https://eth-mainnet.alchemyapi.io/v2/<secret>` (or
  whatever mainnet provider you want - I used
  [alchemy](https://www.alchemy.com/)) in the command line.
  [direnv](https://direnv.net/) is fantastic for this and is ignored in
  `.gitignore`.
+ modify main.py to call `print(main({}))`
+ run `$ pip install -r requirements.txt`
+ run `$ python main.py`
