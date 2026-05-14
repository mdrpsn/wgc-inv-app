# WGC Inventory App

A local-first Flask + SQLite inventory management web app for multi-location warehouse and branch operations.

## Core Architecture

Product + Location + Movement Ledger = Inventory Truth

Stock is not stored directly on products. Current stock is calculated from stock_movements by product and location.

## Tech Stack

- Python
- Flask
- SQLite
- Bootstrap
- Jinja templates
- PowerShell patch workflow

## Setup

Run these commands:

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install flask
python apply_schema.py
.\smoke_routes.ps1
python app.py

Open:

http://127.0.0.1:5000

## Modules

- Products
- Suppliers
- Locations
- Purchase Orders
- Purchase Receiving
- Item Requests
- Stock Transfers
- Stock Adjustments
- Reports
- CSV Exports
- Lifecycle Controls

## Architecture Rules

1. Do not add products.current_stock.
2. All inventory changes must use stock_movements.
3. All stock-changing services must call record_stock_movement().
4. Purchase orders do not move stock until receiving.
5. Item requests do not move stock.
6. Transfers must create transfer_out and transfer_in.
7. Use soft delete only with is_active = 0.

## Current Status

Implemented:

- Product create/edit/deactivate/reactivate
- Supplier create/edit/deactivate/reactivate
- Location create/edit/deactivate/reactivate
- Purchase order create/approve/receive/print
- Location stock report
- In-transit report
- Pending request report
- Supplier purchase history
- Purchase receiving history
- CSV exports
- Route smoke test
- Soft-delete safeguards

## Next Priorities

1. Stock adjustment out
2. Page smoke test
3. User login and roles
4. Audit log
5. Dashboard
6. Database backup/export
