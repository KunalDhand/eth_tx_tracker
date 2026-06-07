import requests

from config import ALCHEMY_RPC_URL


def rpc(method, params=None):

    if params is None:
        params = []

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }

    response = requests.post(
        ALCHEMY_RPC_URL,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if "error" in result:
        raise Exception(result["error"])

    return result["result"]


def get_safe_block():

    return rpc(
        "eth_getBlockByNumber",
        ["safe", False]
    )


def get_finalized_block():

    return rpc(
        "eth_getBlockByNumber",
        ["finalized", False]
    )