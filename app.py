from flask import Flask, redirect, url_for
from database import init_app as init_database_app

from routes.locations import bp as locations_bp
from routes.item_requests import bp as item_requests_bp
from routes.stock_transfers import bp as stock_transfers_bp
from routes.reports import bp as reports_bp
from routes.stock_adjustments import bp as stock_adjustments_bp

# Existing core modules.
# Keep these imports only if the files exist.
try:
    from routes.products import bp as products_bp
except Exception:
    products_bp = None

try:
    from routes.suppliers import bp as suppliers_bp
except Exception:
    suppliers_bp = None

try:
    from routes.purchase_orders import bp as purchase_orders_bp
except Exception:
    purchase_orders_bp = None


app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-change-this-secret-key"
app.config["DATABASE"] = "inventory.db"

init_database_app(app)

app.register_blueprint(locations_bp)
app.register_blueprint(item_requests_bp)
app.register_blueprint(stock_transfers_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(stock_adjustments_bp)

if products_bp:
    app.register_blueprint(products_bp)

if suppliers_bp:
    app.register_blueprint(suppliers_bp)

if purchase_orders_bp:
    app.register_blueprint(purchase_orders_bp)


@app.route("/")
def index():
    if "reports.location_stock" in {rule.endpoint for rule in app.url_map.iter_rules()}:
        return redirect(url_for("reports.location_stock"))

    return "Inventory System is running."


if __name__ == "__main__":
    app.run(debug=True)

