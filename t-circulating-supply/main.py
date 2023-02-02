import json

import requests
from web3.auto import w3

# Token factors
NU_TOKEN_FACTOR = 3.25924249316
KEEP_TOKEN_FACTOR = 4.78318863126

# Addresses
T_TOKEN_ADDRESS = "0xCdF7028ceAB81fA0C6971208e83fa7872994beE5"
T_TREASURY_ADDRESS = "0x9F6e831c8F8939DC0C830C6e492e7cEf4f9C2F5f"
KEEP_TOKEN_ADDRESS = "0x85Eee30c52B0b379b046Fb0F85F4f3Dc3009aFEC"
KEEP_TOKEN_GRANT_ADDRESS = "0x175989c71Fd023D580C65F5dC214002687ff88B7"
NU_TOKEN_ADDRESS = "0x4fE83213D56308330EC302a8BD641f1d0113A4Cc"
MERKLE_DISTRIBUTION_ADDRESS = "0xeA7CA290c7811d1cC2e79f8d706bD05d8280BD37"

# Token supply constants
MAGIC_KEEP_SUPPLY_SUBTRACTOR = 59053770 * (10 ** 18)
INITIAL_T_SUPPLY = 10_000_000_000 * (10 ** 18)  # 10B T
INITIAL_TREASURY_SUPPLY = 1_000_000_000 * (10 ** 18)  # 1B T

# Merkle Distribution
MERKLE_DISTRIBUTION_SUMMARY_FILENAME = "distributions.json"
MERKLE_DISTRIBUTION_CONTRACT_DEPLOYMENT_BLOCK = 15146501  # block that contract was deployed


def make_request(request_url: str, verify: bool = True):
    """
    Issues a HTTP GET for the provided request url. If successful, the response data
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
    distribution_file = make_request(
        f"https://raw.githubusercontent.com/threshold-network/merkle-distribution/main/distributions/{MERKLE_DISTRIBUTION_SUMMARY_FILENAME}"
    )
    total_staking_rewards = int(distribution_file["LatestCumulativeAmount"])
    return total_staking_rewards


def get_already_claimed_rewards():
    """
    Determined the amount of rewards already claimed from the MerkleDistribution contract.
    """
    # TODO would be great to cache the return of this function - doesn't need to be done every time.
    total_claimed = 0
    with open("merkle-distribution.abi") as merkle_distribution_contract_file:
        abi = merkle_distribution_contract_file.read()
        merkle_distribution_contract = w3.eth.contract(address=MERKLE_DISTRIBUTION_ADDRESS, abi=abi)
        events = merkle_distribution_contract.events["Claimed"].getLogs(fromBlock=MERKLE_DISTRIBUTION_CONTRACT_DEPLOYMENT_BLOCK)
        for event in events:
            total_claimed += event["args"]["amount"]

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
    with open("erc20.abi") as erc20_abi_file:
        abi = erc20_abi_file.read()

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
    total_minted_supply = t_total_supply - INITIAL_T_SUPPLY  # staking rewards + overmint
    overminted_tokens = (total_minted_supply - total_staking_rewards)

    # Treasury Supply i.e. unused T (excluding overminted tokens) = CurrentWalletBalance - unclaimed rewards - overminted tokens
    t_treasury_current_balance = t_token_contract.functions.balanceOf(T_TREASURY_ADDRESS).call()
    t_treasury_supply = t_treasury_current_balance - unclaimed_rewards - overminted_tokens

    if request.path == "/treasury":
        return str(t_treasury_supply / (10 ** 18))

    #
    # Circulating Supply Calcs
    #

    # KEEP Tokens Calc
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

    # Treasury spend = Initial Treasury Supply - Current Treasury Supply
    t_treasury_spend = INITIAL_TREASURY_SUPPLY - t_treasury_supply

    # T circulating supply
    #     = All unlocked NU * 3.259 + All unlocked KEEP * 4.783 + staking rewards + treasury spend
    circulating_t = circulating_t_from_nu + circulating_t_from_keep + total_staking_rewards + t_treasury_spend
    circulating_t_tokens = circulating_t / (10 ** 18)

    results = {
        "current_total_supply": t_total_supply / (10 ** 18),
        "dao_treasury_supply": t_treasury_supply / (10 ** 18),
        "future_rewards_supply": overminted_tokens / (10**18),
        "est_circulating_supply": circulating_t_tokens
    }

    if request.path == "/circulating":
        return str(circulating_t_tokens)
    elif request.path == "/":
        return json.dumps(results)
    else:
        raise Exception(f"Unknown route {request.path}")
