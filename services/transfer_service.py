from database import get_db
from services.inventory_service import assert_available_stock, record_stock_movement


def approve_transfer(transfer_id: int) -> None:
    db = get_db()

    transfer = db.execute(
        "SELECT * FROM stock_transfers WHERE id = ?",
        (transfer_id,),
    ).fetchone()

    if not transfer:
        raise ValueError("Transfer not found.")

    if transfer["status"] != "draft":
        raise ValueError("Only draft transfers can be approved.")

    db.execute(
        """
        UPDATE stock_transfers
        SET status = 'approved'
        WHERE id = ?
        """,
        (transfer_id,),
    )

    db.commit()


def dispatch_transfer(transfer_id: int) -> None:
    db = get_db()

    try:
        db.execute("BEGIN")

        transfer = db.execute(
            "SELECT * FROM stock_transfers WHERE id = ?",
            (transfer_id,),
        ).fetchone()

        if not transfer:
            raise ValueError("Transfer not found.")

        if transfer["status"] != "approved":
            raise ValueError("Only approved transfers can be dispatched.")

        items = db.execute(
            """
            SELECT *
            FROM stock_transfer_items
            WHERE stock_transfer_id = ?
            """,
            (transfer_id,),
        ).fetchall()

        if not items:
            raise ValueError("Transfer has no items.")

        for item in items:
            assert_available_stock(
                product_id=item["product_id"],
                location_id=transfer["from_location_id"],
                required_qty=item["quantity_transferred"],
            )

        for item in items:
            record_stock_movement(
                product_id=item["product_id"],
                location_id=transfer["from_location_id"],
                movement_type="transfer_out",
                quantity=item["quantity_transferred"],
                unit_cost=item["unit_cost"],
                reference_type="stock_transfer",
                reference_id=transfer_id,
                reason="Transfer dispatched",
            )

        db.execute(
            """
            UPDATE stock_transfers
            SET status = 'in_transit'
            WHERE id = ?
            """,
            (transfer_id,),
        )

        db.commit()

    except Exception:
        db.rollback()
        raise


def receive_transfer(transfer_id: int, received_items: dict[int, int]) -> None:
    db = get_db()

    try:
        db.execute("BEGIN")

        transfer = db.execute(
            "SELECT * FROM stock_transfers WHERE id = ?",
            (transfer_id,),
        ).fetchone()

        if not transfer:
            raise ValueError("Transfer not found.")

        if transfer["status"] not in ("in_transit", "partially_received"):
            raise ValueError("Only in-transit transfers can be received.")

        items = db.execute(
            """
            SELECT *
            FROM stock_transfer_items
            WHERE stock_transfer_id = ?
            """,
            (transfer_id,),
        ).fetchall()

        total_received_now = 0

        for item in items:
            item_id = item["id"]
            received_qty = int(received_items.get(item_id, 0))

            if received_qty < 0:
                raise ValueError("Received quantity cannot be negative.")

            remaining_qty = item["quantity_transferred"] - item["quantity_received"]

            if received_qty > remaining_qty:
                raise ValueError(
                    f"Cannot receive more than remaining transfer quantity for item ID {item_id}."
                )

            total_received_now += received_qty

        if total_received_now <= 0:
            raise ValueError("No received quantity entered.")

        for item in items:
            item_id = item["id"]
            received_qty = int(received_items.get(item_id, 0))

            if received_qty <= 0:
                continue

            db.execute(
                """
                UPDATE stock_transfer_items
                SET quantity_received = quantity_received + ?
                WHERE id = ?
                """,
                (received_qty, item_id),
            )

            record_stock_movement(
                product_id=item["product_id"],
                location_id=transfer["to_location_id"],
                movement_type="transfer_in",
                quantity=received_qty,
                unit_cost=item["unit_cost"],
                reference_type="stock_transfer",
                reference_id=transfer_id,
                reason="Transfer received",
            )

        remaining_after_receive = db.execute(
            """
            SELECT COALESCE(SUM(quantity_transferred - quantity_received), 0) AS remaining
            FROM stock_transfer_items
            WHERE stock_transfer_id = ?
            """,
            (transfer_id,),
        ).fetchone()["remaining"]

        new_status = "received" if int(remaining_after_receive) == 0 else "partially_received"

        db.execute(
            """
            UPDATE stock_transfers
            SET status = ?
            WHERE id = ?
            """,
            (new_status, transfer_id),
        )

        if transfer["item_request_id"]:
            sync_item_request_fulfillment(transfer["item_request_id"])

        db.commit()

    except Exception:
        db.rollback()
        raise


def sync_item_request_fulfillment(item_request_id: int) -> None:
    db = get_db()

    request_items = db.execute(
        """
        SELECT id, product_id
        FROM item_request_items
        WHERE item_request_id = ?
        """,
        (item_request_id,),
    ).fetchall()

    for request_item in request_items:
        fulfilled_qty = db.execute(
            """
            SELECT COALESCE(SUM(sti.quantity_received), 0) AS fulfilled_qty
            FROM stock_transfers st
            JOIN stock_transfer_items sti
                ON sti.stock_transfer_id = st.id
            WHERE st.item_request_id = ?
              AND sti.product_id = ?
              AND st.status IN ('partially_received', 'received')
            """,
            (item_request_id, request_item["product_id"]),
        ).fetchone()["fulfilled_qty"]

        db.execute(
            """
            UPDATE item_request_items
            SET quantity_fulfilled = ?
            WHERE id = ?
            """,
            (fulfilled_qty, request_item["id"]),
        )

    remaining = db.execute(
        """
        SELECT COALESCE(SUM(quantity_approved - quantity_fulfilled), 0) AS remaining
        FROM item_request_items
        WHERE item_request_id = ?
        """,
        (item_request_id,),
    ).fetchone()["remaining"]

    status = "fulfilled" if int(remaining) == 0 else "partially_fulfilled"

    db.execute(
        """
        UPDATE item_requests
        SET status = ?
        WHERE id = ?
        """,
        (status, item_request_id),
    )
