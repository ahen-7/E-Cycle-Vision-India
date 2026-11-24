import sqlite3

conn = sqlite3.connect("ecycle_vision.db")
cursor = conn.cursor()

columns = {
    "registration_number": "VARCHAR",
    "document_filename": "VARCHAR",
    "document_path": "VARCHAR",
    "verification_notes": "TEXT",
    "verified_at": "DATETIME"
}

existing_columns = [
    row[1] for row in cursor.execute(
        "PRAGMA table_info(partner_applications)"
    ).fetchall()
]

for column, data_type in columns.items():
    if column not in existing_columns:
        cursor.execute(
            f"ALTER TABLE partner_applications ADD COLUMN {column} {data_type}"
        )
        print(f"Added: {column}")
    else:
        print(f"Already exists: {column}")

conn.commit()
conn.close()

print("Verification database migration completed!")