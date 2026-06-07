# test_db.py
'''
from database.db import *

TEST_TX = "0x123abc"

create_transaction(
    tx_hash=TEST_TX,
    from_address="0xAAA",
    to_address="0xBBB",
    nonce=1,
    value_wei="1000000000000000000",
    gas_limit=21000,
    gas_price_wei="20000000000",
    input_data="0x"
)

add_event(
    TEST_TX,
    "PENDING_SEEN",
    "Transaction first observed"
)

update_status(
    TEST_TX,
    "PENDING"
)

print(get_transaction(TEST_TX))
print(get_transaction_events(TEST_TX))
'''

from database.db import get_pending_transactions

txs = get_pending_transactions()

print(
    f"Pending TXs: {len(txs)}"
)

for tx in txs[:5]:
    print(tx["tx_hash"])