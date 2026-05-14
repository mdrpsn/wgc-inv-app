from database import get_db


OPEN_PO_STATUSES = ("draft", "approved", "partially_received")
PENDING_REQUEST_STATUSES = ("draft", "submitted", "approved", "partially_fulfilled")
ACTIVE_TRANSFER_STATUSES = ("draft", "approved", "in_transit", "partially_received")


def get_product_deactivation_blocks(product_id: int) -> list[str]:
    db = get_db()
    blocks = []

    stock = db.execute(
        """
        SELECT COALESCE(SUM(quantity), 0) AS qty
        FROM stock_movements
        WHERE product_id = ?
        """,
        (product_id,),
    ).fetchone()["qty"]

    if stock and stock > 0:
        blocks.append(f"Product still has active stock quantity: {stock}.")

    open_po_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM purchase_order_items poi
        JOIN purchase_orders po ON po.id = poi.purchase_order_id
        WHERE poi.product_id = ?
          AND po.status IN ('draft', 'approved', 'partially_received')
        """,
        (product_id,),
    ).fetchone()["count"]

    if open_po_count > 0:
        blocks.append(f"Product is used in {open_po_count} open purchase order item(s).")

    pending_request_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM item_request_items iri
        JOIN item_requests ir ON ir.id = iri.item_request_id
        WHERE iri.product_id = ?
          AND ir.status IN ('draft', 'submitted', 'approved', 'partially_fulfilled')
        """,
        (product_id,),
    ).fetchone()["count"]

    if pending_request_count > 0:
        blocks.append(f"Product is used in {pending_request_count} pending item request(s).")

    active_transfer_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM stock_transfer_items sti
        JOIN stock_transfers st ON st.id = sti.stock_transfer_id
        WHERE sti.product_id = ?
          AND st.status IN ('draft', 'approved', 'in_transit', 'partially_received')
        """,
        (product_id,),
    ).fetchone()["count"]

    if active_transfer_count > 0:
        blocks.append(f"Product is used in {active_transfer_count} active stock transfer(s).")

    return blocks


def get_supplier_deactivation_blocks(supplier_id: int) -> list[str]:
    db = get_db()
    blocks = []

    open_po_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM purchase_orders
        WHERE supplier_id = ?
          AND status IN ('draft', 'approved', 'partially_received')
        """,
        (supplier_id,),
    ).fetchone()["count"]

    if open_po_count > 0:
        blocks.append(f"Supplier has {open_po_count} open purchase order(s).")

    return blocks


def get_location_deactivation_blocks(location_id: int) -> list[str]:
    db = get_db()
    blocks = []

    stock_rows = db.execute(
        """
        SELECT
            p.sku,
            p.name,
            COALESCE(SUM(sm.quantity), 0) AS qty
        FROM stock_movements sm
        JOIN products p ON p.id = sm.product_id
        WHERE sm.location_id = ?
        GROUP BY sm.product_id
        HAVING qty > 0
        ORDER BY p.name
        """,
        (location_id,),
    ).fetchall()

    if stock_rows:
        blocks.append(f"Location still has positive stock for {len(stock_rows)} product(s).")

    pending_request_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM item_requests
        WHERE (from_location_id = ? OR to_location_id = ?)
          AND status IN ('draft', 'submitted', 'approved', 'partially_fulfilled')
        """,
        (location_id, location_id),
    ).fetchone()["count"]

    if pending_request_count > 0:
        blocks.append(f"Location is used in {pending_request_count} pending item request(s).")

    active_transfer_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM stock_transfers
        WHERE (from_location_id = ? OR to_location_id = ?)
          AND status IN ('draft', 'approved', 'in_transit', 'partially_received')
        """,
        (location_id, location_id),
    ).fetchone()["count"]

    if active_transfer_count > 0:
        blocks.append(f"Location is used in {active_transfer_count} active stock transfer(s).")

    return blocks


def deactivate_product(product_id: int) -> None:
    db = get_db()
    blocks = get_product_deactivation_blocks(product_id)

    if blocks:
        raise ValueError("Cannot deactivate product: " + " ".join(blocks))

    db.execute(
        """
        UPDATE products
        SET is_active = 0
        WHERE id = ?
        """,
        (product_id,),
    )
    db.commit()


def reactivate_product(product_id: int) -> None:
    db = get_db()
    db.execute("UPDATE products SET is_active = 1 WHERE id = ?", (product_id,))
    db.commit()


def deactivate_supplier(supplier_id: int) -> None:
    db = get_db()
    blocks = get_supplier_deactivation_blocks(supplier_id)

    if blocks:
        raise ValueError("Cannot deactivate supplier: " + " ".join(blocks))

    db.execute(
        """
        UPDATE suppliers
        SET is_active = 0
        WHERE id = ?
        """,
        (supplier_id,),
    )
    db.commit()


def reactivate_supplier(supplier_id: int) -> None:
    db = get_db()
    db.execute("UPDATE suppliers SET is_active = 1 WHERE id = ?", (supplier_id,))
    db.commit()


def deactivate_location(location_id: int) -> None:
    db = get_db()
    blocks = get_location_deactivation_blocks(location_id)

    if blocks:
        raise ValueError("Cannot deactivate location: " + " ".join(blocks))

    db.execute(
        """
        UPDATE locations
        SET is_active = 0
        WHERE id = ?
        """,
        (location_id,),
    )
    db.commit()


def reactivate_location(location_id: int) -> None:
    db = get_db()
    db.execute("UPDATE locations SET is_active = 1 WHERE id = ?", (location_id,))
    db.commit()
