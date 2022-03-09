from web3.auto import w3
import json
import requests

def main(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """


    address = '0xCdF7028ceAB81fA0C6971208e83fa7872994beE5'
    with open('t-contract.abi') as t_contract_file:
        abi = t_contract_file.read()
        t_token_contract = w3.eth.contract(address=address, abi=abi)

        address = '0x85Eee30c52B0b379b046Fb0F85F4f3Dc3009aFEC'
        with open('keep-token.abi') as keep_contract_file:
            abi = keep_contract_file.read()
            keep_token_contract = w3.eth.contract(address=address, abi=abi)

            address = '0x4fE83213D56308330EC302a8BD641f1d0113A4Cc'
            with open('nu-contract.abi') as nu_contract_file:
                nu_token_contract = w3.eth.contract(address=address, abi=abi)

                t_total_supply = t_token_contract.functions.totalSupply().call()
                t_treasury_supply = t_token_contract.functions.balanceOf('0x9F6e831c8F8939DC0C830C6e492e7cEf4f9C2F5f').call()
                nu_vending_machine = t_token_contract.functions.balanceOf('0x1CCA7E410eE41739792eA0A24e00349Dd247680e').call()

                nu_token_factor = 3.25924249316
                nu_circulating_supply = requests.get("https://status.nucypher.network/supply_information?q=est_circulating_supply", verify=False).json()
                nu_in_nu_vending = nu_token_contract.functions.balanceOf('0x1CCA7E410eE41739792eA0A24e00349Dd247680e').call() / (10 ** 18)
                nu_circulating_but_not_upgraded = nu_circulating_supply - nu_in_nu_vending
                circulating_t_from_nu = nu_circulating_but_not_upgraded * nu_token_factor * (10 ** 18)

                keep_vending_machine = t_token_contract.functions.balanceOf('0xE47c80e8c23f6B4A1aE41c34837a0599D5D16bb0').call()

                keep_total_supply = keep_token_contract.functions.totalSupply().call()
                keep_token_grant = keep_token_contract.functions.balanceOf('0x175989c71Fd023D580C65F5dC214002687ff88B7').call()
                keep_to_t_vending_machine = keep_token_contract.functions.balanceOf('0xE47c80e8c23f6B4A1aE41c34837a0599D5D16bb0').call()
                magic_subtractor = 59053770 * (10 ** 18)
                keep_circulating_but_not_upgraded = keep_total_supply - keep_token_grant - keep_to_t_vending_machine - magic_subtractor
                keep_supply_in_tokens = keep_circulating_but_not_upgraded / (10 ** 18)
                keep_token_factor = 4.78318863126
                circulating_t_from_keep = keep_supply_in_tokens * keep_token_factor * (10 ** 18)

                circulating_t = t_total_supply - t_treasury_supply - nu_vending_machine + circulating_t_from_nu - keep_vending_machine + circulating_t_from_keep
                circulating_t_tokens = circulating_t / (10 ** 18)
                results = {
                        'current_total_supply': t_total_supply / (10 ** 18),
                        'dao_treasury_supply': t_treasury_supply / (10 ** 18),
                        'est_circulating_supply': circulating_t_tokens
                }
                return json.dumps(results)
