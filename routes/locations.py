from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db
from services.master_data_service import (
    deactivate_location,
    reactivate_location,
    get_location_deactivation_blocks,
)

bp = Blueprint("locations", __name__, url_prefix="/locations")


@bp.route("/")
def index():
    db = get_db()

    locations = db.execute(
        """
        SELECT *
        FROM locations
        ORDER BY is_active DESC, location_type, name
        """
    ).fetchall()

    return render_template("locations/index.html", locations=locations)


@bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        db = get_db()

        name = request.form["name"].strip()
        location_type = request.form["location_type"]
        address = request.form.get("address", "").strip()
        contact_person = request.form.get("contact_person", "").strip()
        phone = request.form.get("phone", "").strip()

        if location_type not in ("warehouse", "branch"):
            flash("Invalid location type.", "error")
            return redirect(url_for("locations.create"))

        try:
            db.execute(
                """
                INSERT INTO locations (
                    name,
                    location_type,
                    address,
                    contact_person,
                    phone
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, location_type, address, contact_person, phone),
            )
            db.commit()
            flash("Location created.", "success")
            return redirect(url_for("locations.index"))
        except Exception as e:
            db.rollback()
            flash(str(e), "error")

    return render_template("locations/create.html")


@bp.route("/<int:location_id>/edit", methods=["GET", "POST"])
def edit(location_id):
    db = get_db()

    location = db.execute(
        "SELECT * FROM locations WHERE id = ?",
        (location_id,),
    ).fetchone()

    if not location:
        flash("Location not found.", "error")
        return redirect(url_for("locations.index"))

    if request.method == "POST":
        name = request.form["name"].strip()
        location_type = request.form["location_type"]
        address = request.form.get("address", "").strip()
        contact_person = request.form.get("contact_person", "").strip()
        phone = request.form.get("phone", "").strip()

        if location_type not in ("warehouse", "branch"):
            flash("Invalid location type.", "error")
            return redirect(url_for("locations.edit", location_id=location_id))

        try:
            db.execute(
                """
                UPDATE locations
                SET
                    name = ?,
                    location_type = ?,
                    address = ?,
                    contact_person = ?,
                    phone = ?
                WHERE id = ?
                """,
                (
                    name,
                    location_type,
                    address,
                    contact_person,
                    phone,
                    location_id,
                ),
            )

            db.commit()
            flash("Location updated.", "success")
            return redirect(url_for("locations.index"))

        except Exception as e:
            db.rollback()
            flash(str(e), "error")

    blocks = get_location_deactivation_blocks(location_id)

    return render_template(
        "locations/edit.html",
        location=location,
        blocks=blocks,
    )


@bp.route("/<int:location_id>/deactivate", methods=["POST"])
def deactivate(location_id):
    try:
        deactivate_location(location_id)
        flash("Location deactivated.", "success")
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("locations.edit", location_id=location_id))


@bp.route("/<int:location_id>/reactivate", methods=["POST"])
def reactivate(location_id):
    reactivate_location(location_id)
    flash("Location reactivated.", "success")
    return redirect(url_for("locations.edit", location_id=location_id))
