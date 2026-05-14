from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db
from services.master_data_service import (
    deactivate_product,
    reactivate_product,
    get_product_deactivation_blocks,
)

bp = Blueprint("products", __name__, url_prefix="/products")


@bp.route("/")
def index():
    db = get_db()

    products = db.execute(
        """
        SELECT *
        FROM products
        ORDER BY is_active DESC, name
        """
    ).fetchall()

    return render_template("products/index.html", products=products)


@bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        db = get_db()

        sku = request.form["sku"].strip()
        name = request.form["name"].strip()
        category = request.form.get("category", "").strip()
        unit = request.form.get("unit", "pcs").strip() or "pcs"
        cost_price = float(request.form.get("cost_price") or 0)
        selling_price = float(request.form.get("selling_price") or 0)
        reorder_level = int(request.form.get("reorder_level") or 0)

        if not sku:
            flash("SKU is required.", "error")
            return redirect(url_for("products.create"))

        if not name:
            flash("Product name is required.", "error")
            return redirect(url_for("products.create"))

        try:
            db.execute(
                """
                INSERT INTO products (
                    sku,
                    name,
                    category,
                    unit,
                    cost_price,
                    selling_price,
                    reorder_level
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sku,
                    name,
                    category,
                    unit,
                    cost_price,
                    selling_price,
                    reorder_level,
                ),
            )

            db.commit()
            flash("Product created.", "success")
            return redirect(url_for("products.index"))

        except Exception as e:
            db.rollback()
            flash(str(e), "error")

    return render_template("products/create.html")


@bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
def edit(product_id):
    db = get_db()

    product = db.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()

    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("products.index"))

    if request.method == "POST":
        sku = request.form["sku"].strip()
        name = request.form["name"].strip()
        category = request.form.get("category", "").strip()
        unit = request.form.get("unit", "pcs").strip() or "pcs"
        cost_price = float(request.form.get("cost_price") or 0)
        selling_price = float(request.form.get("selling_price") or 0)
        reorder_level = int(request.form.get("reorder_level") or 0)

        try:
            db.execute(
                """
                UPDATE products
                SET
                    sku = ?,
                    name = ?,
                    category = ?,
                    unit = ?,
                    cost_price = ?,
                    selling_price = ?,
                    reorder_level = ?
                WHERE id = ?
                """,
                (
                    sku,
                    name,
                    category,
                    unit,
                    cost_price,
                    selling_price,
                    reorder_level,
                    product_id,
                ),
            )
            db.commit()
            flash("Product updated.", "success")
            return redirect(url_for("products.index"))

        except Exception as e:
            db.rollback()
            flash(str(e), "error")

    blocks = get_product_deactivation_blocks(product_id)

    return render_template(
        "products/edit.html",
        product=product,
        blocks=blocks,
    )


@bp.route("/<int:product_id>/deactivate", methods=["POST"])
def deactivate(product_id):
    try:
        deactivate_product(product_id)
        flash("Product deactivated.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("products.edit", product_id=product_id))


@bp.route("/<int:product_id>/reactivate", methods=["POST"])
def reactivate(product_id):
    reactivate_product(product_id)
    flash("Product reactivated.", "success")
    return redirect(url_for("products.edit", product_id=product_id))
