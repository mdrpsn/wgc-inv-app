PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    location_type TEXT NOT NULL CHECK(location_type IN ('warehouse', 'branch')),
    address TEXT,
    contact_person TEXT,
    phone TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL CHECK(movement_type IN (
        'purchase_receive',
        'transfer_out',
        'transfer_in',
        'adjustment_in',
        'adjustment_out',
        'return_in',
        'return_out',
        'sale_out',
        'damage_out'
    )),
    quantity INTEGER NOT NULL,
    unit_cost REAL NOT NULL DEFAULT 0,
    reference_type TEXT NOT NULL,
    reference_id INTEGER NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS item_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_number TEXT NOT NULL UNIQUE,
    from_location_id INTEGER NOT NULL,
    to_location_id INTEGER NOT NULL,
    request_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    needed_date TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN (
        'draft',
        'submitted',
        'approved',
        'partially_fulfilled',
        'fulfilled',
        'rejected',
        'cancelled'
    )),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (from_location_id) REFERENCES locations(id),
    FOREIGN KEY (to_location_id) REFERENCES locations(id),

    CHECK(from_location_id != to_location_id)
);

CREATE TABLE IF NOT EXISTS item_request_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_request_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity_requested INTEGER NOT NULL CHECK(quantity_requested > 0),
    quantity_approved INTEGER NOT NULL DEFAULT 0 CHECK(quantity_approved >= 0),
    quantity_fulfilled INTEGER NOT NULL DEFAULT 0 CHECK(quantity_fulfilled >= 0),
    notes TEXT,

    FOREIGN KEY (item_request_id) REFERENCES item_requests(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS stock_transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transfer_number TEXT NOT NULL UNIQUE,
    item_request_id INTEGER,
    from_location_id INTEGER NOT NULL,
    to_location_id INTEGER NOT NULL,
    transfer_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN (
        'draft',
        'approved',
        'in_transit',
        'partially_received',
        'received',
        'cancelled'
    )),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (item_request_id) REFERENCES item_requests(id),
    FOREIGN KEY (from_location_id) REFERENCES locations(id),
    FOREIGN KEY (to_location_id) REFERENCES locations(id),

    CHECK(from_location_id != to_location_id)
);

CREATE TABLE IF NOT EXISTS stock_transfer_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_transfer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity_transferred INTEGER NOT NULL CHECK(quantity_transferred > 0),
    quantity_received INTEGER NOT NULL DEFAULT 0 CHECK(quantity_received >= 0),
    unit_cost REAL NOT NULL DEFAULT 0,
    notes TEXT,

    FOREIGN KEY (stock_transfer_id) REFERENCES stock_transfers(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
