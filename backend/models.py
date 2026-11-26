
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey, Float,Numeric
)
from sqlalchemy.sql import func
from database import Base


# ==========================================
# COLLECTION REQUESTS
# ==========================================

class CollectionRequest(Base):
    __tablename__ = "collection_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)

    tracking_id = Column(String, unique=True, index=True, nullable=False)
    requester_name = Column(String, nullable=False)
    requester_type = Column(String, nullable=False)

    device_category = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    condition = Column(String, nullable=False)

    state = Column(String, nullable=False)
    district = Column(String, nullable=False)
    city = Column(String, nullable=False)
    pincode = Column(String, nullable=False)

    status = Column(String, default="Requested")

    assigned_partner = Column(String, nullable=True)
    assigned_partner_id = Column(
        Integer,
        ForeignKey("partners.id"),
        nullable=True,
        index=True
    )

    # New collector assignment and pickup details
    assigned_collector_id = Column(
        Integer,
        ForeignKey("collectors.id"),
        nullable=True,
        index=True
    )

    collected_quantity = Column(Integer, nullable=True)
    collected_weight = Column(Float, nullable=True)
    collected_at = Column(DateTime(timezone=True), nullable=True)

    description = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ==========================================
# TRACKING HISTORY
# ==========================================

class TrackingHistory(Base):
    __tablename__ = "tracking_history"

    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(String, index=True, nullable=False)

    status = Column(String, nullable=False)
    remarks = Column(Text, nullable=True)

    actor_id = Column(Integer, nullable=True)
    actor_role = Column(String, nullable=True)
    partner_id = Column(Integer, nullable=True)

    evidence_path = Column(String, nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ==========================================
# PARTNERS
# ==========================================

class Partner(Base):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, index=True)

    partner_name = Column(String, nullable=False)
    organisation_type = Column(String, nullable=True)

    state = Column(String, nullable=False)
    district = Column(String, nullable=False)
    city = Column(String, nullable=False)
    pincode = Column(String, nullable=False)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    accepted_categories = Column(Text, nullable=False)
    capacity = Column(Integer, default=100)

    verification_status = Column(
        String,
        default="Pending Verification"
    )

    registration_number = Column(String, nullable=True)
    authorization_details = Column(Text, nullable=True)
    verification_notes = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Integer, default=1)
    is_demo = Column(Integer, default=1)


# ==========================================
# PARTNER APPLICATIONS
# ==========================================

class PartnerApplication(Base):
    __tablename__ = "partner_applications"

    id = Column(Integer, primary_key=True, index=True)

    organisation_name = Column(String, nullable=False)
    contact_person = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)

    state = Column(String, nullable=False)
    district = Column(String, nullable=False)
    city = Column(String, nullable=False)
    pincode = Column(String, nullable=False)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    accepted_categories = Column(Text, nullable=False)
    capacity = Column(Integer, nullable=False)

    organisation_type = Column(String, nullable=False)
    authorization_details = Column(Text, nullable=True)

    status = Column(
        String,
        default="Pending Verification"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    registration_number = Column(String, nullable=True)
    document_filename = Column(String, nullable=True)
    document_path = Column(String, nullable=True)

    verification_notes = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)


# ==========================================
# PARTNER OFFERS
# ==========================================

class PartnerOffer(Base):
    __tablename__ = "partner_offers"

    id = Column(Integer, primary_key=True, index=True)

    request_id = Column(
        Integer,
        ForeignKey("collection_requests.id"),
        nullable=False,
        index=True
    )

    partner_id = Column(
        Integer,
        ForeignKey("partners.id"),
        nullable=False,
        index=True
    )

    status = Column(String, default="Offered", nullable=False)

    matching_score = Column(Integer, nullable=True)
    matching_reasons = Column(Text, nullable=True)
    response_remarks = Column(Text, nullable=True)

    offered_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    responded_at = Column(DateTime(timezone=True), nullable=True)


# ==========================================
# RECYCLER PRICE OFFERS
# Recyclers publish material purchase rates
# ==========================================

class RecyclerPriceOffer(Base):
    __tablename__ = "recycler_price_offers"

    id = Column(Integer, primary_key=True, index=True)

    recycler_id = Column(
        Integer,
        ForeignKey("partners.id"),
        nullable=False,
        index=True
    )

    material_category = Column(String, nullable=False)

    price_per_kg = Column(Numeric(10, 2), nullable=False)

    minimum_quantity_kg = Column(
        Numeric(10, 2),
        nullable=True
    )

    valid_until = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        String,
        default="Active",
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

# ==========================================
# USERS
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # user, aggregator, recycler, admin
    role = Column(String, default="user", nullable=False)

    partner_id = Column(Integer, nullable=True)

    is_active = Column(Integer, default=1)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ==========================================
# COLLECTORS
# Managed by an aggregator
# ==========================================

class Collector(Base):
    __tablename__ = "collectors"

    id = Column(Integer, primary_key=True, index=True)

    aggregator_id = Column(
        Integer,
        ForeignKey("partners.id"),
        nullable=False,
        index=True
    )

    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)

    service_area = Column(String, nullable=True)
    preferred_language = Column(String, nullable=True)

    is_active = Column(Integer, default=1)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ==========================================
# MATERIAL BATCHES
# Aggregator groups collected material
# ==========================================

class MaterialBatch(Base):
    __tablename__ = "material_batches"

    id = Column(Integer, primary_key=True, index=True)

    batch_code = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    aggregator_id = Column(
        Integer,
        ForeignKey("partners.id"),
        nullable=False,
        index=True
    )

    material_category = Column(String, nullable=False)

    total_quantity = Column(Integer, default=0)
    total_weight = Column(Float, nullable=True)

    status = Column(
        String,
        default="Preparing",
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ==========================================
# MATERIAL BATCH ITEMS
# Connects collection requests to batches
# ==========================================

class MaterialBatchItem(Base):
    __tablename__ = "material_batch_items"

    id = Column(Integer, primary_key=True, index=True)

    batch_id = Column(
        Integer,
        ForeignKey("material_batches.id"),
        nullable=False,
        index=True
    )

    request_id = Column(
        Integer,
        ForeignKey("collection_requests.id"),
        nullable=False,
        unique=True,
        index=True
    )

    quantity = Column(Integer, nullable=False)
    weight = Column(Float, nullable=True)

    added_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ==========================================
# BATCH HANDOVERS
# Aggregator transfers material to recycler
# ==========================================

class BatchHandover(Base):
    __tablename__ = "batch_handovers"

    id = Column(Integer, primary_key=True, index=True)

    batch_id = Column(
        Integer,
        ForeignKey("material_batches.id"),
        nullable=False,
        index=True
    )

    aggregator_id = Column(
        Integer,
        ForeignKey("partners.id"),
        nullable=False,
        index=True
    )

    recycler_id = Column(
        Integer,
        ForeignKey("partners.id"),
        nullable=False,
        index=True
    )

    price_offer_id = Column(
        Integer,
        ForeignKey("recycler_price_offers.id"),
        nullable=True
    )

    agreed_price_per_kg = Column(
        Numeric(10, 2),
        nullable=True
    )

    estimated_amount = Column(
        Numeric(12, 2),
        nullable=True
    )

    status = Column(
        String,
        default="Pending",
        nullable=False
    )

    dispatched_weight = Column(Float, nullable=True)
    received_weight = Column(Float, nullable=True)

    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)

    receipt_path = Column(String, nullable=True)
    remarks = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
