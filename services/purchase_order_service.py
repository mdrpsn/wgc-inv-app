from database import get_db
from services.inventory_service import record_stock_movement


def approve_purchase_order(po_id: int) -> None:
    db = get_db()

    po = db.execute(
        "SELECT * FROM purchase_orders WHERE id = ?",
        (po_id,),
    ).fetchone()

    if not po:
        raise ValueError("Purchase order not found.")

    if po["status"] != "draft":
        raise ValueError("Only draft purchase orders can be approved.")

    items = db.execute(
        """
        SELECT *
        FROM purchase_order_items
        WHERE purchase_order_id = ?
        """,
        (po_id,),
    ).fetchall()

    if not items:
        raise ValueError("Purchase order has no items.")

    db.execute(
        """
        UPDATE purchase_orders
        SET status = 'approved'
        WHERE id = ?
        """,
        (po_id,),
    )

    db.commit()


def receive_purchase_order(po_id: int, warehouse_location_id: int, received_items: dict[int, int]) -> None:
    db = get_db()

    try:
        db.execute("BEGIN")

        po = db.execute(
            """
            SELECT *
            FROM purchase_orders
            WHERE id = ?
            """,
            (po_id,),
        ).fetchone()

        if not po:
            raise ValueError("Purchase order not found.")

        if po["status"] not in ("approved", "partially_received"):
            raise ValueError("Only approved or partially received purchase orders can be received.")

        location = db.execute(
            """
            SELECT *
            FROM locations
            WHERE id = ?
              AND location_type = 'warehouse'
              AND is_active = 1
            """,
            (warehouse_location_id,),
        ).fetchone()

        if not location:
            raise ValueError("Receiving location must be an active warehouse.")

        items = db.execute(
            """
            SELECT *
            FROM purchase_order_items
            WHERE purchase_order_id = ?
            """,
            (po_id,),
        ).fetchall()

        if not items:
            raise ValueError("Purchase order has no items.")

        total_received_now = 0

        for item in items:
            item_id = item["id"]
            received_qty = int(received_items.get(item_id, 0))

            if received_qty < 0:
                raise ValueError("Received quantity cannot be negative.")

            remaining_qty = item["quantity_ordered"] - item["quantity_received"]

            if received_qty > remaining_qty:
                raise ValueError(
                    f"Cannot receive more than remaining PO quantity for item ID {item_id}."
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
                UPDATE purchase_order_items
                SET quantity_received = quantity_received + ?
                WHERE id = ?
                """,
                (received_qty, item_id),
            )

            record_stock_movement(
                product_id=item["product_id"],
                location_id=warehouse_location_id,
                movement_type="purchase_receive",
                quantity=received_qty,
                unit_cost=item["unit_cost"],
                reference_type="purchase_order",
                reference_id=po_id,
                reason=f"Purchase order received: {po['po_number']}",
            )

        remaining_after_receive = db.execute(
            """
            SELECT COALESCE(SUM(quantity_ordered - quantity_received), 0) AS remaining
            FROM purchase_order_items
            WHERE purchase_order_id = ?
            """,
            (po_id,),
        ).fetchone()["remaining"]

        new_status = "received" if int(remaining_after_receive) == 0 else "partially_received"

        db.execute(
            """
            UPDATE purchase_orders
            SET status = ?
            WHERE id = ?
            """,
            (new_status, po_id),
        )

        db.commit()

    except Exception:
        db.rollback()
        raise
