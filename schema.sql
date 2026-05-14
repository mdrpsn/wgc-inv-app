PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    contact_person TEXT,
    phone TEXT,
    email TEXT,
    address TEXT,
    payment_terms TEXT,
    lead_time_days INTEGER DEFAULT 0,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT,
    unit TEXT NOT NULL DEFAULT 'pcs',
    cost_price REAL NOT NULL DEFAULT 0,
    selling_price REAL NOT NULL DEFAULT 0,
    reorder_level INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    po_number TEXT NOT NULL UNIQUE,
    supplier_id INTEGER NOT NULL,
    order_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    expected_date TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    purchase_order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity_ordered INTEGER NOT NULL CHECK(quantity_ordered > 0),
    quantity_received INTEGER NOT NULL DEFAULT 0 CHECK(quantity_received >= 0),
    unit_cost REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
