from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db
from services.inventory_service import record_stock_movement

bp = Blueprint("stock_adjustments", __name__, url_prefix="/stock-adjustments")


@bp.route("/")
def index():
    db = get_db()

    rows = db.execute(
        """
        SELECT
            sm.id,
            sm.created_at,
            sm.movement_type,
            sm.quantity,
            sm.unit_cost,
            sm.reason,
            p.sku,
            p.name AS product_name,
            l.name AS location_name
        FROM stock_movements sm
        JOIN products p ON p.id = sm.product_id
        JOIN locations l ON l.id = sm.location_id
        WHERE sm.movement_type IN ('adjustment_in', 'adjustment_out')
        ORDER BY sm.created_at DESC
        """
    ).fetchall()

    return render_template("stock_adjustments/index.html", rows=rows)


@bp.route("/new", methods=["GET", "POST"])
def create():
    db = get_db()

    if request.method == "POST":
        product_id = int(request.form["product_id"])
        location_id = int(request.form["location_id"])
        quantity = int(request.form["quantity"])
        unit_cost = float(request.form.get("unit_cost") or 0)
        reason = request.form.get("reason", "").strip()

        if quantity <= 0:
            flash("Quantity must be greater than zero.", "error")
            return redirect(url_for("stock_adjustments.create"))

        if not reason:
            reason = "Starting stock adjustment"

        try:
            db.execute("BEGIN")

            record_stock_movement(
                product_id=product_id,
                location_id=location_id,
                movement_type="adjustment_in",
                quantity=quantity,
                unit_cost=unit_cost,
                reference_type="stock_adjustment",
                reference_id=0,
                reason=reason,
            )

            db.commit()
            flash("Starting stock adjustment posted.", "success")
            return redirect(url_for("reports.location_stock"))

        except Exception as e:
            db.rollback()
            flash(str(e), "error")

    products = db.execute(
        """
        SELECT *
        FROM products
        WHERE is_active = 1
        ORDER BY name
        """
    ).fetchall()

    locations = db.execute(
        """
        SELECT *
        FROM locations
        WHERE is_active = 1
        ORDER BY location_type, name
        """
    ).fetchall()

    return render_template(
        "stock_adjustments/create.html",
        products=products,
        locations=locations,
    )
