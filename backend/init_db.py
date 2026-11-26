
from database import engine, Base
from sqlalchemy import inspect, text

from models import (
    CollectionRequest,
    TrackingHistory,
    Partner,
    PartnerApplication,
    PartnerOffer,
    RecyclerPriceOffer,
    User,
    Collector,
    MaterialBatch,
    MaterialBatchItem,
    BatchHandover
)

# Create any missing tables
Base.metadata.create_all(bind=engine)


def add_missing_columns(table_name, new_columns):
    inspector = inspect(engine)

    existing_columns = {
        column["name"]
        for column in inspector.get_columns(table_name)
    }

    for column_name, column_type in new_columns.items():
        if column_name not in existing_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        f"ALTER TABLE {table_name} "
                        f"ADD COLUMN {column_name} {column_type}"
                    )
                )
            print(f"Added {table_name}.{column_name}")
        else:
            print(f"{table_name}.{column_name} already exists.")


# Collection requests
add_missing_columns("collection_requests", {
    "user_id": "INTEGER",
    "assigned_partner_id": "INTEGER",
    "assigned_collector_id": "INTEGER",
    "collected_quantity": "INTEGER",
    "collected_weight": "FLOAT",
    "collected_at": "TIMESTAMP WITH TIME ZONE"
})

# Partners
add_missing_columns("partners", {
    "organisation_type": "VARCHAR",
    "verification_status": "VARCHAR DEFAULT 'Pending Verification'",
    "registration_number": "VARCHAR",
    "authorization_details": "TEXT",
    "verification_notes": "TEXT",
    "verified_at": "TIMESTAMP WITH TIME ZONE",
    "latitude": "FLOAT",
    "longitude": "FLOAT"
})

# Partner applications
add_missing_columns("partner_applications", {
    "registration_number": "VARCHAR",
    "document_filename": "VARCHAR",
    "document_path": "VARCHAR",
    "verification_notes": "TEXT",
    "verified_at": "TIMESTAMP WITH TIME ZONE",
    "latitude": "FLOAT",
    "longitude": "FLOAT"
})

# Tracking history
add_missing_columns("tracking_history", {
    "actor_id": "INTEGER",
    "actor_role": "VARCHAR",
    "partner_id": "INTEGER",
    "evidence_path": "VARCHAR",
    "latitude": "FLOAT",
    "longitude": "FLOAT"
})
add_missing_columns("batch_handovers", {
    "price_offer_id": "INTEGER REFERENCES recycler_price_offers(id)",
    "agreed_price_per_kg": "NUMERIC(10, 2)",
    "estimated_amount": "NUMERIC(12, 2)"
})

print("E-Cycle Vision database updated successfully!")
