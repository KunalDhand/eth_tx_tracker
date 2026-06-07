import asyncio

from tracker.rpc import (
    rpc,
    get_safe_block,
    get_finalized_block
)

from database.db import (
    get_active_transactions,
    save_confirmation,
    get_latest_confirmation,
    add_event,
    has_event,
    mark_finalized,
    mark_safe
)


class ConfirmationMonitor:

    async def start(self):

        print(
            "[+] Confirmation monitor started"
        )

        while True:

            try:

                await self.process()

            except Exception as e:

                print(
                    "[CONFIRMATION ERROR]",
                    e
                )

            await asyncio.sleep(12)

    async def process(self):

        latest_block = int(
            rpc(
                "eth_blockNumber",
                []
            ),
            16
        )

        safe_block = get_safe_block()
        finalized_block = get_finalized_block()

        safe_number = (
            int(safe_block["number"], 16)
            if safe_block
            else 0
        )

        finalized_number = (
            int(finalized_block["number"], 16)
            if finalized_block
            else 0
        )

        txs = get_active_transactions()

        for tx in txs:

            if (
                tx["current_block_number"]
                is None
            ):
                continue

            confirmations = (
                latest_block
                - tx["current_block_number"]
            )

            if (
                tx["current_block_number"]
                <= safe_number
                and not has_event(
                    tx["tx_hash"],
                    "SAFE"
                )
            ):
                mark_safe(tx["tx_hash"])

            if (
                tx["current_block_number"]
                <= finalized_number
                and not has_event(
                    tx["tx_hash"],
                    "FINALIZED"
                )
            ):
                mark_finalized(tx["tx_hash"])

            previous = (
                get_latest_confirmation(
                    tx["tx_hash"]
                )
            )

            if confirmations <= previous:
                continue

            save_confirmation(
                tx["tx_hash"],
                tx["current_block_number"],
                confirmations
            )

            self.record_milestone(
                tx["tx_hash"],
                confirmations
            )

            print(
                f"[CONFIRMATIONS] "
                f"{tx['tx_hash'][:10]} "
                f"{confirmations}"
            )

    def record_milestone(
        self,
        tx_hash,
        confirmations
    ):

        milestones = [
            1,
            2,
            3,
            5,
            10,
            12,
            25,
            50,
            64
        ]

        if confirmations in milestones:

            add_event(
                tx_hash,
                "CONFIRMED",
                f"{confirmations} confirmations"
            )
