import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, UTC

DB_PATH = "database/tx_tracker.db"
SCHEMA_PATH = "database/schema.sql"


def initialize_database():
    conn = sqlite3.connect(DB_PATH)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    conn.executescript(schema)

    conn.commit()
    conn.close()

    print("Database initialized successfully.")


# =====================================================
# CONNECTION HANDLER
# =====================================================

@contextmanager
def get_connection():
    conn = sqlite3.connect(
    DB_PATH,
    check_same_thread=False
)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =====================================================
# TRANSACTIONS
# =====================================================

def create_transaction(
    tx_hash,
    from_address,
    to_address,
    nonce,
    value_wei,
    gas_limit,
    gas_price_wei,
    input_data,
    first_seen=None,
    status="PENDING"
):
    """
    Create a new transaction record.
    """

    if first_seen is None:
        first_seen = datetime.now(UTC).isoformat()

    with get_connection() as conn:

        conn.execute("""
        INSERT OR IGNORE INTO transactions (

            tx_hash,
            from_address,
            to_address,
            nonce,
            value_wei,
            gas_limit,
            gas_price_wei,
            input_data,
            first_seen,
            current_status

        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            tx_hash,
            from_address,
            to_address,
            nonce,
            value_wei,
            gas_limit,
            gas_price_wei,
            input_data,
            first_seen,
            status

        ))


# =====================================================
# EVENTS
# =====================================================

def add_event(
    tx_hash,
    event_type,
    details=""
):
    """
    Add lifecycle event.
    """

    event_time = datetime.now(UTC).isoformat()

    with get_connection() as conn:

        conn.execute("""
        INSERT INTO transaction_events (

            tx_hash,
            event_time,
            event_type,
            details

        )
        VALUES (?, ?, ?, ?)
        """, (

            tx_hash,
            event_time,
            event_type,
            details

        ))


# =====================================================
# BLOCKS
# =====================================================

def save_block(
    block_number,
    block_hash,
    parent_hash,
    timestamp,
    is_canonical=1
):
    """
    Store observed block.
    """

    observed_time = datetime.now(UTC).isoformat()

    with get_connection() as conn:

        conn.execute("""
        INSERT OR REPLACE INTO blocks (

            block_hash,
            block_number,
            parent_hash,
            timestamp,
            observed_time,
            is_canonical

        )
        VALUES (?, ?, ?, ?, ?, ?)
        """, (

            block_hash,
            block_number,
            parent_hash,
            timestamp,
            observed_time,
            is_canonical

        ))


# =====================================================
# RECEIPTS
# =====================================================

def save_receipt(
    tx_hash,
    block_number,
    block_hash,
    transaction_index,
    gas_used,
    effective_gas_price,
    status,
    contract_address=None
):
    """
    Store transaction receipt.
    """

    with get_connection() as conn:

        conn.execute("""
        INSERT OR REPLACE INTO transaction_receipts (

            tx_hash,
            block_number,
            block_hash,
            transaction_index,
            gas_used,
            effective_gas_price,
            status,
            contract_address

        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            tx_hash,
            block_number,
            block_hash,
            transaction_index,
            gas_used,
            effective_gas_price,
            status,
            contract_address

        ))


# =====================================================
# STATUS UPDATES
# =====================================================

def update_status(
    tx_hash,
    new_status,
    block_number=None,
    block_hash=None
):
    """
    Update transaction current state.
    Also records state history.
    """

    timestamp = datetime.now(UTC).isoformat()

    with get_connection() as conn:

        conn.execute("""
        UPDATE transactions
        SET
            current_status=?,
            current_block_number=COALESCE(?, current_block_number),
            current_block_hash=COALESCE(?, current_block_hash)
        WHERE tx_hash=?
        """, (

            new_status,
            block_number,
            block_hash,
            tx_hash

        ))

        conn.execute("""
        INSERT INTO transaction_state_history (

            tx_hash,
            state,
            block_number,
            block_hash,
            recorded_at

        )
        VALUES (?, ?, ?, ?, ?)
        """, (

            tx_hash,
            new_status,
            block_number,
            block_hash,
            timestamp

        ))


# =====================================================
# LOOKUPS
# =====================================================

def get_transaction(tx_hash):

    with get_connection() as conn:

        result = conn.execute("""
        SELECT *
        FROM transactions
        WHERE tx_hash=?
        """, (tx_hash,))

        row = result.fetchone()

        return dict(row) if row else None


def get_transaction_events(tx_hash):

    with get_connection() as conn:

        result = conn.execute("""
        SELECT *
        FROM transaction_events
        WHERE tx_hash=?
        ORDER BY event_time
        """, (tx_hash,))

        return [dict(row) for row in result.fetchall()]


def has_event(
    tx_hash,
    event_type
):

    with get_connection() as conn:

        result = conn.execute("""
        SELECT 1
        FROM transaction_events
        WHERE tx_hash=?
        AND event_type=?
        LIMIT 1
        """, (
            tx_hash,
            event_type
        ))

        return result.fetchone() is not None
    

# =====================================================
# CONFIRMATIONS
# =====================================================

def save_confirmation(
    tx_hash,
    block_number,
    confirmation_count
):
    """
    Store confirmation progress.
    """

    timestamp = datetime.now(UTC).isoformat()

    with get_connection() as conn:

        conn.execute("""
        INSERT INTO transaction_confirmations (

            tx_hash,
            block_number,
            confirmation_count,
            recorded_at

        )
        VALUES (?, ?, ?, ?)
        """, (

            tx_hash,
            block_number,
            confirmation_count,
            timestamp

        ))

# =====================================================
# TRACES
# =====================================================

def save_trace(
    tx_hash,
    trace_address,
    call_type,
    from_address,
    to_address,
    value_wei,
    gas,
    trace_index
):
    """
    Store internal trace call.
    """

    with get_connection() as conn:

        conn.execute("""
        INSERT INTO traces (

            tx_hash,
            trace_address,
            call_type,
            from_address,
            to_address,
            value_wei,
            gas,
            trace_index

        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            tx_hash,
            trace_address,
            call_type,
            from_address,
            to_address,
            value_wei,
            gas,
            trace_index

        ))

# =====================================================
# REORGS
# =====================================================

def save_reorg(
    block_number,
    old_block_hash,
    new_block_hash
):
    """
    Store reorg event.
    """

    timestamp = datetime.now(UTC).isoformat()

    with get_connection() as conn:

        conn.execute("""
        INSERT INTO reorgs (

            detected_time,
            block_number,
            old_block_hash,
            new_block_hash

        )
        VALUES (?, ?, ?, ?)
        """, (

            timestamp,
            block_number,
            old_block_hash,
            new_block_hash

        ))

# =====================================================
# REPLACEMENTS
# =====================================================

def save_replacement(
    original_tx,
    replacement_tx,
    sender,
    nonce
):
    """
    Store replacement transaction.
    """

    timestamp = datetime.now(UTC).isoformat()

    with get_connection() as conn:

        conn.execute("""
        INSERT INTO replacements (

            original_tx,
            replacement_tx,
            sender,
            nonce,
            detected_time

        )
        VALUES (?, ?, ?, ?, ?)
        """, (

            original_tx,
            replacement_tx,
            sender,
            nonce,
            timestamp

        ))

def get_pending_transactions():

    with get_connection() as conn:

        result = conn.execute("""
        SELECT *
        FROM transactions
        WHERE current_status='PENDING'
        """)

        return [dict(row) for row in result.fetchall()]
    
def get_latest_block():

    with get_connection() as conn:

        result = conn.execute("""
        SELECT *
        FROM blocks
        ORDER BY block_number DESC
        LIMIT 1
        """)

        row = result.fetchone()

        return dict(row) if row else None

def transaction_exists(tx_hash):

    with get_connection() as conn:

        result = conn.execute("""
        SELECT 1
        FROM transactions
        WHERE tx_hash=?
        LIMIT 1
        """, (tx_hash,))

        return result.fetchone() is not None
    
def mark_transaction_mined(
    tx_hash,
    block_number,
    block_hash
):
    update_status(
        tx_hash,
        "MINED",
        block_number,
        block_hash
    )

    add_event(
        tx_hash,
        "MINED",
        f"Included in block {block_number}"
    )

def mark_transaction_result(
    tx_hash,
    status
):

    if status == 1:

        update_status(
            tx_hash,
            "SUCCESS"
        )

        add_event(
            tx_hash,
            "SUCCESS",
            "Transaction executed successfully"
        )

    else:

        update_status(
            tx_hash,
            "FAILED"
        )

        add_event(
            tx_hash,
            "FAILED",
            "Transaction execution reverted"
        )

def get_active_transactions():

    with get_connection() as conn:

        result = conn.execute("""
        SELECT *
        FROM transactions
        WHERE current_status IN (
            'MINED',
            'SUCCESS',
            'FAILED'
        )
        """)

        return [
            dict(row)
            for row in result.fetchall()
        ]

def get_latest_confirmation(
    tx_hash
):

    with get_connection() as conn:

        result = conn.execute("""
        SELECT confirmation_count
        FROM transaction_confirmations
        WHERE tx_hash=?
        ORDER BY confirmation_count DESC
        LIMIT 1
        """, (tx_hash,))

        row = result.fetchone()

        return (
            row["confirmation_count"]
            if row
            else -1
        )

def mark_finalized(
    tx_hash
):

    update_status(
        tx_hash,
        "FINALIZED"
    )

    add_event(
        tx_hash,
        "FINALIZED",
        "Transaction finalized"
    )


def mark_safe(
    tx_hash
):

    add_event(
        tx_hash,
        "SAFE",
        "Transaction reached safe block"
    )

'''
save_confirmation(
    tx_hash="0xabc",
    block_number=23000000,
    confirmation_count=12
)

save_reorg(
    100,
    "AAA",
    "BBB"
)

save_replacement(
    original_tx="TX_A",
    replacement_tx="TX_B",
    sender="0x123",
    nonce=50
)
'''
