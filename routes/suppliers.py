from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db
from services.master_data_service import (
    deactivate_supplier,
    reactivate_supplier,
    get_supplier_deactivation_blocks,
)

bp = Blueprint("suppliers", __name__, url_prefix="/suppliers")


@bp.route("/")
def index():
    db = get_db()

    suppliers = db.execute(
        """
        SELECT *
        FROM suppliers
        ORDER BY is_active DESC, name
        """
    ).fetchall()

    return render_template("suppliers/index.html", suppliers=suppliers)


@bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        db = get_db()

        name = request.form["name"].strip()
        contact_person = request.form.get("contact_person", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        payment_terms = request.form.get("payment_terms", "").strip()
        lead_time_days = int(request.form.get("lead_time_days") or 0)
        notes = request.form.get("notes", "").strip()

        if not name:
            flash("Supplier name is required.", "error")
            return redirect(url_for("suppliers.create"))

        try:
            db.execute(
                """
                INSERT INTO suppliers (
                    name,
                    contact_person,
                    phone,
                    email,
                    address,
                    payment_terms,
                    lead_time_days,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    contact_person,
                    phone,
                    email,
                    address,
                    payment_terms,
                    lead_time_days,
                    notes,
                ),
            )

            db.commit()
            flash("Supplier created.", "success")
            return redirect(url_for("suppliers.index"))

        except Exception as e:
            db.rollback()
            flash(str(e), "error")

    return render_template("suppliers/create.html")


@bp.route("/<int:supplier_id>/edit", methods=["GET", "POST"])
def edit(supplier_id):
    db = get_db()

    supplier = db.execute(
        "SELECT * FROM suppliers WHERE id = ?",
        (supplier_id,),
    ).fetchone()

    if not supplier:
        flash("Supplier not found.", "error")
        return redirect(url_for("suppliers.index"))

    if request.method == "POST":
        name = request.form["name"].strip()
        contact_person = request.form.get("contact_person", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        payment_terms = request.form.get("payment_terms", "").strip()
        lead_time_days = int(request.form.get("lead_time_days") or 0)
        notes = request.form.get("notes", "").strip()

        try:
            db.execute(
                """
                UPDATE suppliers
                SET
                    name = ?,
                    contact_person = ?,
                    phone = ?,
                    email = ?,
                    address = ?,
                    payment_terms = ?,
                    lead_time_days = ?,
                    notes = ?
                WHERE id = ?
                """,
                (
                    name,
                    contact_person,
                    phone,
                    email,
                    address,
                    payment_terms,
                    lead_time_days,
                    notes,
                    supplier_id,
                ),
            )

            db.commit()
            flash("Supplier updated.", "success")
            return redirect(url_for("suppliers.index"))

        except Exception as e:
            db.rollback()
            flash(str(e), "error")

    blocks = get_supplier_deactivation_blocks(supplier_id)

    return render_template(
        "suppliers/edit.html",
        supplier=supplier,
        blocks=blocks,
    )


@bp.route("/<int:supplier_id>/deactivate", methods=["POST"])
def deactivate(supplier_id):
    try:
        deactivate_supplier(supplier_id)
        flash("Supplier deactivated.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("suppliers.edit", supplier_id=supplier_id))


@bp.route("/<int:supplier_id>/reactivate", methods=["POST"])
def reactivate(supplier_id):
    reactivate_supplier(supplier_id)
    flash("Supplier reactivated.", "success")
    return redirect(url_for("suppliers.edit", supplier_id=supplier_id))
