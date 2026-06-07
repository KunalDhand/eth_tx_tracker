#from database.db import initialize_database

#if __name__ == "__main__":
#    initialize_database()

import asyncio

from tracker.pending_listener import (
    PendingTransactionListener
)

from tracker.receipt_monitor import (
    ReceiptMonitor
)

from tracker.confirmation_monitor import (
    ConfirmationMonitor
)


async def main():

    listener = (
        PendingTransactionListener()
    )

    monitor = (
        ReceiptMonitor()
    )

    confirmation_monitor = (
        ConfirmationMonitor()
    )

    await asyncio.gather(

        listener.subscribe(),

        monitor.start(),

        confirmation_monitor.start()

    )


if __name__ == "__main__":

    asyncio.run(main())
