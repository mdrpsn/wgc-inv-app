from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db
from services.purchase_order_service import (
    approve_purchase_order,
    receive_purchase_order,
)

bp = Blueprint("purchase_orders", __name__, url_prefix="/purchase-orders")


@bp.route("/")
def index():
    db = get_db()

    purchase_orders = db.execute(
        """
        SELECT
            po.*,
            s.name AS supplier_name
        FROM purchase_orders po
        LEFT JOIN suppliers s ON s.id = po.supplier_id
        ORDER BY po.created_at DESC
        """
    ).fetchall()

    return render_template(
        "purchase_orders/index.html",
        purchase_orders=purchase_orders,
    )


@bp.route("/new", methods=["GET", "POST"])
def create():
    db = get_db()

    if request.method == "POST":
        po_number = request.form["po_number"].strip()
        supplier_id = int(request.form["supplier_id"])
        order_date = request.form.get("order_date") or None
        expected_date = request.form.get("expected_date") or None
        notes = request.form.get("notes", "").strip()

        if not po_number:
            flash("PO number is required.", "error")
            return redirect(url_for("purchase_orders.create"))

        try:
            db.execute("BEGIN")

            db.execute(
                """
                INSERT INTO purchase_orders (
                    po_number,
                    supplier_id,
                    order_date,
                    expected_date,
                    notes
                )
                VALUES (?, ?, COALESCE(?, CURRENT_DATE), ?, ?)
                """,
                (po_number, supplier_id, order_date, expected_date, notes),
            )

            po_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

            product_ids = request.form.getlist("product_id[]")
            quantities = request.form.getlist("quantity[]")
            unit_costs = request.form.getlist("unit_cost[]")

            inserted_items = 0

            for product_id, quantity, unit_cost in zip(product_ids, quantities, unit_costs):
                if not product_id or not quantity:
                    continue

                qty = int(quantity)

                if qty <= 0:
                    continue

                cost = float(unit_cost or 0)

                db.execute(
                    """
                    INSERT INTO purchase_order_items (
                        purchase_order_id,
                        product_id,
                        quantity_ordered,
                        unit_cost
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (po_id, int(product_id), qty, cost),
                )

                inserted_items += 1

            if inserted_items == 0:
                raise ValueError("Purchase order must have at least one item.")

            db.commit()
            flash("Purchase order created.", "success")
            return redirect(url_for("purchase_orders.view", po_id=po_id))

        except Exception as e:
            db.rollback()
            flash(str(e), "error")

    suppliers = db.execute(
        """
        SELECT *
        FROM suppliers
        WHERE is_active = 1
        ORDER BY name
        """
    ).fetchall()

    products = db.execute(
        """
        SELECT *
        FROM products
        WHERE is_active = 1
        ORDER BY name
        """
    ).fetchall()

    return render_template(
        "purchase_orders/create.html",
        suppliers=suppliers,
        products=products,
    )


@bp.route("/<int:po_id>")
def view(po_id):
    db = get_db()

    po = db.execute(
        """
        SELECT
            po.*,
            s.name AS supplier_name
        FROM purchase_orders po
        LEFT JOIN suppliers s ON s.id = po.supplier_id
        WHERE po.id = ?
        """,
        (po_id,),
    ).fetchone()

    if not po:
        flash("Purchase order not found.", "error")
        return redirect(url_for("purchase_orders.index"))

    items = db.execute(
        """
        SELECT
            poi.*,
            p.sku,
            p.name AS product_name
        FROM purchase_order_items poi
        JOIN products p ON p.id = poi.product_id
        WHERE poi.purchase_order_id = ?
        ORDER BY p.name
        """,
        (po_id,),
    ).fetchall()

    return render_template(
        "purchase_orders/view.html",
        po=po,
        items=items,
    )


@bp.route("/<int:po_id>/approve", methods=["POST"])
def approve(po_id):
    try:
        approve_purchase_order(po_id)
        flash("Purchase order approved.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("purchase_orders.view", po_id=po_id))


@bp.route("/<int:po_id>/receive", methods=["GET", "POST"])
def receive(po_id):
    db = get_db()

    if request.method == "POST":
        warehouse_location_id = int(request.form["warehouse_location_id"])
        received_items = {}

        for key, value in request.form.items():
            if key.startswith("received_qty_"):
                item_id = int(key.replace("received_qty_", ""))
                received_items[item_id] = int(value or 0)

        try:
            receive_purchase_order(
                po_id=po_id,
                warehouse_location_id=warehouse_location_id,
                received_items=received_items,
            )
            flash("Purchase order received into warehouse.", "success")
            return redirect(url_for("purchase_orders.view", po_id=po_id))

        except ValueError as e:
            flash(str(e), "error")

    po = db.execute(
        """
        SELECT
            po.*,
            s.name AS supplier_name
        FROM purchase_orders po
        LEFT JOIN suppliers s ON s.id = po.supplier_id
        WHERE po.id = ?
        """,
        (po_id,),
    ).fetchone()

    if not po:
        flash("Purchase order not found.", "error")
        return redirect(url_for("purchase_orders.index"))

    items = db.execute(
        """
        SELECT
            poi.*,
            p.sku,
            p.name AS product_name,
            poi.quantity_ordered - poi.quantity_received AS remaining_qty
        FROM purchase_order_items poi
        JOIN products p ON p.id = poi.product_id
        WHERE poi.purchase_order_id = ?
        ORDER BY p.name
        """,
        (po_id,),
    ).fetchall()

    warehouses = db.execute(
        """
        SELECT *
        FROM locations
        WHERE location_type = 'warehouse'
          AND is_active = 1
        ORDER BY name
        """
    ).fetchall()

    return render_template(
        "purchase_orders/receive.html",
        po=po,
        items=items,
        warehouses=warehouses,
    )


@bp.route("/<int:po_id>/print")
def print_view(po_id):
    db = get_db()

    po = db.execute(
        """
        SELECT
            po.*,
            s.name AS supplier_name,
            s.contact_person,
            s.phone AS supplier_phone,
            s.email AS supplier_email,
            s.address AS supplier_address,
            s.payment_terms
        FROM purchase_orders po
        LEFT JOIN suppliers s ON s.id = po.supplier_id
        WHERE po.id = ?
        """,
        (po_id,),
    ).fetchone()

    if not po:
        flash("Purchase order not found.", "error")
        return redirect(url_for("purchase_orders.index"))

    items = db.execute(
        """
        SELECT
            poi.*,
            p.sku,
            p.name AS product_name,
            p.unit
        FROM purchase_order_items poi
        JOIN products p ON p.id = poi.product_id
        WHERE poi.purchase_order_id = ?
        ORDER BY p.name
        """,
        (po_id,),
    ).fetchall()

    totals = db.execute(
        """
        SELECT
            COALESCE(SUM(quantity_ordered * unit_cost), 0) AS ordered_total,
            COALESCE(SUM(quantity_received * unit_cost), 0) AS received_total
        FROM purchase_order_items
        WHERE purchase_order_id = ?
        """,
        (po_id,),
    ).fetchone()

    return render_template(
        "purchase_orders/print.html",
        po=po,
        items=items,
        totals=totals,
    )
