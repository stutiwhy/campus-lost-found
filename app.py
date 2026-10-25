import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, jsonify
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-development-key")

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get(
    "DATABASE_PATH", str(BASE_DIR / "lost_found.db")
))

CATEGORIES = [
    "Electronics",
    "ID Cards",
    "Books",
    "Bags",
    "Clothing",
    "Accessories",
    "Other"
]


@contextmanager
def get_db():
    """Open a connection, commit on success, roll back on error, always close."""
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db():
    with get_db() as db:
        # WAL lets several gunicorn workers read while one writes.
        db.execute("PRAGMA journal_mode = WAL")
        db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                report_type TEXT NOT NULL
                    CHECK(report_type IN ('Lost', 'Found')),
                status TEXT NOT NULL DEFAULT 'Open'
                    CHECK(status IN ('Open', 'Resolved')),
                created_at TEXT NOT NULL DEFAULT
                    (datetime('now', 'localtime'))
            )
        """)


@app.route("/")
def index():
    search = request.args.get("q", "").strip()
    report_type = request.args.get("type", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "Open").strip()

    query = "SELECT * FROM items WHERE 1=1"
    values = []

    if search:
        query += """
            AND (
                name LIKE ? OR
                description LIKE ? OR
                location LIKE ?
            )
        """
        term = f"%{search}%"
        values.extend([term, term, term])

    if report_type in ("Lost", "Found"):
        query += " AND report_type = ?"
        values.append(report_type)

    if category in CATEGORIES:
        query += " AND category = ?"
        values.append(category)

    if status in ("Open", "Resolved"):
        query += " AND status = ?"
        values.append(status)

    query += " ORDER BY id DESC"

    with get_db() as db:
        items = db.execute(query, values).fetchall()
        total = db.execute(
            "SELECT COUNT(*) FROM items"
        ).fetchone()[0]
        open_count = db.execute(
            "SELECT COUNT(*) FROM items WHERE status = 'Open'"
        ).fetchone()[0]
        resolved_count = db.execute(
            "SELECT COUNT(*) FROM items WHERE status = 'Resolved'"
        ).fetchone()[0]

    return render_template(
        "index.html",
        items=items,
        categories=CATEGORIES,
        search=search,
        selected_type=report_type,
        selected_category=category,
        selected_status=status,
        total=total,
        open_count=open_count,
        resolved_count=resolved_count
    )


@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        report_type = request.form.get("report_type", "").strip()

        if not all([name, category, description, location, report_type]):
            flash("All fields are required.", "error")
            return render_template(
                "report.html", categories=CATEGORIES
            ), 400

        if category not in CATEGORIES:
            flash("Please select a valid category.", "error")
            return render_template(
                "report.html", categories=CATEGORIES
            ), 400

        if report_type not in ("Lost", "Found"):
            flash("Please select Lost or Found.", "error")
            return render_template(
                "report.html", categories=CATEGORIES
            ), 400

        if any(len(value) > limit for value, limit in [
            (name, 100),
            (description, 1000),
            (location, 150)
        ]):
            flash("One or more fields exceed the allowed length.", "error")
            return render_template(
                "report.html", categories=CATEGORIES
            ), 400

        with get_db() as db:
            db.execute("""
                INSERT INTO items
                    (name, category, description, location, report_type)
                VALUES (?, ?, ?, ?, ?)
            """, (
                name, category, description, location, report_type
            ))

        flash("Your report has been submitted.", "success")
        return redirect(url_for("index"))

    return render_template("report.html", categories=CATEGORIES)


@app.route("/item/<int:item_id>")
def item_detail(item_id):
    with get_db() as db:
        item = db.execute(
            "SELECT * FROM items WHERE id = ?", (item_id,)
        ).fetchone()

    if item is None:
        return render_template("404.html"), 404

    return render_template("item.html", item=item)


@app.route("/resolve/<int:item_id>", methods=["POST"])
def resolve_item(item_id):
    with get_db() as db:
        updated = db.execute("""
            UPDATE items
            SET status = 'Resolved'
            WHERE id = ? AND status = 'Open'
        """, (item_id,)).rowcount

    if updated == 0:
        flash("Item not found or already resolved.", "error")
    else:
        flash("Item marked as resolved.", "success")

    return redirect(url_for("index"))


@app.route("/health")
def health():
    try:
        with get_db() as db:
            db.execute("SELECT 1")
        return jsonify({"status": "ok", "database": "connected"}), 200
    except sqlite3.Error:
        return jsonify({"status": "error", "database": "unavailable"}), 500


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=False
    )