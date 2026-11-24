
from sqlalchemy import Column, Integer, String, DateTime,Text,ForeignKey, Float
from sqlalchemy.sql import func
from database import Base


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

    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())



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

    updated_at = Column(DateTime(timezone=True), server_default=func.now())

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

    status = Column(String, default="Pending Verification")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    registration_number = Column(String, nullable=True)
    document_filename = Column(String, nullable=True)
    document_path = Column(String, nullable=True)
    verification_notes = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

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

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    role = Column(String, default="user", nullable=False)

    partner_id = Column(Integer, nullable=True)

    is_active = Column(Integer, default=1)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
  