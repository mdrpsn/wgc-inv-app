from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db
from services.item_request_service import (
    submit_item_request,
    approve_item_request,
    reject_item_request,
)

bp = Blueprint("item_requests", __name__, url_prefix="/item-requests")


@bp.route("/")
def index():
    db = get_db()

    requests = db.execute(
        """
        SELECT
            ir.*,
            fl.name AS from_location,
            tl.name AS to_location
        FROM item_requests ir
        JOIN locations fl ON fl.id = ir.from_location_id
        JOIN locations tl ON tl.id = ir.to_location_id
        ORDER BY ir.created_at DESC
        """
    ).fetchall()

    return render_template("item_requests/index.html", requests=requests)


@bp.route("/new", methods=["GET", "POST"])
def create():
    db = get_db()

    if request.method == "POST":
        request_number = request.form["request_number"].strip()
        from_location_id = int(request.form["from_location_id"])
        to_location_id = int(request.form["to_location_id"])
        needed_date = request.form.get("needed_date") or None
        notes = request.form.get("notes", "").strip()

        if from_location_id == to_location_id:
            flash("Request source and destination cannot be the same.", "error")
            return redirect(url_for("item_requests.create"))

        try:
            db.execute("BEGIN")

            db.execute(
                """
                INSERT INTO item_requests (
                    request_number,
                    from_location_id,
                    to_location_id,
                    needed_date,
                    notes
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (request_number, from_location_id, to_location_id, needed_date, notes),
            )

            request_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

            product_ids = request.form.getlist("product_id[]")
            quantities = request.form.getlist("quantity[]")

            for product_id, quantity in zip(product_ids, quantities):
                if not product_id or not quantity:
                    continue

                qty = int(quantity)

                if qty <= 0:
                    continue

                db.execute(
                    """
                    INSERT INTO item_request_items (
                        item_request_id,
                        product_id,
                        quantity_requested
                    )
                    VALUES (?, ?, ?)
                    """,
                    (request_id, int(product_id), qty),
                )

            db.commit()
            flash("Item request created.", "success")
            return redirect(url_for("item_requests.view", request_id=request_id))

        except Exception as e:
            db.rollback()
            flash(str(e), "error")

    locations = db.execute(
        "SELECT * FROM locations WHERE is_active = 1 ORDER BY name"
    ).fetchall()

    products = db.execute(
        "SELECT * FROM products WHERE is_active = 1 ORDER BY name"
    ).fetchall()

    return render_template(
        "item_requests/create.html",
        locations=locations,
        products=products,
    )


@bp.route("/<int:request_id>")
def view(request_id):
    db = get_db()

    item_request = db.execute(
        """
        SELECT
            ir.*,
            fl.name AS from_location,
            tl.name AS to_location
        FROM item_requests ir
        JOIN locations fl ON fl.id = ir.from_location_id
        JOIN locations tl ON tl.id = ir.to_location_id
        WHERE ir.id = ?
        """,
        (request_id,),
    ).fetchone()

    items = db.execute(
        """
        SELECT
            iri.*,
            p.sku,
            p.name AS product_name
        FROM item_request_items iri
        JOIN products p ON p.id = iri.product_id
        WHERE iri.item_request_id = ?
        """,
        (request_id,),
    ).fetchall()

    return render_template(
        "item_requests/view.html",
        item_request=item_request,
        items=items,
    )


@bp.route("/<int:request_id>/submit", methods=["POST"])
def submit(request_id):
    try:
        submit_item_request(request_id)
        flash("Item request submitted.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("item_requests.view", request_id=request_id))


@bp.route("/<int:request_id>/approve", methods=["POST"])
def approve(request_id):
    approved_items = {}

    for key, value in request.form.items():
        if key.startswith("approved_qty_"):
            item_id = int(key.replace("approved_qty_", ""))
            approved_items[item_id] = int(value or 0)

    try:
        approve_item_request(request_id, approved_items)
        flash("Item request approved.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("item_requests.view", request_id=request_id))


@bp.route("/<int:request_id>/reject", methods=["POST"])
def reject(request_id):
    try:
        reject_item_request(request_id)
        flash("Item request rejected.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("item_requests.view", request_id=request_id))
