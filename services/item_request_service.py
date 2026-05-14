from database import get_db


def submit_item_request(request_id: int) -> None:
    db = get_db()

    request_row = db.execute(
        "SELECT * FROM item_requests WHERE id = ?",
        (request_id,),
    ).fetchone()

    if not request_row:
        raise ValueError("Item request not found.")

    if request_row["status"] != "draft":
        raise ValueError("Only draft requests can be submitted.")

    db.execute(
        """
        UPDATE item_requests
        SET status = 'submitted'
        WHERE id = ?
        """,
        (request_id,),
    )

    db.commit()


def approve_item_request(request_id: int, approved_items: dict[int, int]) -> None:
    db = get_db()

    try:
        db.execute("BEGIN")

        request_row = db.execute(
            "SELECT * FROM item_requests WHERE id = ?",
            (request_id,),
        ).fetchone()

        if not request_row:
            raise ValueError("Item request not found.")

        if request_row["status"] != "submitted":
            raise ValueError("Only submitted requests can be approved.")

        items = db.execute(
            """
            SELECT *
            FROM item_request_items
            WHERE item_request_id = ?
            """,
            (request_id,),
        ).fetchall()

        for item in items:
            approved_qty = int(approved_items.get(item["id"], 0))

            if approved_qty < 0:
                raise ValueError("Approved quantity cannot be negative.")

            if approved_qty > item["quantity_requested"]:
                raise ValueError("Approved quantity cannot exceed requested quantity.")

            db.execute(
                """
                UPDATE item_request_items
                SET quantity_approved = ?
                WHERE id = ?
                """,
                (approved_qty, item["id"]),
            )

        db.execute(
            """
            UPDATE item_requests
            SET status = 'approved'
            WHERE id = ?
            """,
            (request_id,),
        )

        db.commit()

    except Exception:
        db.rollback()
        raise


def reject_item_request(request_id: int) -> None:
    db = get_db()

    request_row = db.execute(
        "SELECT * FROM item_requests WHERE id = ?",
        (request_id,),
    ).fetchone()

    if not request_row:
        raise ValueError("Item request not found.")

    if request_row["status"] not in ("submitted", "approved"):
        raise ValueError("Only submitted or approved requests can be rejected.")

    db.execute(
        """
        UPDATE item_requests
        SET status = 'rejected'
        WHERE id = ?
        """,
        (request_id,),
    )

    db.commit()
