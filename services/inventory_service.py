from database import get_db


POSITIVE_MOVEMENTS = {
    "purchase_receive",
    "transfer_in",
    "adjustment_in",
    "return_in",
}

NEGATIVE_MOVEMENTS = {
    "transfer_out",
    "adjustment_out",
    "return_out",
    "sale_out",
    "damage_out",
}


def get_stock(product_id: int, location_id: int) -> int:
    db = get_db()

    row = db.execute(
        """
        SELECT COALESCE(SUM(quantity), 0) AS current_stock
        FROM stock_movements
        WHERE product_id = ?
          AND location_id = ?
        """,
        (product_id, location_id),
    ).fetchone()

    return int(row["current_stock"])


def assert_available_stock(product_id: int, location_id: int, required_qty: int) -> None:
    current_stock = get_stock(product_id, location_id)

    if current_stock < required_qty:
        raise ValueError(
            f"Insufficient stock. Available: {current_stock}, required: {required_qty}"
        )


def normalize_quantity(movement_type: str, quantity: int) -> int:
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    if movement_type in POSITIVE_MOVEMENTS:
        return quantity

    if movement_type in NEGATIVE_MOVEMENTS:
        return -quantity

    raise ValueError(f"Invalid movement type: {movement_type}")


def record_stock_movement(
    product_id: int,
    location_id: int,
    movement_type: str,
    quantity: int,
    unit_cost: float,
    reference_type: str,
    reference_id: int,
    reason: str = "",
) -> None:
    db = get_db()

    signed_quantity = normalize_quantity(movement_type, quantity)

    if signed_quantity < 0:
        assert_available_stock(product_id, location_id, abs(signed_quantity))

    db.execute(
        """
        INSERT INTO stock_movements (
            product_id,
            location_id,
            movement_type,
            quantity,
            unit_cost,
            reference_type,
            reference_id,
            reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id,
            location_id,
            movement_type,
            signed_quantity,
            unit_cost,
            reference_type,
            reference_id,
            reason,
        ),
    )
