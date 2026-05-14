$ErrorActionPreference = "Stop"

Write-Host "Running Flask route endpoint smoke test..." -ForegroundColor Cyan

$ProjectRoot = (Get-Location).Path

Write-Host "Project root: $ProjectRoot" -ForegroundColor DarkGray

if (-not (Test-Path "app.py")) {
    Write-Host ""
    Write-Host "FAIL: app.py was not found in the current directory." -ForegroundColor Red
    Write-Host "Move to your Flask project root first, then run:" -ForegroundColor Yellow
    Write-Host "  cd path\to\your\project" -ForegroundColor Yellow
    Write-Host "  .\smoke_routes.ps1" -ForegroundColor Yellow
    exit 1
}

$pythonScript = @"
import os
import sys
import traceback

PROJECT_ROOT = r'''$ProjectRoot'''

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.chdir(PROJECT_ROOT)

REQUIRED_ENDPOINTS = [
    "products.index",
    "products.create",
    "products.edit",
    "products.deactivate",
    "products.reactivate",

    "suppliers.index",
    "suppliers.create",
    "suppliers.edit",
    "suppliers.deactivate",
    "suppliers.reactivate",

    "purchase_orders.index",
    "purchase_orders.create",
    "purchase_orders.view",
    "purchase_orders.approve",
    "purchase_orders.receive",
    "purchase_orders.print_view",

    "locations.index",
    "locations.create",
    "locations.edit",
    "locations.deactivate",
    "locations.reactivate",

    "item_requests.index",
    "item_requests.create",
    "item_requests.view",
    "item_requests.submit",
    "item_requests.approve",
    "item_requests.reject",

    "stock_transfers.index",
    "stock_transfers.create",
    "stock_transfers.view",
    "stock_transfers.approve",
    "stock_transfers.dispatch",
    "stock_transfers.receive",

    "stock_adjustments.index",
    "stock_adjustments.create",

    "reports.location_stock",
    "reports.location_stock_csv",
    "reports.in_transit",
    "reports.in_transit_csv",
    "reports.pending_requests",
    "reports.pending_requests_csv",
    "reports.supplier_purchase_history",
    "reports.supplier_purchase_history_csv",
    "reports.purchase_receiving_history",
    "reports.purchase_receiving_history_csv",
]

try:
    from app import app
except Exception:
    print("FAIL: Could not import Flask app from app.py")
    print("")
    print("Python sys.path:")
    for item in sys.path:
        print("  -", item)
    print("")
    traceback.print_exc()
    sys.exit(1)

try:
    registered_endpoints = sorted(rule.endpoint for rule in app.url_map.iter_rules())
except Exception:
    print("FAIL: Could not inspect Flask url_map.")
    traceback.print_exc()
    sys.exit(1)

missing = [endpoint for endpoint in REQUIRED_ENDPOINTS if endpoint not in registered_endpoints]

print("")
print("Registered endpoints:")
for endpoint in registered_endpoints:
    print(f"  - {endpoint}")

print("")

if missing:
    print("FAIL: Missing required endpoints used by templates/base.html:")
    for endpoint in missing:
        print(f"  - {endpoint}")
    sys.exit(1)

print("PASS: All required navbar endpoints are registered.")
sys.exit(0)
"@

$tempFile = Join-Path $ProjectRoot "_flask_route_smoke_test.py"

Set-Content -Path $tempFile -Value $pythonScript -Encoding UTF8

python $tempFile

$exitCode = $LASTEXITCODE

Remove-Item $tempFile -Force -ErrorAction SilentlyContinue

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "Smoke test failed. Fix the issue above before running the app." -ForegroundColor Red
    exit $exitCode
}

Write-Host ""
Write-Host "Smoke test passed. You can run the Flask app." -ForegroundColor Green






