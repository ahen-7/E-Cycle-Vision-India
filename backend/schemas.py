
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class CollectionRequestCreate(BaseModel):
    requester_name: str = Field(min_length=2)
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

class StatusUpdate(BaseModel):
    status: str
    remarks: str = Field(min_length=3)

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
    authorization_details: str | None
    status: str
    registration_number: str | None = None
    document_filename: str | None = None
    verification_notes: str | None = None
    verified_at: datetime | None = None

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
