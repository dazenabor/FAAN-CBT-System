"""Create and initialize the SQLite database used by the CBT app.

This script drops and recreates the required tables, seeds a demo admin
and demo user (using `INSERT OR IGNORE` so the script can be re-run),
and loads questions from `seed_questions.csv`.

Usage: run `python init_db.py` from the project root.
"""

from pathlib import Path
import sqlite3
import csv
import sys


DB_PATH = Path("cbt.db")
SEED_CSV = Path("seed_questions.csv")


SCHEMA_SQL = """
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    pin TEXT NOT NULL,
    active INTEGER DEFAULT 1
);

DROP TABLE IF EXISTS questions;
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option TEXT NOT NULL
);

DROP TABLE IF EXISTS answers;
CREATE TABLE answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    question_id INTEGER NOT NULL,
    selected_option TEXT NOT NULL,
    FOREIGN KEY (question_id) REFERENCES questions(id)
);

DROP TABLE IF EXISTS admins;
CREATE TABLE admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    pin TEXT NOT NULL,
    active INTEGER DEFAULT 1
);
"""


def init_db(db_path: Path = DB_PATH) -> None:
    """Create the database schema (drops existing tables)."""
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.executescript(SCHEMA_SQL)


def seed_users(db_path: Path = DB_PATH) -> None:
    """Insert a demo admin and demo user using INSERT OR IGNORE.

    Using OR IGNORE lets the script be idempotent (safe to re-run).
    """
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO admins (username, pin, active) VALUES (?, ?, ?)",
                    ("admin", "admin123", 1))
        cur.execute("INSERT OR IGNORE INTO users (user_id, pin, active) VALUES (?, ?, ?)",
                    ("demo_user", "123456", 1))
        conn.commit()


def load_questions_from_csv(csv_path: Path = SEED_CSV, db_path: Path = DB_PATH) -> None:
    """Load questions from the provided CSV into the `questions` table.

    The CSV must have these headers: question, option_a, option_b, option_c,
    option_d, correct_option.
    """
    if not csv_path.exists():
        print(f"⚠ Seed CSV not found: {csv_path}")
        return

    with sqlite3.connect(db_path) as conn, csv_path.open(newline="", encoding="utf-8") as fh:
        cur = conn.cursor()
        reader = csv.DictReader(fh)
        inserted = 0
        skipped = 0
        for row in reader:
            question = (row.get("question") or "").strip()
            option_a = (row.get("option_a") or "").strip()
            option_b = (row.get("option_b") or "").strip()
            option_c = (row.get("option_c") or "").strip()
            option_d = (row.get("option_d") or "").strip()
            correct_option = (row.get("correct_option") or "").strip()

            if not question or not correct_option:
                skipped += 1
                continue

            cur.execute(
                "INSERT INTO questions (question, option_a, option_b, option_c, option_d, correct_option) VALUES (?, ?, ?, ?, ?, ?)",
                (question, option_a, option_b, option_c, option_d, correct_option),
            )
            inserted += 1

        conn.commit()
    print(f"✅ Loaded {inserted} questions (skipped {skipped} invalid rows)")


def main():
    init_db()
    seed_users()
    load_questions_from_csv()
    print("✅ Database initialized with demo admin, demo user, and questions from CSV.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # keep top-level handler simple for CLI usage
        print("Error initializing DB:", exc, file=sys.stderr)
        raise
