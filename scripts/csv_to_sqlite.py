#!/usr/bin/env python3
"""
Convert wine_data.csv to wine_data.db SQLite database.
Optimized for read-only access with proper indexes.
"""

import csv
import sqlite3
import sys
from pathlib import Path


def create_sqlite_db(csv_path: str, db_path: str):
    """Convert CSV to SQLite database with optimizations."""

    # Remove existing database if it exists
    db_file = Path(db_path)
    if db_file.exists():
        print(f"Removing existing database: {db_path}")
        db_file.unlink()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table matching PostgreSQL schema
    cursor.execute("""
        CREATE TABLE wine_descriptions (
            id TEXT PRIMARY KEY,
            name TEXT,
            category_1 TEXT,
            category_2 TEXT,
            origin TEXT,
            description TEXT
        )
    """)

    # Create index on category_2 for faster filtering
    cursor.execute("""
        CREATE INDEX idx_category_2 ON wine_descriptions(category_2)
    """)

    # Import CSV data
    print(f"Reading CSV from: {csv_path}")
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append(
                (row["id"], row["name"], row["category_1"], row["category_2"], row["origin"], row["description"])
            )

        cursor.executemany(
            """
            INSERT INTO wine_descriptions
            (id, name, category_1, category_2, origin, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            rows,
        )

        print(f"Inserted {len(rows)} wine descriptions")

    # Optimize database for read-only access
    cursor.execute("ANALYZE")
    cursor.execute("PRAGMA journal_mode=WAL")

    # Get statistics before committing
    cursor.execute("SELECT COUNT(*) FROM wine_descriptions")
    count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT category_2) FROM wine_descriptions")
    categories = cursor.fetchone()[0]

    conn.commit()
    cursor.close()

    # VACUUM must be run outside a transaction with no active cursors
    conn.execute("VACUUM")

    db_size = db_file.stat().st_size / (1024 * 1024)  # MB

    print("\n✅ Database created successfully!")
    print(f"  Location: {db_path}")
    print(f"  Size: {db_size:.2f} MB")
    print(f"  Records: {count:,}")
    print(f"  Categories: {categories}")

    conn.close()


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent

    csv_path = project_dir / "wine_data.csv"
    db_path = project_dir / "wine_data.db"

    if not csv_path.exists():
        print(f"❌ Error: CSV file not found at {csv_path}")
        sys.exit(1)

    create_sqlite_db(str(csv_path), str(db_path))
