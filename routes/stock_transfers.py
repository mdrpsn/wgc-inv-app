from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db
from services.transfer_service import (
    approve_transfer,
    dispatch_transfer,
    receive_transfer,
)

bp = Blueprint("stock_transfers", __name__, url_prefix="/stock-transfers")


@bp.route("/")
def index():
    db = get_db()

    transfers = db.execute(
        """
        SELECT
            st.*,
            fl.name AS from_location,
            tl.name AS to_location
        FROM stock_transfers st
        JOIN locations fl ON fl.id = st.from_location_id
        JOIN locations tl ON tl.id = st.to_location_id
        ORDER BY st.created_at DESC
        """
    ).fetchall()

    return render_template("stock_transfers/index.html", transfers=transfers)


@bp.route("/new", methods=["GET", "POST"])
def create():
    db = get_db()

    if request.method == "POST":
        transfer_number = request.form["transfer_number"].strip()
        from_location_id = int(request.form["from_location_id"])
        to_location_id = int(request.form["to_location_id"])
        item_request_id = request.form.get("item_request_id") or None
        notes = request.form.get("notes", "").strip()

        if from_location_id == to_location_id:
            flash("Source and destination cannot be the same.", "error")
            return redirect(url_for("stock_transfers.create"))

        try:
            db.execute("BEGIN")

            db.execute(
                """
                INSERT INTO stock_transfers (
                    transfer_number,
                    item_request_id,
                    from_location_id,
                    to_location_id,
                    notes
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    transfer_number,
                    item_request_id,
                    from_location_id,
                    to_location_id,
                    notes,
                ),
            )

            transfer_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

            product_ids = request.form.getlist("product_id[]")
            quantities = request.form.getlist("quantity[]")
            unit_costs = request.form.getlist("unit_cost[]")

            for product_id, qty, unit_cost in zip(product_ids, quantities, unit_costs):
                if not product_id or not qty:
                    continue

                qty_int = int(qty)

                if qty_int <= 0:
                    continue

                db.execute(
                    """
                    INSERT INTO stock_transfer_items (
                        stock_transfer_id,
                        product_id,
                        quantity_transferred,
                        unit_cost
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (transfer_id, int(product_id), qty_int, float(unit_cost or 0)),
                )

            db.commit()
            flash("Stock transfer created.", "success")
            return redirect(url_for("stock_transfers.view", transfer_id=transfer_id))

        except Exception as e:
            db.rollback()
            flash(str(e), "error")

    locations = db.execute(
        "SELECT * FROM locations WHERE is_active = 1 ORDER BY name"
    ).fetchall()

    products = db.execute(
        "SELECT * FROM products WHERE is_active = 1 ORDER BY name"
    ).fetchall()

    requests = db.execute(
        """
        SELECT *
        FROM item_requests
        WHERE status IN ('approved', 'partially_fulfilled')
        ORDER BY created_at DESC
        """
    ).fetchall()

    return render_template(
        "stock_transfers/create.html",
        locations=locations,
        products=products,
        requests=requests,
    )


@bp.route("/<int:transfer_id>")
def view(transfer_id):
    db = get_db()

    transfer = db.execute(
        """
        SELECT
            st.*,
            fl.name AS from_location,
            tl.name AS to_location
        FROM stock_transfers st
        JOIN locations fl ON fl.id = st.from_location_id
        JOIN locations tl ON tl.id = st.to_location_id
        WHERE st.id = ?
        """,
        (transfer_id,),
    ).fetchone()

    items = db.execute(
        """
        SELECT
            sti.*,
            p.sku,
            p.name AS product_name
        FROM stock_transfer_items sti
        JOIN products p ON p.id = sti.product_id
        WHERE sti.stock_transfer_id = ?
        """,
        (transfer_id,),
    ).fetchall()

    return render_template(
        "stock_transfers/view.html",
        transfer=transfer,
        items=items,
    )


@bp.route("/<int:transfer_id>/approve", methods=["POST"])
def approve(transfer_id):
    try:
        approve_transfer(transfer_id)
        flash("Transfer approved.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("stock_transfers.view", transfer_id=transfer_id))


@bp.route("/<int:transfer_id>/dispatch", methods=["POST"])
def dispatch(transfer_id):
    try:
        dispatch_transfer(transfer_id)
        flash("Transfer dispatched. Stock deducted from source location.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("stock_transfers.view", transfer_id=transfer_id))


@bp.route("/<int:transfer_id>/receive", methods=["GET", "POST"])
def receive(transfer_id):
    db = get_db()

    if request.method == "POST":
        received_items = {}

        for key, value in request.form.items():
            if key.startswith("received_qty_"):
                item_id = int(key.replace("received_qty_", ""))
                received_items[item_id] = int(value or 0)

        try:
            receive_transfer(transfer_id, received_items)
            flash("Transfer received.", "success")
        except ValueError as e:
            flash(str(e), "error")

        return redirect(url_for("stock_transfers.view", transfer_id=transfer_id))

    transfer = db.execute(
        """
        SELECT
            st.*,
            fl.name AS from_location,
            tl.name AS to_location
        FROM stock_transfers st
        JOIN locations fl ON fl.id = st.from_location_id
        JOIN locations tl ON tl.id = st.to_location_id
        WHERE st.id = ?
        """,
        (transfer_id,),
    ).fetchone()

    items = db.execute(
        """
        SELECT
            sti.*,
            p.sku,
            p.name AS product_name,
            sti.quantity_transferred - sti.quantity_received AS remaining_qty
        FROM stock_transfer_items sti
        JOIN products p ON p.id = sti.product_id
        WHERE sti.stock_transfer_id = ?
        """,
        (transfer_id,),
    ).fetchall()

    return render_template(
        "stock_transfers/receive.html",
        transfer=transfer,
        items=items,
    )
