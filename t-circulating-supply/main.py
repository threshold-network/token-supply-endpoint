import json

from web3.auto import w3

WEI_FACTOR = 10 ** 18

# Addresses
T_TOKEN_ADDRESS = "0xCdF7028ceAB81fA0C6971208e83fa7872994beE5"
GB_TIMELOCK_CONTROLLER_ADDRESS = "0x87F005317692D05BAA4193AB0c961c69e175f45f"  # T Treasury stored here
FUTURE_REWARDS_ADDRESS = "0xbe3e95Dc12C0aE3FAC264Bf63ef89Ec81139E3DF"


def main(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """

    with open("erc20.abi") as erc20_abi_file:
        abi = erc20_abi_file.read()

    t_token_contract = w3.eth.contract(address=T_TOKEN_ADDRESS, abi=abi)

    # Total Supply
    t_total_supply = t_token_contract.functions.totalSupply().call()
    if request.path == "/total":
        return str(t_total_supply / WEI_FACTOR)

    # Treasury Supply i.e. T in Governor Bravo TimeLock Contract
    t_treasury_supply = t_token_contract.functions.balanceOf(GB_TIMELOCK_CONTROLLER_ADDRESS).call()
    if request.path == "/treasury":
        return str(t_treasury_supply / WEI_FACTOR)

    # Circulating supply is now fully diluted
    circulating_t = t_total_supply
    circulating_t_tokens = circulating_t / WEI_FACTOR
    if request.path == "/circulating":
        return str(circulating_t_tokens)

    # Future Rewards
    future_rewards = t_token_contract.functions.balanceOf(FUTURE_REWARDS_ADDRESS).call()

    results = {
        "current_total_supply": t_total_supply / WEI_FACTOR,
        "dao_treasury_supply": t_treasury_supply / WEI_FACTOR,
        "future_rewards_supply": future_rewards / WEI_FACTOR,
        "est_circulating_supply": circulating_t_tokens
    }

    if request.path == "/":
        return json.dumps(results)
    else:
        raise Exception(f"Unknown route '{request.path}'")
