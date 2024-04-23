import json

import requests
from web3.auto import w3

# Token factors
NU_TOKEN_FACTOR = 3.25924249316  # NU -> T
KEEP_TOKEN_FACTOR = 4.78318863126  # KEEP -> T

WEI_FACTOR = 10 ** 18

# Addresses
T_TOKEN_ADDRESS = "0xCdF7028ceAB81fA0C6971208e83fa7872994beE5"
KEEP_TOKEN_ADDRESS = "0x85Eee30c52B0b379b046Fb0F85F4f3Dc3009aFEC"
KEEP_TOKEN_GRANT_ADDRESS = "0x175989c71Fd023D580C65F5dC214002687ff88B7"
GB_TIMELOCK_CONTROLLER_ADDRESS = "0x87F005317692D05BAA4193AB0c961c69e175f45f"  # T Treasury stored here

# Token supply constants
MAGIC_KEEP_SUPPLY_SUBTRACTOR = 59053770 * WEI_FACTOR
INITIAL_T_SUPPLY = 10_000_000_000 * WEI_FACTOR  # 10B T
INITIAL_TREASURY_SUPPLY = 1_000_000_000 * WEI_FACTOR  # 1B T

NU_CIRCULATING_SUPPLY_ENDPOINT = "https://status.nucypher.network/supply_information?q=est_circulating_supply"

# Merkle Distribution
MERKLE_DISTRIBUTION_SUMMARY_ENDPOINT = f"https://raw.githubusercontent.com/threshold-network/merkle-distribution/main/distributions/distributions.json"


def make_request(request_url: str, verify: bool = True):
    """
    Issues an HTTP GET for the provided request url. If successful, the response data
    is expected to be JSON.
    """
    response = requests.get(request_url, verify=verify)
    if response.status_code != 200:
        # TODO is this the best way to indicate an error occurred
        raise Exception(f"Unable to retrieve data from {request_url}")

    return response.json()


def get_total_staking_rewards():
    """
    Retrieves total staking rewards issued from the threshold/merkle-distribution repos.
    """
    distribution_file = make_request(MERKLE_DISTRIBUTION_SUMMARY_ENDPOINT)
    total_staking_rewards = int(distribution_file["LatestCumulativeAmount"])
    return total_staking_rewards


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
    with open("erc20.abi") as erc20_abi_file:
        abi = erc20_abi_file.read()

    t_token_contract = w3.eth.contract(address=T_TOKEN_ADDRESS, abi=abi)
    t_total_supply = t_token_contract.functions.totalSupply().call()

    if request.path == "/total":
        return str(t_total_supply / WEI_FACTOR)

    #
    # Treasury Supply Calcs
    #
    
    # Treasury Supply i.e. T in Governor Bravo TimeLock Contract
    t_treasury_supply = t_token_contract.functions.balanceOf(GB_TIMELOCK_CONTROLLER_ADDRESS).call()
    if request.path == "/treasury":
        return str(t_treasury_supply / WEI_FACTOR)

    #
    # Circulating Supply Calcs
    #

    # NU Tokens Calc
    circulating_t_from_nu = 1380688920 * NU_TOKEN_FACTOR * WEI_FACTOR # Nu is fully circulating at 1.38B

    # KEEP Tokens Calc
    keep_token_contract = w3.eth.contract(address=KEEP_TOKEN_ADDRESS, abi=abi)
    keep_total_supply = keep_token_contract.functions.totalSupply().call()

    keep_token_grant = keep_token_contract.functions.balanceOf(
        KEEP_TOKEN_GRANT_ADDRESS).call()
    keep_circulating_supply = keep_total_supply - keep_token_grant - MAGIC_KEEP_SUPPLY_SUBTRACTOR
    circulating_t_from_keep = keep_circulating_supply * KEEP_TOKEN_FACTOR

    # Staking Rewards
    total_staking_rewards = get_total_staking_rewards()
    total_minted_supply = t_total_supply - INITIAL_T_SUPPLY  # claimable staking rewards + future rewards
    future_rewards = (total_minted_supply - total_staking_rewards)

    # Treasury spend = Initial Treasury Supply - Current Treasury Supply
    t_treasury_spend = INITIAL_TREASURY_SUPPLY - t_treasury_supply

    # T circulating supply
    #     = All unlocked NU * 3.259 + All unlocked KEEP * 4.783 + staking rewards + treasury spend
    circulating_t = circulating_t_from_nu + circulating_t_from_keep + total_staking_rewards + t_treasury_spend
    circulating_t_tokens = circulating_t / WEI_FACTOR

    results = {
        "current_total_supply": t_total_supply / WEI_FACTOR,
        "dao_treasury_supply": t_treasury_supply / WEI_FACTOR,
        "future_rewards_supply": future_rewards / WEI_FACTOR,
        "est_circulating_supply": circulating_t_tokens
    }

    if request.path == "/circulating":
        return str(circulating_t_tokens)
    elif request.path == "/":
        return json.dumps(results)
    else:
        raise Exception(f"Unknown route '{request.path}'")
