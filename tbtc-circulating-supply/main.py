from web3.auto import w3

def main(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """

    with open("tbtc-token.abi") as tbtc_token_file:
        abi = tbtc_token_file.read()

    address = '0x18084fbA666a33d37592fA2633fD49a74DD93a88'
    contract = w3.eth.contract(address=address, abi=abi)
    total_supply = contract.functions.totalSupply().call()

    return str(total_supply / (10 ** 18))
