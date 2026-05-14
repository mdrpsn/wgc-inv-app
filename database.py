import sqlite3
from flask import current_app, g


def get_db():
    if "db" not in g:
        database_path = current_app.config.get("DATABASE", "inventory.db")

        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        g.db = conn

    return g.db


def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db(schema_path="schema.sql"):
    db = get_db()

    with current_app.open_resource(schema_path) as f:
        db.executescript(f.read().decode("utf-8"))

    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
