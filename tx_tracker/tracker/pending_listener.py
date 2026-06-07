import asyncio
import json
import websockets

from config import ALCHEMY_WS_URL
from websockets.exceptions import WebSocketException

from tracker.rpc import rpc

from database.db import (
    create_transaction,
    add_event,
    transaction_exists
)


class PendingTransactionListener:

    async def subscribe(self):
        reconnect_delay = 5

        while True:
            try:
                await self._listen()
                reconnect_delay = 5

            except asyncio.CancelledError:
                raise

            except (
                TimeoutError,
                OSError,
                WebSocketException
            ) as exc:
                print(
                    f"[WS ERROR] {exc}. "
                    f"Retrying in {reconnect_delay}s..."
                )

            except Exception as exc:
                print(
                    f"[LISTENER ERROR] {exc}. "
                    f"Retrying in {reconnect_delay}s..."
                )

            await asyncio.sleep(
                reconnect_delay
            )
            reconnect_delay = min(
                reconnect_delay * 2,
                60
            )

    async def _listen(self):

        async with websockets.connect(
            ALCHEMY_WS_URL,
            open_timeout=45,
            ping_interval=20,
            ping_timeout=20
        ) as websocket:

            print("[+] Connected to Alchemy")

            subscription = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": [
                    "newPendingTransactions"
                ]
            }

            await websocket.send(
                json.dumps(subscription)
            )

            response = await websocket.recv()

            print("[+] Subscription:", response)

            while True:

                try:

                    message = await websocket.recv()

                    data = json.loads(message)

                    if "params" not in data:
                        continue

                    tx_hash = (
                        data["params"]["result"]
                    )

                    await self.process_transaction(
                        tx_hash
                    )

                except Exception as e:

                    print(
                        "[ERROR]",
                        str(e)
                    )

    async def process_transaction(
        self,
        tx_hash
    ):

        try:

            if transaction_exists(
                tx_hash
            ):
                return

            tx = rpc(
                "eth_getTransactionByHash",
                [tx_hash]
            )

            if not tx:
                return

            create_transaction(

                tx_hash=tx["hash"],

                from_address=tx["from"],

                to_address=tx.get("to"),

                nonce=int(
                    tx["nonce"],
                    16
                ),

                value_wei=tx["value"],

                gas_limit=int(
                    tx["gas"],
                    16
                ),

                gas_price_wei=tx.get(
                    "gasPrice",
                    "0x0"
                ),

                input_data=tx["input"]
            )

            add_event(
                tx["hash"],
                "PENDING_SEEN",
                "First observed in mempool"
            )

            print(
                "[PENDING]",
                tx["hash"]
            )

        except Exception as e:

            print(
                "[PROCESS ERROR]",
                tx_hash,
                str(e)
            )
