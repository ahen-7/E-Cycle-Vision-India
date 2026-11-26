
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal


# ==========================================
# COLLECTION REQUESTS
# ==========================================

class CollectionRequestCreate(BaseModel):
    requester_name: str | None = None
    requester_type: str
    device_category: str
    quantity: int = Field(gt=0)
    condition: str
    state: str
    district: str
    city: str
    pincode: str = Field(pattern=r"^[1-9][0-9]{5}$")
    description: str | None = None


class CollectionRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tracking_id: str
    requester_name: str
    requester_type: str
    device_category: str
    quantity: int
    condition: str
    state: str
    district: str
    city: str
    pincode: str
    status: str
    assigned_partner: str | None = None
    assigned_collector_id: int | None = None
    collected_quantity: int | None = None
    collected_weight: float | None = None
    collected_at: datetime | None = None


# ==========================================
# PARTNERS
# ==========================================

class PartnerCreate(BaseModel):
    partner_name: str = Field(min_length=2)
    state: str
    district: str
    city: str
    pincode: str = Field(pattern=r"^[1-9][0-9]{5}$")
    accepted_categories: str
    capacity: int = Field(gt=0)


class PartnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partner_name: str
    organisation_type: str | None = None
    state: str
    district: str
    city: str
    pincode: str
    latitude: float | None = None
    longitude: float | None = None
    accepted_categories: str
    capacity: int
    is_active: int
    is_demo: int


# ==========================================
# STATUS UPDATES
# ==========================================

class StatusUpdate(BaseModel):
    status: str
    remarks: str = Field(min_length=3)


# ==========================================
# PARTNER APPLICATIONS
# ==========================================

class PartnerApplicationCreate(BaseModel):
    organisation_name: str = Field(min_length=2)
    contact_person: str = Field(min_length=2)
    phone: str = Field(min_length=10, max_length=15)
    email: str
    state: str
    district: str
    city: str
    pincode: str = Field(pattern=r"^[1-9][0-9]{5}$")
    accepted_categories: str
    capacity: int = Field(gt=0)
    organisation_type: str
    authorization_details: str | None = None
    registration_number: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class PartnerApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organisation_name: str
    contact_person: str
    phone: str
    email: str
    state: str
    district: str
    city: str
    pincode: str
    accepted_categories: str
    capacity: int
    organisation_type: str
    authorization_details: str | None = None
    status: str
    registration_number: str | None = None
    document_filename: str | None = None
    verification_notes: str | None = None
    verified_at: datetime | None = None


# ==========================================
# AUTHENTICATION
# ==========================================

class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


# ==========================================
# COLLECTORS
# ==========================================

class CollectorCreate(BaseModel):
    full_name: str = Field(min_length=2)
    phone: str = Field(min_length=10, max_length=15)
    service_area: str | None = None
    preferred_language: str | None = None


class CollectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aggregator_id: int
    full_name: str
    phone: str
    service_area: str | None = None
    preferred_language: str | None = None
    is_active: int


# ==========================================
# COLLECTOR ASSIGNMENT
# ==========================================

class CollectorAssignment(BaseModel):
    collector_id: int


# ==========================================
# COLLECTION RECORD
# ==========================================

class CollectionRecord(BaseModel):
    collected_quantity: int = Field(gt=0)
    collected_weight: float | None = Field(default=None, gt=0)
    remarks: str | None = None


# ==========================================
# MATERIAL BATCHES
# ==========================================

class MaterialBatchCreate(BaseModel):
    material_category: str = Field(min_length=2)
    request_ids: list[int] = Field(min_length=1)


class MaterialBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_code: str
    aggregator_id: int
    material_category: str
    total_quantity: int
    total_weight: float | None = None
    status: str
    created_at: datetime | None = None


# ==========================================
# BATCH HANDOVER
# ==========================================

class BatchHandoverCreate(BaseModel):
    recycler_id: int
    remarks: str | None = None
    price_offer_id: int | None = None


class BatchHandoverResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    aggregator_id: int
    recycler_id: int
    price_offer_id: int | None = None
    agreed_price_per_kg: Decimal | None = None
    estimated_amount: Decimal | None = None
    final_amount: Decimal | None = None
    payment_status: str = "Pending"
    payment_reference: str | None = None
    paid_at: datetime | None = None
    status: str
    dispatched_weight: float | None = None
    received_weight: float | None = None
    dispatched_at: datetime | None = None
    received_at: datetime | None = None
    remarks: str | None = None


class HandoverDecision(BaseModel):
    decision: str
    received_weight: float | None = Field(default=None, gt=0)
    remarks: str | None = None


class PaymentUpdate(BaseModel):
    payment_reference: str | None = None


# ==========================================
# RECYCLER PRICE OFFERS
# ==========================================

class RecyclerPriceOfferCreate(BaseModel):
    material_category: str = Field(min_length=2)
    price_per_kg: Decimal = Field(gt=0)
    minimum_quantity_kg: Decimal | None = Field(default=None, gt=0)
    valid_until: datetime | None = None


class RecyclerPriceOfferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recycler_id: int
    material_category: str
    price_per_kg: Decimal
    minimum_quantity_kg: Decimal | None = None
    valid_until: datetime | None = None
    status: str
    created_at: datetime | None = None
