"""
Verification script to inspect records stored in the PostgreSQL summaries table.
"""

import sys
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Summary


def verify_stored_records(limit: int = 10) -> None:
    """
    Query the database and print recent summary records.
    """
    db = SessionLocal()
    try:
        print(f"\n{'='*70}")
        print("DATABASE RECORD VERIFICATION: 'summaries' table")
        print(f"{'='*70}\n")

        query = select(Summary).order_by(Summary.created_at.desc()).limit(limit)
        records = db.scalars(query).all()

        if not records:
            print("No summary records found in the database.")
            print("Generate a summary via POST /summarize first!")
            return

        print(f"Found {len(records)} recent record(s):\n")
        for record in records:
            print(f"ID:         {record.id}")
            print(f"Created At: {record.created_at}")
            print(f"Input:      {record.original_text[:80]}..." if len(record.original_text) > 80 else f"Input:      {record.original_text}")
            print(f"Summary:    {record.generated_summary[:80]}..." if len(record.generated_summary) > 80 else f"Summary:    {record.generated_summary}")
            print(f"{'-'*70}")

    except Exception as exc:
        print(f"Error querying database: {exc}", file=sys.stderr)
    finally:
        db.close()


if __name__ == "__main__":
    verify_stored_records()
