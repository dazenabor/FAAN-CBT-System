"""Load questions from seed_questions.csv into the SQLite database.

This script drops and recreates the questions table, then loads questions
from the CSV file with auto-incremented IDs.

Usage: run `python load_seed_questions.py` from the project root.
"""

from pathlib import Path
import sqlite3
import csv
import sys


DB_FILE = Path("cbt.db")
CSV_FILE = Path("seed_questions.csv")


def reset_questions(db_path: Path = DB_FILE, csv_path: Path = CSV_FILE) -> None:
    """Drop the questions table and reload it from CSV.

    Assigns auto-incremented IDs starting from 1.
    """
    # Check if CSV exists
    if not csv_path.exists():
        print(f"⚠ CSV file not found: {csv_path}", file=sys.stderr)
        return

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()

        # Drop and recreate table
        cur.execute("DROP TABLE IF EXISTS questions")
        cur.execute("""
            CREATE TABLE questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_option TEXT NOT NULL
            )
        """)

        # Load from CSV with auto-generated IDs
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise ValueError("CSV file is empty or has no headers")

            inserted = 0
            skipped = 0
            for row in reader:
                try:
                    question = (row.get("question") or "").strip()
                    option_a = (row.get("option_a") or "").strip()
                    option_b = (row.get("option_b") or "").strip()
                    option_c = (row.get("option_c") or "").strip()
                    option_d = (row.get("option_d") or "").strip()
                    correct_option = (row.get("correct_option") or "").strip()

                    # Validate required fields
                    if not question or not correct_option:
                        skipped += 1
                        continue

                    cur.execute("""
                        INSERT INTO questions (question, option_a, option_b, option_c, option_d, correct_option)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (question, option_a, option_b, option_c, option_d, correct_option))
                    inserted += 1

                except (KeyError, ValueError) as e:
                    print(f"⚠ Skipping malformed row: {row} ({e})", file=sys.stderr)
                    skipped += 1

        conn.commit()

    print(f"✅ Questions table refreshed: {inserted} rows inserted (skipped {skipped})")


def main() -> None:
    reset_questions()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error loading questions: {exc}", file=sys.stderr)
        sys.exit(1)
