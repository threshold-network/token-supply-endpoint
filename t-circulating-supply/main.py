import json
from datetime import datetime

import requests
from web3.auto import w3

# Token factors
NU_TOKEN_FACTOR = 3.25924249316
KEEP_TOKEN_FACTOR = 4.78318863126

# Addresses
T_TOKEN_ADDRESS = '0xCdF7028ceAB81fA0C6971208e83fa7872994beE5'
T_TREASURY_ADDRESS = '0x9F6e831c8F8939DC0C830C6e492e7cEf4f9C2F5f'
KEEP_TOKEN_ADDRESS = '0x85Eee30c52B0b379b046Fb0F85F4f3Dc3009aFEC'
KEEP_TOKEN_GRANT_ADDRESS = '0x175989c71Fd023D580C65F5dC214002687ff88B7'
NU_TOKEN_ADDRESS = '0x4fE83213D56308330EC302a8BD641f1d0113A4Cc'
MERKLE_DISTRIBUTION_ADDRESS = '0xeA7CA290c7811d1cC2e79f8d706bD05d8280BD37'

# Token supply constants
MAGIC_KEEP_SUPPLY_SUBTRACTOR = 59053770 * (10 ** 18)
INITIAL_T_SUPPLY = 10_000_000_000 * (10 ** 18)  # 10B T
INITIAL_TREASURY_SUPPLY = 1_000_000_000 * (10 ** 18)  # 1B T

# Merkle Distribution
MERKLE_DISTRIBUTION_FILENAME = "MerkleDist.json"


def make_request(request_url: str, verify: bool = True):
    response = requests.get(request_url, verify=verify)
    if response.status_code != 200:
        # TODO is this the best way to indicate an error occurred
        raise Exception(f"Unable to retrieve data from {request_url}")

    return response.json()


def get_total_staking_rewards():

    # TODO only use latest distribution (it has cumulative total)

    # TODO may need GITHUB TOKEN to prevent rate limiting
    distribution_folders = make_request(
        "https://api.github.com/repos/threshold-network/merkle-distribution/contents/distributions"
    )

    # get folder names
    distribution_folder_names = []
    for folder in distribution_folders:
        distribution_folder_names.append(folder['name'])

    # sort folder names by date
    distribution_folder_names.sort(key=lambda date: datetime.strptime(date, "%Y-%m-%d"))

    latest_folder = distribution_folder_names[-1]

    distribution_file = make_request(
        f"https://raw.githubusercontent.com/threshold-network/merkle-distribution/main/distributions/{latest_folder}/{MERKLE_DISTRIBUTION_FILENAME}"
    )
    total_rewards_for_distribution = int(distribution_file['totalAmount'])

    return total_rewards_for_distribution


def get_already_claimed_rewards():
    # TODO would be great to cache the return of this function - doesn't need to be done every time.
    total_claimed = 0
    with open('merkle-distribution.abi') as merkle_distribution_contract_file:
        abi = merkle_distribution_contract_file.read()
        merkle_distribution_contract = w3.eth.contract(address=MERKLE_DISTRIBUTION_ADDRESS, abi=abi)
        events = merkle_distribution_contract.events['Claimed'].getLogs(fromBlock=15146501)  # block that contract was deployed
        for event in events:
            total_claimed += event['args']['amount']

    return total_claimed


def main(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """

    #
    # Total Supply Calcs
    #
    with open('t-contract.abi') as t_contract_file:
        abi = t_contract_file.read()
        t_token_contract = w3.eth.contract(address=T_TOKEN_ADDRESS, abi=abi)
        t_total_supply = t_token_contract.functions.totalSupply().call()

        if request.path == "/total":
            return str(t_total_supply / (10 ** 18))

    #
    # Treasury Supply Calcs
    #
    
    # Staking Rewards
    total_staking_rewards = get_total_staking_rewards()
    claimed_rewards = get_already_claimed_rewards()
    unclaimed_rewards = total_staking_rewards - claimed_rewards

    # Treasury Supply i.e. unused T (including overminted tokens) = CurrentWalletBalance - unclaimed rewards
    t_treasury_current_balance = t_token_contract.functions.balanceOf(T_TREASURY_ADDRESS).call()
    t_treasury_supply = t_treasury_current_balance - unclaimed_rewards

    if request.path == "/treasury":
        return str(t_treasury_supply / (10 ** 18))

    #
    # Circulating Supply Calcs
    #

    # KEEP Tokens Calc
    with open('keep-token.abi') as keep_contract_file:
        abi = keep_contract_file.read()
        keep_token_contract = w3.eth.contract(address=KEEP_TOKEN_ADDRESS, abi=abi)
        keep_total_supply = keep_token_contract.functions.totalSupply().call()

    keep_token_grant = keep_token_contract.functions.balanceOf(
        KEEP_TOKEN_GRANT_ADDRESS).call()
    keep_circulating_supply = keep_total_supply - keep_token_grant - MAGIC_KEEP_SUPPLY_SUBTRACTOR
    circulating_t_from_keep = keep_circulating_supply * KEEP_TOKEN_FACTOR

    # NU Tokens Calc
    nu_circulating_supply = make_request(
        "https://status.nucypher.network/supply_information?q=est_circulating_supply",
        verify=False
    )
    circulating_t_from_nu = nu_circulating_supply * NU_TOKEN_FACTOR * (10 ** 18)

    # Treasury spend = Initial Treasury Supply - (CurrentWalletBalance - unclaimed rewards - overminted tokens)
    total_minted_supply = t_total_supply - INITIAL_T_SUPPLY  # staking rewards + overmint
    overminted_tokens = (total_minted_supply - total_staking_rewards)
    t_treasury_spend = INITIAL_TREASURY_SUPPLY - (
                t_treasury_current_balance - unclaimed_rewards - overminted_tokens)

    # T circulating supply = All unlocked NU * 3.259 + All unlocked KEEP * 4.783 + staking rewards + treasury spend
    circulating_t = circulating_t_from_nu + circulating_t_from_keep + total_staking_rewards + t_treasury_spend
    circulating_t_tokens = circulating_t / (10 ** 18)
    results = {
        'current_total_supply': t_total_supply / (10 ** 18),
        'dao_treasury_supply': t_treasury_supply / (10 ** 18),
        'est_circulating_supply': circulating_t_tokens
    }

    if request.path == "/circulating":
        return str(circulating_t_tokens)
    elif request.path == '/':
        return json.dumps(results)
    else:
        raise Exception(f'Unknown route {request.path}')
