import csv
import io
from flask import Blueprint, render_template, request, Response
from database import get_db

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/location-stock")
def location_stock():
    db = get_db()

    rows = db.execute(
        """
        SELECT
            l.name AS location_name,
            l.location_type,
            p.sku,
            p.name AS product_name,
            COALESCE(SUM(sm.quantity), 0) AS current_stock,
            COALESCE(SUM(sm.quantity * sm.unit_cost), 0) AS stock_value
        FROM locations l
        CROSS JOIN products p
        LEFT JOIN stock_movements sm
            ON sm.location_id = l.id
           AND sm.product_id = p.id
        WHERE l.is_active = 1
          AND p.is_active = 1
        GROUP BY l.id, p.id
        ORDER BY l.name, p.name
        """
    ).fetchall()

    return render_template("reports/location_stock.html", rows=rows)


@bp.route("/in-transit")
def in_transit():
    db = get_db()

    rows = db.execute(
        """
        SELECT
            st.transfer_number,
            fl.name AS from_location,
            tl.name AS to_location,
            p.sku,
            p.name AS product_name,
            sti.quantity_transferred,
            sti.quantity_received,
            sti.quantity_transferred - sti.quantity_received AS in_transit_qty,
            st.status,
            st.created_at
        FROM stock_transfers st
        JOIN stock_transfer_items sti
            ON sti.stock_transfer_id = st.id
        JOIN products p
            ON p.id = sti.product_id
        JOIN locations fl
            ON fl.id = st.from_location_id
        JOIN locations tl
            ON tl.id = st.to_location_id
        WHERE st.status IN ('in_transit', 'partially_received')
          AND sti.quantity_transferred > sti.quantity_received
        ORDER BY st.created_at DESC
        """
    ).fetchall()

    return render_template("reports/in_transit.html", rows=rows)


@bp.route("/pending-requests")
def pending_requests():
    db = get_db()

    rows = db.execute(
        """
        SELECT
            ir.request_number,
            fl.name AS from_location,
            tl.name AS to_location,
            p.sku,
            p.name AS product_name,
            iri.quantity_requested,
            iri.quantity_approved,
            iri.quantity_fulfilled,
            ir.status,
            ir.created_at
        FROM item_requests ir
        JOIN item_request_items iri
            ON iri.item_request_id = ir.id
        JOIN products p
            ON p.id = iri.product_id
        JOIN locations fl
            ON fl.id = ir.from_location_id
        JOIN locations tl
            ON tl.id = ir.to_location_id
        WHERE ir.status IN ('submitted', 'approved', 'partially_fulfilled')
        ORDER BY ir.created_at DESC
        """
    ).fetchall()

    return render_template("reports/pending_requests.html", rows=rows)


@bp.route("/supplier-purchase-history")
def supplier_purchase_history():
    db = get_db()

    supplier_id = request.args.get("supplier_id", "")
    product_id = request.args.get("product_id", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    filters = []
    params = []

    if supplier_id:
        filters.append("po.supplier_id = ?")
        params.append(supplier_id)

    if product_id:
        filters.append("poi.product_id = ?")
        params.append(product_id)

    if date_from:
        filters.append("po.order_date >= ?")
        params.append(date_from)

    if date_to:
        filters.append("po.order_date <= ?")
        params.append(date_to)

    where_sql = ""
    if filters:
        where_sql = "WHERE " + " AND ".join(filters)

    rows = db.execute(
        f"""
        SELECT
            po.po_number,
            po.order_date,
            po.expected_date,
            po.status,
            s.name AS supplier_name,
            p.sku,
            p.name AS product_name,
            poi.quantity_ordered,
            poi.quantity_received,
            poi.unit_cost,
            poi.quantity_ordered * poi.unit_cost AS ordered_total,
            poi.quantity_received * poi.unit_cost AS received_total
        FROM purchase_orders po
        JOIN suppliers s ON s.id = po.supplier_id
        JOIN purchase_order_items poi ON poi.purchase_order_id = po.id
        JOIN products p ON p.id = poi.product_id
        {where_sql}
        ORDER BY po.order_date DESC, po.po_number DESC, p.name
        """,
        params,
    ).fetchall()

    totals = {
        "ordered_qty": sum(row["quantity_ordered"] or 0 for row in rows),
        "received_qty": sum(row["quantity_received"] or 0 for row in rows),
        "ordered_total": sum(row["ordered_total"] or 0 for row in rows),
        "received_total": sum(row["received_total"] or 0 for row in rows),
    }

    suppliers = db.execute(
        "SELECT * FROM suppliers WHERE is_active = 1 ORDER BY name"
    ).fetchall()

    products = db.execute(
        "SELECT * FROM products WHERE is_active = 1 ORDER BY name"
    ).fetchall()

    return render_template(
        "reports/supplier_purchase_history.html",
        rows=rows,
        totals=totals,
        suppliers=suppliers,
        products=products,
        selected_supplier_id=supplier_id,
        selected_product_id=product_id,
        date_from=date_from,
        date_to=date_to,
    )


@bp.route("/purchase-receiving-history")
def purchase_receiving_history():
    db = get_db()

    supplier_id = request.args.get("supplier_id", "")
    warehouse_id = request.args.get("warehouse_id", "")
    product_id = request.args.get("product_id", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    filters = ["sm.movement_type = 'purchase_receive'"]
    params = []

    if supplier_id:
        filters.append("po.supplier_id = ?")
        params.append(supplier_id)

    if warehouse_id:
        filters.append("sm.location_id = ?")
        params.append(warehouse_id)

    if product_id:
        filters.append("sm.product_id = ?")
        params.append(product_id)

    if date_from:
        filters.append("date(sm.created_at) >= ?")
        params.append(date_from)

    if date_to:
        filters.append("date(sm.created_at) <= ?")
        params.append(date_to)

    where_sql = "WHERE " + " AND ".join(filters)

    rows = db.execute(
        f"""
        SELECT
            sm.created_at,
            sm.quantity,
            sm.unit_cost,
            sm.quantity * sm.unit_cost AS received_value,
            sm.reason,
            po.po_number,
            po.status AS po_status,
            s.name AS supplier_name,
            l.name AS warehouse_name,
            p.sku,
            p.name AS product_name
        FROM stock_movements sm
        JOIN purchase_orders po
            ON po.id = sm.reference_id
           AND sm.reference_type = 'purchase_order'
        JOIN suppliers s ON s.id = po.supplier_id
        JOIN locations l ON l.id = sm.location_id
        JOIN products p ON p.id = sm.product_id
        {where_sql}
        ORDER BY sm.created_at DESC
        """,
        params,
    ).fetchall()

    totals = {
        "received_qty": sum(row["quantity"] or 0 for row in rows),
        "received_value": sum(row["received_value"] or 0 for row in rows),
    }

    suppliers = db.execute(
        "SELECT * FROM suppliers WHERE is_active = 1 ORDER BY name"
    ).fetchall()

    warehouses = db.execute(
        """
        SELECT *
        FROM locations
        WHERE is_active = 1
          AND location_type = 'warehouse'
        ORDER BY name
        """
    ).fetchall()

    products = db.execute(
        "SELECT * FROM products WHERE is_active = 1 ORDER BY name"
    ).fetchall()

    return render_template(
        "reports/purchase_receiving_history.html",
        rows=rows,
        totals=totals,
        suppliers=suppliers,
        warehouses=warehouses,
        products=products,
        selected_supplier_id=supplier_id,
        selected_warehouse_id=warehouse_id,
        selected_product_id=product_id,
        date_from=date_from,
        date_to=date_to,
    )


def csv_response(filename, headers, rows):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(headers)

    for row in rows:
        writer.writerow(row)

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


def get_report_filters():
    return {
        "supplier_id": request.args.get("supplier_id", ""),
        "warehouse_id": request.args.get("warehouse_id", ""),
        "product_id": request.args.get("product_id", ""),
        "date_from": request.args.get("date_from", ""),
        "date_to": request.args.get("date_to", ""),
    }

@bp.route("/location-stock.csv")
def location_stock_csv():
    db = get_db()

    rows = db.execute(
        """
        SELECT
            l.name AS location_name,
            l.location_type,
            p.sku,
            p.name AS product_name,
            COALESCE(SUM(sm.quantity), 0) AS current_stock,
            COALESCE(SUM(sm.quantity * sm.unit_cost), 0) AS stock_value
        FROM locations l
        CROSS JOIN products p
        LEFT JOIN stock_movements sm
            ON sm.location_id = l.id
           AND sm.product_id = p.id
        WHERE l.is_active = 1
          AND p.is_active = 1
        GROUP BY l.id, p.id
        ORDER BY l.name, p.name
        """
    ).fetchall()

    csv_rows = [
        [
            row["location_name"],
            row["location_type"],
            row["sku"],
            row["product_name"],
            row["current_stock"],
            row["stock_value"],
        ]
        for row in rows
    ]

    return csv_response(
        "location_stock.csv",
        [
            "Location",
            "Location Type",
            "SKU",
            "Product",
            "Current Stock",
            "Stock Value",
        ],
        csv_rows,
    )


@bp.route("/in-transit.csv")
def in_transit_csv():
    db = get_db()

    rows = db.execute(
        """
        SELECT
            st.transfer_number,
            fl.name AS from_location,
            tl.name AS to_location,
            p.sku,
            p.name AS product_name,
            sti.quantity_transferred,
            sti.quantity_received,
            sti.quantity_transferred - sti.quantity_received AS in_transit_qty,
            st.status,
            st.created_at
        FROM stock_transfers st
        JOIN stock_transfer_items sti
            ON sti.stock_transfer_id = st.id
        JOIN products p
            ON p.id = sti.product_id
        JOIN locations fl
            ON fl.id = st.from_location_id
        JOIN locations tl
            ON tl.id = st.to_location_id
        WHERE st.status IN ('in_transit', 'partially_received')
          AND sti.quantity_transferred > sti.quantity_received
        ORDER BY st.created_at DESC
        """
    ).fetchall()

    csv_rows = [
        [
            row["transfer_number"],
            row["from_location"],
            row["to_location"],
            row["sku"],
            row["product_name"],
            row["quantity_transferred"],
            row["quantity_received"],
            row["in_transit_qty"],
            row["status"],
            row["created_at"],
        ]
        for row in rows
    ]

    return csv_response(
        "in_transit_stock.csv",
        [
            "Transfer Number",
            "From Location",
            "To Location",
            "SKU",
            "Product",
            "Quantity Transferred",
            "Quantity Received",
            "In Transit Quantity",
            "Status",
            "Created At",
        ],
        csv_rows,
    )


@bp.route("/pending-requests.csv")
def pending_requests_csv():
    db = get_db()

    rows = db.execute(
        """
        SELECT
            ir.request_number,
            fl.name AS from_location,
            tl.name AS to_location,
            p.sku,
            p.name AS product_name,
            iri.quantity_requested,
            iri.quantity_approved,
            iri.quantity_fulfilled,
            ir.status,
            ir.created_at
        FROM item_requests ir
        JOIN item_request_items iri
            ON iri.item_request_id = ir.id
        JOIN products p
            ON p.id = iri.product_id
        JOIN locations fl
            ON fl.id = ir.from_location_id
        JOIN locations tl
            ON tl.id = ir.to_location_id
        WHERE ir.status IN ('submitted', 'approved', 'partially_fulfilled')
        ORDER BY ir.created_at DESC
        """
    ).fetchall()

    csv_rows = [
        [
            row["request_number"],
            row["from_location"],
            row["to_location"],
            row["sku"],
            row["product_name"],
            row["quantity_requested"],
            row["quantity_approved"],
            row["quantity_fulfilled"],
            row["status"],
            row["created_at"],
        ]
        for row in rows
    ]

    return csv_response(
        "pending_item_requests.csv",
        [
            "Request Number",
            "From Location",
            "To Location",
            "SKU",
            "Product",
            "Quantity Requested",
            "Quantity Approved",
            "Quantity Fulfilled",
            "Status",
            "Created At",
        ],
        csv_rows,
    )


@bp.route("/supplier-purchase-history.csv")
def supplier_purchase_history_csv():
    db = get_db()

    filters = get_report_filters()

    conditions = []
    params = []

    if filters["supplier_id"]:
        conditions.append("po.supplier_id = ?")
        params.append(filters["supplier_id"])

    if filters["product_id"]:
        conditions.append("poi.product_id = ?")
        params.append(filters["product_id"])

    if filters["date_from"]:
        conditions.append("po.order_date >= ?")
        params.append(filters["date_from"])

    if filters["date_to"]:
        conditions.append("po.order_date <= ?")
        params.append(filters["date_to"])

    where_sql = ""
    if conditions:
        where_sql = "WHERE " + " AND ".join(conditions)

    rows = db.execute(
        f"""
        SELECT
            po.po_number,
            po.order_date,
            po.expected_date,
            po.status,
            s.name AS supplier_name,
            p.sku,
            p.name AS product_name,
            poi.quantity_ordered,
            poi.quantity_received,
            poi.unit_cost,
            poi.quantity_ordered * poi.unit_cost AS ordered_total,
            poi.quantity_received * poi.unit_cost AS received_total
        FROM purchase_orders po
        JOIN suppliers s ON s.id = po.supplier_id
        JOIN purchase_order_items poi ON poi.purchase_order_id = po.id
        JOIN products p ON p.id = poi.product_id
        {where_sql}
        ORDER BY po.order_date DESC, po.po_number DESC, p.name
        """,
        params,
    ).fetchall()

    csv_rows = [
        [
            row["po_number"],
            row["order_date"],
            row["expected_date"],
            row["status"],
            row["supplier_name"],
            row["sku"],
            row["product_name"],
            row["quantity_ordered"],
            row["quantity_received"],
            row["unit_cost"],
            row["ordered_total"],
            row["received_total"],
        ]
        for row in rows
    ]

    return csv_response(
        "supplier_purchase_history.csv",
        [
            "PO Number",
            "Order Date",
            "Expected Date",
            "Status",
            "Supplier",
            "SKU",
            "Product",
            "Quantity Ordered",
            "Quantity Received",
            "Unit Cost",
            "Ordered Total",
            "Received Total",
        ],
        csv_rows,
    )


@bp.route("/purchase-receiving-history.csv")
def purchase_receiving_history_csv():
    db = get_db()

    filters = get_report_filters()

    conditions = ["sm.movement_type = 'purchase_receive'"]
    params = []

    if filters["supplier_id"]:
        conditions.append("po.supplier_id = ?")
        params.append(filters["supplier_id"])

    if filters["warehouse_id"]:
        conditions.append("sm.location_id = ?")
        params.append(filters["warehouse_id"])

    if filters["product_id"]:
        conditions.append("sm.product_id = ?")
        params.append(filters["product_id"])

    if filters["date_from"]:
        conditions.append("date(sm.created_at) >= ?")
        params.append(filters["date_from"])

    if filters["date_to"]:
        conditions.append("date(sm.created_at) <= ?")
        params.append(filters["date_to"])

    where_sql = "WHERE " + " AND ".join(conditions)

    rows = db.execute(
        f"""
        SELECT
            sm.created_at,
            sm.quantity,
            sm.unit_cost,
            sm.quantity * sm.unit_cost AS received_value,
            sm.reason,
            po.po_number,
            po.status AS po_status,
            s.name AS supplier_name,
            l.name AS warehouse_name,
            p.sku,
            p.name AS product_name
        FROM stock_movements sm
        JOIN purchase_orders po
            ON po.id = sm.reference_id
           AND sm.reference_type = 'purchase_order'
        JOIN suppliers s ON s.id = po.supplier_id
        JOIN locations l ON l.id = sm.location_id
        JOIN products p ON p.id = sm.product_id
        {where_sql}
        ORDER BY sm.created_at DESC
        """,
        params,
    ).fetchall()

    csv_rows = [
        [
            row["created_at"],
            row["po_number"],
            row["po_status"],
            row["supplier_name"],
            row["warehouse_name"],
            row["sku"],
            row["product_name"],
            row["quantity"],
            row["unit_cost"],
            row["received_value"],
            row["reason"],
        ]
        for row in rows
    ]

    return csv_response(
        "purchase_receiving_history.csv",
        [
            "Received At",
            "PO Number",
            "PO Status",
            "Supplier",
            "Warehouse",
            "SKU",
            "Product",
            "Received Quantity",
            "Unit Cost",
            "Received Value",
            "Reason",
        ],
        csv_rows,
    )
