
from fastapi import (
    FastAPI, Depends, HTTPException, UploadFile, File,Body,Header
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import uuid4
from pathlib import Path
from datetime import datetime, timedelta, timezone
import shutil
import os
import secrets
import jwt
from pwdlib import PasswordHash
from database import get_db
import init_db
from models import (
    CollectionRequest as DBCollectionRequest,
    TrackingHistory,
    Partner,
    PartnerApplication,
    PartnerOffer,
    User,
    Collector,
    MaterialBatch,
    MaterialBatchItem,
    BatchHandover,
    RecyclerPriceOffer
    )
from schemas import (
    CollectionRequestCreate,
    CollectionRequestResponse,
    PartnerCreate,
    PartnerResponse,
    PartnerApplicationCreate,
    PartnerApplicationResponse,
    StatusUpdate,
    UserRegister,
    UserLogin,
    AuthResponse,
    CollectorCreate,
    CollectorResponse,
    CollectorAssignment,
    CollectionRecord,
    MaterialBatchCreate,
    MaterialBatchResponse,
    BatchHandoverCreate,
    BatchHandoverResponse,
    HandoverDecision,
    RecyclerPriceOfferCreate,
    RecyclerPriceOfferResponse 
)
from dotenv import load_dotenv
load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================

ADMIN_API_KEY = os.getenv("ECYCLE_ADMIN_KEY")
JWT_SECRET_KEY = os.getenv("ECYCLE_JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer()

UPLOAD_DIR = Path("uploads/partner_documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="E-Cycle Vision API",
    description="E-Waste Collection and Traceability Platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://e-cycle-vision-india.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ==========================================
# BASIC ROUTES
# ==========================================

@app.get("/")
def home():
    return {
        "message": "Welcome to E-Cycle Vision",
        "platform": "E-Waste Collection and Traceability",
        "status": "Running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# ==========================================
# AUTHENTICATION AND ROLE HELPERS
# ==========================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        user_id = int(payload.get("sub"))

    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user = db.query(User).filter(
        User.id == user_id,
        User.is_active == 1
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Account not found or inactive"
        )

    return user


def verify_admin(
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user

def get_partner_role(partner: Partner | None):
    """
    Identify an organisation's role.
    Unknown organisation types must not receive automatic access.
    """
    if not partner:
        return None

    organisation_type = (
        partner.organisation_type or ""
    ).strip().lower()

    if "recycl" in organisation_type:
        return "recycler"

    if "refurbish" in organisation_type:
        return "recycler"

    if (
        "collection centre" in organisation_type
        or "collection center" in organisation_type
        or "collection agency" in organisation_type
        or "waste collection" in organisation_type
        or "aggregator" in organisation_type
    ):
        return "aggregator"

    return None

def get_user_partner(
    current_user: User,
    db: Session
):
    if not current_user.partner_id:
        raise HTTPException(
            status_code=403,
            detail="Organisation account is not linked to a partner"
        )

    partner = db.query(Partner).filter(
        Partner.id == current_user.partner_id,
        Partner.is_active == 1
    ).first()

    if not partner:
        raise HTTPException(
            status_code=403,
            detail="Organisation account is inactive"
        )

    return partner


def require_organisation_role(
    current_user: User,
    db: Session,
    required_role: str
):
    if current_user.role == "admin":
        raise HTTPException(
            status_code=403,
            detail="This operation requires an organisation account"
        )

    partner = get_user_partner(current_user, db)

    actual_role = (
        current_user.role
        if current_user.role in ["aggregator", "recycler"]
        else get_partner_role(partner)
    )

    if actual_role != required_role:
        raise HTTPException(
            status_code=403,
            detail=f"{required_role.capitalize()} access required"
        )

    return partner


def add_history(
    db: Session,
    tracking_id: str,
    status: str,
    remarks: str,
    user: User | None = None,
    partner_id: int | None = None
):
    db.add(
        TrackingHistory(
            tracking_id=tracking_id,
            status=status,
            remarks=remarks,
            actor_id=user.id if user else None,
            actor_role=user.role if user else None,
            partner_id=partner_id
        )
    )


def create_access_token(user: User):
    if not JWT_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="JWT secret is not configured"
        )

    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


# ==========================================
# COLLECTION REQUESTS
# ==========================================

@app.post(
    "/requests",
    response_model=CollectionRequestResponse
)
def create_request(
    request: CollectionRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "user":
        raise HTTPException(
            status_code=403,
            detail="Only registered users can submit collection requests"
        )

    tracking_id = f"ECV-{uuid4().hex[:10].upper()}"

    new_request = DBCollectionRequest(
        user_id=current_user.id,
        tracking_id=tracking_id,
        requester_name=current_user.full_name,
        requester_type=request.requester_type,
        device_category=request.device_category,
        quantity=request.quantity,
        condition=request.condition,
        state=request.state,
        district=request.district,
        city=request.city,
        pincode=request.pincode,
        description=request.description,
        status="Requested"
    )

    db.add(new_request)

    add_history(
        db,
        tracking_id,
        "Requested",
        "Collection request submitted",
        current_user
    )

    db.commit()
    db.refresh(new_request)

    return new_request


@app.get(
    "/requests/{tracking_id}",
    response_model=CollectionRequestResponse
)
def get_request(
    tracking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    request = db.query(DBCollectionRequest).filter(
        DBCollectionRequest.tracking_id == tracking_id
    ).first()

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Collection request not found"
        )

    if (
        current_user.role != "admin"
        and request.user_id != current_user.id
        and request.assigned_partner_id != current_user.partner_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this request"
        )

    return request


@app.get("/tracking/{tracking_id}")
def get_tracking_history(
    tracking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    request = db.query(DBCollectionRequest).filter(
        DBCollectionRequest.tracking_id == tracking_id
    ).first()

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Tracking ID not found"
        )

    if (
        current_user.role != "admin"
        and request.user_id != current_user.id
        and request.assigned_partner_id != current_user.partner_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this history"
        )

    history = db.query(TrackingHistory).filter(
        TrackingHistory.tracking_id == tracking_id
    ).order_by(
        TrackingHistory.updated_at.asc()
    ).all()

    return {
        "tracking_id": tracking_id,
        "current_status": request.status,
        "history": [
            {
                "status": item.status,
                "remarks": item.remarks,
                "updated_at": item.updated_at
            }
            for item in history
        ]
    }


# ==========================================
# PARTNER MANAGEMENT
# ==========================================

@app.post(
    "/partners",
    response_model=PartnerResponse,
    dependencies=[Depends(verify_admin)]
)
def create_partner(
    partner: PartnerCreate,
    db: Session = Depends(get_db)
):
    new_partner = Partner(
        partner_name=partner.partner_name,
        organisation_type="Local Collection Centre",
        state=partner.state,
        district=partner.district,
        city=partner.city,
        pincode=partner.pincode,
        accepted_categories=partner.accepted_categories,
        capacity=partner.capacity,
        verification_status="Verified",
        is_active=1,
        is_demo=1
    )

    db.add(new_partner)
    db.commit()
    db.refresh(new_partner)

    return new_partner


@app.get(
    "/partners",
    response_model=list[PartnerResponse]
)
def get_partners(db: Session = Depends(get_db)):
    return db.query(Partner).filter(
        Partner.is_active == 1
    ).all()


@app.get("/partners/recommend/{tracking_id}")
def recommend_partners(
    tracking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    collection = db.query(DBCollectionRequest).filter(
        DBCollectionRequest.tracking_id == tracking_id
    ).first()

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Request not found"
        )

    if (
        current_user.role != "admin"
        and collection.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    partners = db.query(Partner).filter(
        Partner.is_active == 1
    ).all()

    recommendations = []

    for partner in partners:

        if (
            partner.verification_status != "Verified"
            and partner.is_demo != 1
        ):
            continue

        if get_partner_role(partner) != "aggregator":
            continue

        if partner.state.strip().lower() != collection.state.strip().lower():
            continue

        accepted = [
            category.strip().lower()
            for category in partner.accepted_categories.split(",")
        ]

        if collection.device_category.strip().lower() not in accepted:
            continue

        if partner.capacity < collection.quantity:
            continue

        score = 10
        reasons = ["Same state"]

        if partner.district.strip().lower() == collection.district.strip().lower():
            score += 20
            reasons.append("District match")

        if partner.city.strip().lower() == collection.city.strip().lower():
            score += 30
            reasons.append("City match")

        if partner.pincode.strip() == collection.pincode.strip():
            score += 40
            reasons.append("Exact PIN code match")

        recommendations.append({
            "partner_id": partner.id,
            "partner_name": partner.partner_name,
            "organisation_type": partner.organisation_type,
            "verification_status": partner.verification_status,
            "city": partner.city,
            "district": partner.district,
            "capacity": partner.capacity,
            "is_demo": partner.is_demo,
            "match_score": score,
            "match_reasons": reasons
        })

    recommendations.sort(
        key=lambda item: item["match_score"],
        reverse=True
    )

    return {
        "tracking_id": tracking_id,
        "total_recommendations": len(recommendations),
        "recommendations": recommendations
    }


@app.get("/partners")
def get_all_network_partners(
    db: Session = Depends(get_db)
):
    partners = db.query(Partner).filter(
        Partner.is_active == 1
    ).all()

    return [
        {
            "id": partner.id,
            "partner_name": partner.partner_name,
            "organisation_type": partner.organisation_type,
            "state": partner.state,
            "district": partner.district,
            "city": partner.city,
            "pincode": partner.pincode,
            "latitude": partner.latitude,
            "longitude": partner.longitude,
            "accepted_categories": partner.accepted_categories,
            "capacity": partner.capacity,
            "is_active": partner.is_active,
            "is_demo": partner.is_demo,
            "verification_status": partner.verification_status,
            "partner_role": get_partner_role(partner)
        }
        for partner in partners
        if get_partner_role(partner) in ["aggregator", "recycler"]
        and (
            partner.verification_status == "Verified"
            or partner.is_demo == 1
        )
    ]

@app.get("/partners")
def get_all_network_partners(
    db: Session = Depends(get_db)
):
    partners = db.query(Partner).filter(
        Partner.is_active == 1
    ).all()

    return [
        {
            "id": partner.id,
            "partner_name": partner.partner_name,
            "organisation_type": partner.organisation_type,
            "state": partner.state,
            "district": partner.district,
            "city": partner.city,
            "pincode": partner.pincode,
            "latitude": partner.latitude,
            "longitude": partner.longitude,
            "accepted_categories": partner.accepted_categories,
            "capacity": partner.capacity,
            "is_active": partner.is_active,
            "is_demo": partner.is_demo,
            "verification_status": partner.verification_status,
            "partner_role": get_partner_role(partner)
        }
        for partner in partners
        if get_partner_role(partner) in ["aggregator", "recycler"]
        and (
            partner.verification_status == "Verified"
            or partner.is_demo == 1
        )
    ]


@app.post("/admin/setup-demo-map-locations")
def setup_demo_map_locations(
    db: Session = Depends(get_db)
):
    demo_partners = [
        {
            "partner_name": "Demo E-Waste Collection Centre",
            "organisation_type": "aggregator",
            "state": "Telangana",
            "district": "Hyderabad",
            "city": "Hyderabad",
            "pincode": "500001",
            "latitude": 17.3850,
            "longitude": 78.4867,
            "accepted_categories": "Mobile Phone, Laptop, Television",
            "capacity": 100
        },
        {
            "partner_name": "WWO Recycler - Demo",
            "organisation_type": "recycler",
            "state": "Telangana",
            "district": "Hyderabad",
            "city": "Hyderabad",
            "pincode": "500001",
            "latitude": 17.4401,
            "longitude": 78.3489,
            "accepted_categories": "Laptop, Television",
            "capacity": 100
        }
    ]

    for item in demo_partners:
        partner = db.query(Partner).filter(
            Partner.partner_name == item["partner_name"]
        ).first()

        if not partner:
            partner = Partner(**item)
            db.add(partner)
        else:
            for key, value in item.items():
                setattr(partner, key, value)

        partner.is_active = 1
        partner.is_demo = 1
        partner.verification_status = "Verified"

    db.commit()

    return {
        "message": "Demo partners created/updated",
        "total": 2
    }


# ==========================================
# ADMIN: SEND COLLECTION OFFER
# ==========================================

@app.post("/requests/{tracking_id}/offer/{partner_id}")
def offer_request_to_partner(
    tracking_id: str,
    partner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    collection = db.query(DBCollectionRequest).filter(
        DBCollectionRequest.tracking_id == tracking_id
    ).first()

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Request not found"
        )

    if collection.status not in ["Requested", "Matching"]:
        raise HTTPException(
            status_code=400,
            detail="Request is not available"
        )

    partner = db.query(Partner).filter(
        Partner.id == partner_id,
        Partner.is_active == 1
    ).first()

    if not partner:
        raise HTTPException(
            status_code=404,
            detail="Active partner not found"
        )

    if get_partner_role(partner) != "aggregator":
        raise HTTPException(
            status_code=400,
            detail="Collection offers can only be sent to aggregators"
        )

    if (
        partner.verification_status != "Verified"
        and partner.is_demo != 1
    ):
        raise HTTPException(
            status_code=400,
            detail="Partner is not verified"
        )

    if partner.state.strip().lower() != collection.state.strip().lower():
        raise HTTPException(
            status_code=400,
            detail="Location mismatch"
        )

    accepted = [
        category.strip().lower()
        for category in partner.accepted_categories.split(",")
    ]

    if collection.device_category.strip().lower() not in accepted:
        raise HTTPException(
            status_code=400,
            detail="Device category not accepted"
        )

    if partner.capacity < collection.quantity:
        raise HTTPException(
            status_code=400,
            detail="Insufficient capacity"
        )

    existing = db.query(PartnerOffer).filter(
        PartnerOffer.request_id == collection.id,
        PartnerOffer.partner_id == partner.id,
        PartnerOffer.status.in_(["Offered", "Accepted"])
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="An active offer already exists"
        )

    offer = PartnerOffer(
        request_id=collection.id,
        partner_id=partner.id,
        status="Offered",
        matching_reasons="Suitable location, category and capacity"
    )

    db.add(offer)

    add_history(
        db,
        tracking_id,
        "Offer Sent",
        f"Collection offer sent to {partner.partner_name}",
        current_user,
        partner.id
    )

    db.commit()

    return {
        "message": "Offer sent successfully",
        "tracking_id": tracking_id,
        "partner_name": partner.partner_name,
        "offer_status": "Offered"
    }


# ==========================================
# PARTNER APPLICATIONS
# ==========================================

@app.post(
    "/partner-applications",
    response_model=PartnerApplicationResponse
)
def submit_partner_application(
    application: PartnerApplicationCreate,
    db: Session = Depends(get_db)
):
    new_application = PartnerApplication(
        organisation_name=application.organisation_name,
        contact_person=application.contact_person,
        phone=application.phone,
        email=application.email.strip().lower(),
        state=application.state,
        district=application.district,
        city=application.city,
        pincode=application.pincode,
        latitude=application.latitude,
        longitude=application.longitude,
        accepted_categories=application.accepted_categories,
        capacity=application.capacity,
        organisation_type=application.organisation_type,
        authorization_details=application.authorization_details,
        registration_number=application.registration_number,
        status="Pending Verification"
    )

    db.add(new_application)
    db.commit()
    db.refresh(new_application)

    return new_application

@app.post("/partner-applications/{application_id}/upload-document")
async def upload_partner_document(
    application_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    application = db.query(PartnerApplication).filter(
        PartnerApplication.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Partner application not found"
        )

    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
    extension = Path(file.filename or "").suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, JPG, JPEG and PNG files are allowed"
        )

    if file.content_type not in {
        "application/pdf",
        "image/jpeg",
        "image/png"
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid document file type"
        )

    content = await file.read(5 * 1024 * 1024 + 1)

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size must not exceed 5 MB"
        )

    saved_filename = (
        f"application_{application_id}_{uuid4().hex}{extension}"
    )

    file_path = UPLOAD_DIR / saved_filename
    file_path.write_bytes(content)

    application.document_filename = file.filename
    application.document_path = str(file_path)

    db.commit()

    return {
        "message": "Document uploaded successfully",
        "application_id": application_id,
        "document_filename": file.filename,
        "status": application.status
    }


# ==========================================
# ADMIN: VERIFY ORGANISATIONS
# ==========================================

@app.get(
    "/admin/partner-applications",
    dependencies=[Depends(verify_admin)]
)
def get_partner_applications(
    db: Session = Depends(get_db)
):
    return db.query(PartnerApplication).order_by(
        PartnerApplication.created_at.desc()
    ).all()


@app.post(
    "/admin/partner-applications/{application_id}/approve",
    dependencies=[Depends(verify_admin)]
)

@app.post(
    "/admin/partner-applications/{application_id}/approve",
    dependencies=[Depends(verify_admin)]
)
def approve_partner_application(
    application_id: int,
    notes: str,
    db: Session = Depends(get_db)
):
    application = db.query(PartnerApplication).filter(
        PartnerApplication.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    if application.status != "Pending Verification":
        raise HTTPException(
            status_code=400,
            detail="Application already reviewed"
        )

    if (
        not application.document_path
        or not Path(application.document_path).is_file()
    ):
        raise HTTPException(
            status_code=400,
            detail="A valid supporting document is required"
        )

    if not notes or len(notes.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Provide at least 20 characters of verification notes"
        )

    existing_user = db.query(User).filter(
        User.email == application.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists"
        )

    new_partner = Partner(
        partner_name=application.organisation_name,
        organisation_type=application.organisation_type,
        state=application.state,
        district=application.district,
        city=application.city,
        pincode=application.pincode,
        accepted_categories=application.accepted_categories,
        capacity=application.capacity,
        verification_status="Verified",
        registration_number=application.registration_number,
        authorization_details=application.authorization_details,
        verification_notes=notes.strip(),
        verified_at=datetime.now(timezone.utc),
        is_active=1,
        is_demo=0,
        latitude=application.latitude,
        longitude=application.longitude
    )

    organisation_role = get_partner_role(new_partner)

    if organisation_role is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Organisation type is unclear. "
                "Verify and classify it as an aggregator or recycler "
                "before approval."
            )
        )

    db.add(new_partner)
    db.flush()

    temporary_password = secrets.token_urlsafe(12)

    partner_user = User(
        full_name=application.contact_person,
        email=application.email,
        password_hash=password_hasher.hash(temporary_password),
        role=organisation_role,
        partner_id=new_partner.id,
        is_active=1
    )

    db.add(partner_user)

    application.status = "Approved"
    application.verification_notes = notes.strip()
    application.verified_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "message": "Organisation application approved and account created",
        "application_id": application.id,
        "partner_id": new_partner.id,
        "organisation_role": organisation_role,
        "email": partner_user.email,
        "temporary_password": temporary_password
    }

@app.post(
    "/admin/partner-applications/{application_id}/regenerate-credentials",
    dependencies=[Depends(verify_admin)]
)
def regenerate_organisation_credentials(
    application_id: int,
    db: Session = Depends(get_db)
):
    application = db.query(PartnerApplication).filter(
        PartnerApplication.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    if application.status != "Approved":
        raise HTTPException(
            status_code=400,
            detail="Only approved organisations can receive login credentials"
        )

    partner_user = db.query(User).filter(
        User.email == application.email.strip().lower()
    ).first()

    if not partner_user or not partner_user.partner_id:
        raise HTTPException(
            status_code=404,
            detail="Organisation account not found"
        )

    if partner_user.role not in ["aggregator", "recycler"]:
        raise HTTPException(
            status_code=400,
            detail="This account is not an organisation account"
        )

    temporary_password = secrets.token_urlsafe(12)

    partner_user.password_hash = password_hasher.hash(
        temporary_password
    )

    db.commit()

    return {
        "message": "Organisation credentials regenerated successfully",
        "application_id": application.id,
        "partner_id": partner_user.partner_id,
        "organisation_role": partner_user.role,
        "email": partner_user.email,
        "temporary_password": temporary_password
    }

@app.post(
    "/admin/partner-applications/{application_id}/reject",
    dependencies=[Depends(verify_admin)]
)
def reject_partner_application(
    application_id: int,
    reason: str,
    db: Session = Depends(get_db)
):
    application = db.query(PartnerApplication).filter(
        PartnerApplication.id == application_id
    ).first()

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    if application.status != "Pending Verification":
        raise HTTPException(
            status_code=400,
            detail="Application already reviewed"
        )

    application.status = "Rejected"
    application.verification_notes = reason
    application.verified_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "message": "Application rejected",
        "application_id": application.id,
        "status": application.status,
        "reason": reason
    }


@app.get(
    "/admin/partner-applications/{application_id}/document",
    dependencies=[Depends(verify_admin)]
)
def view_partner_document(
    application_id: int,
    db: Session = Depends(get_db)
):
    application = db.query(PartnerApplication).filter(
        PartnerApplication.id == application_id
    ).first()

    if not application or not application.document_path:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    path = Path(application.document_path)

    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document file is missing"
        )

    return FileResponse(
        path,
        filename=application.document_filename
    )


# ==========================================
# USER REGISTRATION AND LOGIN
# ==========================================

@app.post("/auth/register", response_model=AuthResponse)
def register_user(
    data: UserRegister,
    db: Session = Depends(get_db)
):
    email = data.email.strip().lower()

    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(
            status_code=400,
            detail="Enter a valid email address"
        )

    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists"
        )

    new_user = User(
        full_name=data.full_name.strip(),
        email=email,
        password_hash=password_hasher.hash(data.password),
        role="user",
        is_active=1
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "access_token": create_access_token(new_user),
        "token_type": "bearer",
        "role": new_user.role,
        "full_name": new_user.full_name
    }


@app.post("/auth/login", response_model=AuthResponse)
def login_user(
    data: UserLogin,
    db: Session = Depends(get_db)
):
    email = data.email.strip().lower()

    user = db.query(User).filter(
        User.email == email
    ).first()

    if not user or not password_hasher.verify(
        data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    if user.is_active != 1:
        raise HTTPException(
            status_code=403,
            detail="Your account is inactive"
        )

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name
    }


@app.get("/auth/me")
def get_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role,
        "partner_id": current_user.partner_id
    }


# ==========================================
# AGGREGATOR: COLLECTION REQUESTS
# ==========================================

@app.get("/aggregator/requests")
def get_aggregator_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = require_organisation_role(
        current_user,
        db,
        "aggregator"
    )

    offers = db.query(
        PartnerOffer,
        DBCollectionRequest
    ).join(
        DBCollectionRequest,
        PartnerOffer.request_id == DBCollectionRequest.id
    ).filter(
        PartnerOffer.partner_id == partner.id
    ).order_by(
        PartnerOffer.offered_at.desc()
    ).all()

    results = []

    for offer, collection in offers:
        results.append({
            "id": collection.id,
            "offer_id": offer.id,
            "tracking_id": collection.tracking_id,
            "requester_name": collection.requester_name,
            "device_category": collection.device_category,
            "quantity": collection.quantity,
            "condition": collection.condition,
            "state": collection.state,
            "district": collection.district,
            "city": collection.city,
            "pincode": collection.pincode,
            "status": collection.status,
            "offer_status": offer.status,
            "assigned_collector_id": collection.assigned_collector_id,
            "collected_quantity": collection.collected_quantity,
            "collected_weight": collection.collected_weight,
            "created_at": collection.created_at
        })

    return {
        "total_requests": len(results),
        "requests": results
    }


# Keep the old partner endpoint working for existing frontend versions.
@app.get("/partner/requests")
def get_legacy_partner_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = require_organisation_role(
        current_user,
        db,
        "aggregator"
    )

    offers = db.query(
        PartnerOffer,
        DBCollectionRequest
    ).join(
        DBCollectionRequest,
        PartnerOffer.request_id == DBCollectionRequest.id
    ).filter(
        PartnerOffer.partner_id == partner.id
    ).order_by(
        PartnerOffer.offered_at.desc()
    ).all()

    results = []

    for offer, collection in offers:
        results.append({
            "id": collection.id,
            "offer_id": offer.id,
            "tracking_id": collection.tracking_id,
            "requester_name": collection.requester_name,
            "device_category": collection.device_category,
            "quantity": collection.quantity,
            "condition": collection.condition,
            "state": collection.state,
            "district": collection.district,
            "city": collection.city,
            "pincode": collection.pincode,
            "status": collection.status,
            "offer_status": offer.status,
            "created_at": collection.created_at
        })

    return {
        "total_requests": len(results),
        "requests": results
    }


@app.post("/aggregator/offers/{offer_id}/respond")
def aggregator_respond_to_offer(
    offer_id: int,
    decision: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = require_organisation_role(
        current_user,
        db,
        "aggregator"
    )

    decision = decision.lower().strip()

    if decision not in ["accept", "decline"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be accept or decline"
        )

    offer = db.query(PartnerOffer).filter(
        PartnerOffer.id == offer_id,
        PartnerOffer.partner_id == partner.id
    ).first()

    if not offer:
        raise HTTPException(
            status_code=404,
            detail="Offer not found"
        )

    if offer.status != "Offered":
        raise HTTPException(
            status_code=400,
            detail="Offer already responded to"
        )

    collection = db.query(DBCollectionRequest).filter(
        DBCollectionRequest.id == offer.request_id
    ).first()

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Collection request not found"
        )

    if decision == "accept":

        if collection.assigned_partner_id is not None:
            raise HTTPException(
                status_code=409,
                detail="Request already assigned to another partner"
            )

        if partner.capacity < collection.quantity:
            raise HTTPException(
                status_code=400,
                detail="Insufficient partner capacity"
            )

        offer.status = "Accepted"

        collection.assigned_partner_id = partner.id
        collection.assigned_partner = partner.partner_name
        collection.status = "Accepted"

        history_status = "Aggregator Accepted"

    else:
        offer.status = "Declined"
        history_status = "Aggregator Declined"

    offer.responded_at = datetime.now(timezone.utc)

    add_history(
        db,
        collection.tracking_id,
        history_status,
        f"{partner.partner_name} {decision}ed the collection offer",
        current_user,
        partner.id
    )

    db.commit()

    return {
        "message": f"Offer {decision}ed successfully",
        "offer_id": offer.id,
        "offer_status": offer.status,
        "tracking_id": collection.tracking_id
    }


# Legacy endpoint retained for existing partner frontend.
@app.post("/partner/offers/{offer_id}/respond")
def legacy_partner_respond(
    offer_id: int,
    decision: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return aggregator_respond_to_offer(
        offer_id,
        decision,
        db,
        current_user
    )


# ==========================================
# AGGREGATOR: COLLECTOR MANAGEMENT
# ==========================================

@app.post(
    "/aggregator/collectors",
    response_model=CollectorResponse
)
def create_collector(
    data: CollectorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = require_organisation_role(
        current_user,
        db,
        "aggregator"
    )

    collector = Collector(
        aggregator_id=partner.id,
        full_name=data.full_name.strip(),
        phone=data.phone.strip(),
        service_area=data.service_area,
        preferred_language=data.preferred_language,
        is_active=1
    )

    db.add(collector)
    db.commit()
    db.refresh(collector)

    return collector


@app.get(
    "/aggregator/collectors",
    response_model=list[CollectorResponse]
)
def get_collectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = require_organisation_role(
        current_user,
        db,
        "aggregator"
    )

    return db.query(Collector).filter(
        Collector.aggregator_id == partner.id
    ).order_by(
        Collector.created_at.desc()
    ).all()


@app.put("/aggregator/requests/{tracking_id}/assign-collector")
def assign_collector(
    tracking_id: str,
    assignment: CollectorAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = require_organisation_role(
        current_user,
        db,
        "aggregator"
    )

    collection = db.query(DBCollectionRequest).filter(
        DBCollectionRequest.tracking_id == tracking_id,
        DBCollectionRequest.assigned_partner_id == partner.id
    ).first()

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Assigned collection request not found"
        )

    if collection.status not in ["Accepted", "Assigned"]:
        raise HTTPException(
            status_code=400,
            detail="Request is not ready for collector assignment"
        )

    collector = db.query(Collector).filter(
        Collector.id == assignment.collector_id,
        Collector.aggregator_id == partner.id,
        Collector.is_active == 1
    ).first()

    if not collector:
        raise HTTPException(
            status_code=404,
            detail="Active collector not found under your organisation"
        )

    collection.assigned_collector_id = collector.id
    collection.status = "Scheduled"

    add_history(
        db,
        tracking_id,
        "Scheduled",
        f"Pickup assigned to collector {collector.full_name}",
        current_user,
        partner.id
    )

    db.commit()

    return {
        "message": "Collector assigned successfully",
        "tracking_id": tracking_id,
        "collector_id": collector.id,
        "collector_name": collector.full_name,
        "status": collection.status
    }


# ==========================================
# AGGREGATOR: RECORD PHYSICAL COLLECTION
# ==========================================

@app.post("/aggregator/requests/{tracking_id}/record-pickup")
def record_pickup(
    tracking_id: str,
    record: CollectionRecord,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = require_organisation_role(
        current_user,
        db,
        "aggregator"
    )

    collection = db.query(DBCollectionRequest).filter(
        DBCollectionRequest.tracking_id == tracking_id,
        DBCollectionRequest.assigned_partner_id == partner.id
    ).first()

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Collection request not found"
        )

    if collection.status != "Scheduled":
        raise HTTPException(
            status_code=400,
            detail="A scheduled pickup is required before recording collection"
        )

    if not collection.assigned_collector_id:
        raise HTTPException(
            status_code=400,
            detail="Assign a collector before recording pickup"
        )

    collector = db.query(Collector).filter(
        Collector.id == collection.assigned_collector_id,
        Collector.aggregator_id == partner.id
    ).first()

    if not collector:
        raise HTTPException(
            status_code=400,
            detail="Assigned collector record is unavailable"
        )

    collection.collected_quantity = record.collected_quantity
    collection.collected_weight = record.collected_weight
    collection.collected_at = datetime.now(timezone.utc)
    collection.status = "Collected"

    remarks = (
        f"Pickup recorded by aggregator. "
        f"Collector: {collector.full_name}. "
        f"Actual quantity: {record.collected_quantity}."
    )

    if record.collected_weight is not None:
        remarks += f" Actual weight: {record.collected_weight} kg."

    if record.remarks:
        remarks += f" Notes: {record.remarks}"

    add_history(
        db,
        tracking_id,
        "Collected",
        remarks,
        current_user,
        partner.id
    )

    db.commit()

    return {
        "message": "Collection recorded successfully",
        "tracking_id": tracking_id,
        "collected_quantity": collection.collected_quantity,
        "collected_weight": collection.collected_weight,
        "status": collection.status
    }


# ==========================================
# AGGREGATOR: MATERIAL BATCHES
# ==========================================

@app.post(
    "/aggregator/batches",
    response_model=MaterialBatchResponse
)
def create_material_batch(
    data: MaterialBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = require_organisation_role(
        current_user,
        db,
        "aggregator"
    )

    if len(set(data.request_ids)) != len(data.request_ids):
        raise HTTPException(
            status_code=400,
            detail="Duplicate request IDs are not allowed"
        )

    collections = db.query(DBCollectionRequest).filter(
        DBCollectionRequest.id.in_(data.request_ids),
        DBCollectionRequest.assigned_partner_id == partner.id,
        DBCollectionRequest.status == "Collected"
    ).all()

    if len(collections) != len(data.request_ids):
        raise HTTPException(
            status_code=400,
            detail="Every request must belong to your organisation and be collected"
        )

    existing_items = db.query(MaterialBatchItem).filter(
        MaterialBatchItem.request_id.in_(data.request_ids)
    ).first()

    if existing_items:
        raise HTTPException(
            status_code=409,
            detail="One or more requests already belong to a material batch"
        )

    for collection in collections:
        if (
            collection.device_category.strip().lower()
            != data.material_category.strip().lower()
        ):
            raise HTTPException(
                status_code=400,
                detail="All requests in a batch must have the selected material category"
            )

    total_quantity = sum(
        collection.collected_quantity or collection.quantity
        for collection in collections
    )

    weights = [
        collection.collected_weight
        for collection in collections
        if collection.collected_weight is not None
    ]

    total_weight = sum(weights) if weights else None

    batch = MaterialBatch(
        batch_code=f"ECVB-{uuid4().hex[:10].upper()}",
        aggregator_id=partner.id,
        material_category=data.material_category,
        total_quantity=total_quantity,
        total_weight=total_weight,
        status="Preparing"
    )

    db.add(batch)
    db.flush()

    for collection in collections:
        db.add(
            MaterialBatchItem(
                batch_id=batch.id,
                request_id=collection.id,
                quantity=collection.collected_quantity or collection.quantity,
                weight=collection.collected_weight
            )
        )

        add_history(
            db,
            collection.tracking_id,
            "Batched",
            f"Material added to batch {batch.batch_code}",
            current_user,
            partner.id
        )

    db.commit()
    db.refresh(batch)

    return batch


@app.get(
    "/aggregator/batches",
    response_model=list[MaterialBatchResponse]
)
def get_aggregator_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = require_organisation_role(
        current_user,
        db,
        "aggregator"
    )

    return db.query(MaterialBatch).filter(
        MaterialBatch.aggregator_id == partner.id
    ).order_by(
        MaterialBatch.created_at.desc()
    ).all()


# ==========================================
# AGGREGATOR: HANDOVER TO RECYCLER
# ==========================================

@app.post(
    "/aggregator/batches/{batch_id}/handover",
    response_model=BatchHandoverResponse
)

@app.post(
    "/aggregator/batches/{batch_id}/handover",
    response_model=BatchHandoverResponse
)
def create_batch_handover(
    batch_id: int,
    data: BatchHandoverCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = require_organisation_role(
        current_user,
        db,
        "aggregator"
    )

    batch = db.query(MaterialBatch).filter(
        MaterialBatch.id == batch_id,
        MaterialBatch.aggregator_id == partner.id
    ).first()

    if not batch:
        raise HTTPException(
            status_code=404,
            detail="Material batch not found"
        )

    if batch.status not in ["Preparing", "Ready"]:
        raise HTTPException(
            status_code=400,
            detail="This batch is not available for handover"
        )

    recycler = db.query(Partner).filter(
        Partner.id == data.recycler_id,
        Partner.is_active == 1,
        Partner.verification_status == "Verified"
    ).first()

    if not recycler or get_partner_role(recycler) != "recycler":
        raise HTTPException(
            status_code=404,
            detail="Verified recycler not found"
        )

    accepted = [
        category.strip().lower()
        for category in recycler.accepted_categories.split(",")
    ]

    if batch.material_category.strip().lower() not in accepted:
        raise HTTPException(
            status_code=400,
            detail="Recycler does not list this material category"
        )

    selected_offer = None

    if data.price_offer_id is not None:
        selected_offer = db.query(RecyclerPriceOffer).filter(
            RecyclerPriceOffer.id == data.price_offer_id,
            RecyclerPriceOffer.recycler_id == recycler.id,
            RecyclerPriceOffer.status == "Active"
        ).first()

        if not selected_offer:
            raise HTTPException(
                status_code=404,
                detail="Selected recycler price offer not found or inactive"
            )

        if (
            selected_offer.material_category.strip().lower()
            != batch.material_category.strip().lower()
        ):
            raise HTTPException(
                status_code=400,
                detail="Selected offer does not match the batch category"
            )

        if selected_offer.valid_until:
            expiry = selected_offer.valid_until

            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            if expiry <= datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=400,
                    detail="Selected price offer has expired"
                )

        if batch.total_weight is None or batch.total_weight <= 0:
            raise HTTPException(
                status_code=400,
                detail="Record the batch weight before selecting a price offer"
            )

        if (
            selected_offer.minimum_quantity_kg is not None
            and float(batch.total_weight)
            < float(selected_offer.minimum_quantity_kg)
        ):
            raise HTTPException(
                status_code=400,
                detail="Batch weight is below the offer's minimum quantity"
            )

    agreed_price = (
        selected_offer.price_per_kg
        if selected_offer else None
    )

    estimated_amount = (
        round(
            float(batch.total_weight) * float(agreed_price),
            2
        )
        if agreed_price is not None else None
    )

    existing = db.query(BatchHandover).filter(
        BatchHandover.batch_id == batch.id,
        BatchHandover.status.in_(["Dispatched", "Received"])
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="This batch already has an active or completed handover"
        )

    handover = BatchHandover(
        batch_id=batch.id,
        aggregator_id=partner.id,
        recycler_id=recycler.id,
        price_offer_id=(
            selected_offer.id if selected_offer else None
        ),
        agreed_price_per_kg=agreed_price,
        estimated_amount=estimated_amount,
        status="Dispatched",
        dispatched_weight=batch.total_weight,
        dispatched_at=datetime.now(timezone.utc),
        remarks=data.remarks
    )

    batch.status = "Dispatched"

    db.add(handover)
    db.commit()
    db.refresh(handover)

    return handover

# ==========================================
# RECYCLER: PRICE OFFERS
# ==========================================

@app.post(
    "/recycler/price-offers",
    response_model=RecyclerPriceOfferResponse
)
def create_recycler_price_offer(
    data: RecyclerPriceOfferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recycler = require_organisation_role(
        current_user,
        db,
        "recycler"
    )

    if recycler.verification_status != "Verified":
        raise HTTPException(
            status_code=403,
            detail="Only verified recyclers can publish price offers"
        )

    accepted = [
        category.strip().lower()
        for category in recycler.accepted_categories.split(",")
    ]

    if data.material_category.strip().lower() not in accepted:
        raise HTTPException(
            status_code=400,
            detail="You do not accept this material category"
        )

    if data.valid_until:
        expiry = data.valid_until

        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if expiry <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400,
                detail="Offer validity must be in the future"
            )

    price_offer = RecyclerPriceOffer(
        recycler_id=recycler.id,
        material_category=data.material_category.strip(),
        price_per_kg=data.price_per_kg,
        minimum_quantity_kg=data.minimum_quantity_kg,
        valid_until=data.valid_until,
        status="Active"
    )

    db.add(price_offer)
    db.commit()
    db.refresh(price_offer)

    return price_offer


@app.get(
    "/recycler/price-offers",
    response_model=list[RecyclerPriceOfferResponse]
)
def get_recycler_price_offers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recycler = require_organisation_role(
        current_user,
        db,
        "recycler"
    )

    return db.query(RecyclerPriceOffer).filter(
        RecyclerPriceOffer.recycler_id == recycler.id
    ).order_by(
        RecyclerPriceOffer.created_at.desc()
    ).all()


@app.get("/aggregator/batches/{batch_id}/price-offers")
def get_batch_price_offers(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    aggregator = require_organisation_role(
        current_user,
        db,
        "aggregator"
    )

    batch = db.query(MaterialBatch).filter(
        MaterialBatch.id == batch_id,
        MaterialBatch.aggregator_id == aggregator.id
    ).first()

    if not batch:
        raise HTTPException(
            status_code=404,
            detail="Material batch not found"
        )

    if batch.total_weight is None or batch.total_weight <= 0:
        raise HTTPException(
            status_code=400,
            detail="Record the batch weight before comparing price offers"
        )

    now = datetime.now(timezone.utc)

    offers = db.query(
        RecyclerPriceOffer,
        Partner
    ).join(
        Partner,
        RecyclerPriceOffer.recycler_id == Partner.id
    ).filter(
        RecyclerPriceOffer.status == "Active",
        Partner.is_active == 1,
        Partner.verification_status == "Verified",
        RecyclerPriceOffer.material_category.ilike(
            batch.material_category.strip()
        )
    ).all()

    results = []

    for offer, recycler in offers:

        if get_partner_role(recycler) != "recycler":
            continue

        if offer.valid_until:
            expiry = offer.valid_until

            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            if expiry <= now:
                continue

        if (
            offer.minimum_quantity_kg is not None
            and batch.total_weight < float(offer.minimum_quantity_kg)
        ):
            continue

        estimated_value = (
            float(batch.total_weight) * float(offer.price_per_kg)
        )

        results.append({
            "offer_id": offer.id,
            "recycler_id": recycler.id,
            "recycler_name": recycler.partner_name,
            "city": recycler.city,
            "material_category": offer.material_category,
            "price_per_kg": float(offer.price_per_kg),
            "minimum_quantity_kg": (
                float(offer.minimum_quantity_kg)
                if offer.minimum_quantity_kg is not None
                else None
            ),
            "batch_weight_kg": float(batch.total_weight),
            "estimated_value": round(estimated_value, 2),
            "valid_until": offer.valid_until
        })

    results.sort(
        key=lambda item: item["price_per_kg"],
        reverse=True
    )

    return {
        "batch_id": batch.id,
        "batch_code": batch.batch_code,
        "material_category": batch.material_category,
        "total_weight_kg": float(batch.total_weight),
        "total_offers": len(results),
        "offers": results
    }
# ==========================================
# RECYCLER: INCOMING HANDOVERS
# ==========================================

@app.get(
    "/recycler/handovers",
    response_model=list[BatchHandoverResponse]
)
def get_recycler_handovers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = require_organisation_role(
        current_user,
        db,
        "recycler"
    )

    return db.query(BatchHandover).filter(
        BatchHandover.recycler_id == partner.id
    ).order_by(
        BatchHandover.created_at.desc()
    ).all()


@app.post("/recycler/handovers/{handover_id}/respond")
def respond_to_handover(
    handover_id: int,
    decision: HandoverDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    partner = require_organisation_role(
        current_user,
        db,
        "recycler"
    )

    action = decision.decision.strip().lower()

    if action not in ["accept", "reject"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be accept or reject"
        )

    handover = db.query(BatchHandover).filter(
        BatchHandover.id == handover_id,
        BatchHandover.recycler_id == partner.id
    ).first()

    if not handover:
        raise HTTPException(
            status_code=404,
            detail="Handover not found"
        )

    if handover.status != "Dispatched":
        raise HTTPException(
            status_code=400,
            detail="This handover has already been processed"
        )

    batch = db.query(MaterialBatch).filter(
        MaterialBatch.id == handover.batch_id
    ).first()

    if action == "accept":

        if decision.received_weight is None:
            raise HTTPException(
                status_code=400,
                detail="Enter the actual received weight"
            )

        handover.status = "Received"
        handover.received_weight = decision.received_weight
        handover.received_at = datetime.now(timezone.utc)

        if decision.remarks:
            handover.remarks = decision.remarks

        if batch:
            batch.status = "Received"

        items = db.query(MaterialBatchItem).filter(
            MaterialBatchItem.batch_id == handover.batch_id
        ).all()

        for item in items:
            collection = db.query(DBCollectionRequest).filter(
                DBCollectionRequest.id == item.request_id
            ).first()

            if collection:
                collection.status = "Received"

                add_history(
                    db,
                    collection.tracking_id,
                    "Received",
                    (
                        f"Recycler {partner.partner_name} confirmed "
                        f"receipt through batch {batch.batch_code if batch else handover.batch_id}. "
                        f"Received weight: {decision.received_weight} kg."
                    ),
                    current_user,
                    partner.id
                )

    else:
        handover.status = "Rejected"

        if decision.remarks:
            handover.remarks = decision.remarks

        if batch:
            batch.status = "Preparing"

    db.commit()

    return {
        "message": f"Handover {action}ed successfully",
        "handover_id": handover.id,
        "status": handover.status
    }


# ==========================================
# ADMIN: VIEW BATCHES AND HANDOVERS
# ==========================================

@app.get(
    "/admin/batches",
    dependencies=[Depends(verify_admin)]
)
def admin_get_batches(
    db: Session = Depends(get_db)
):
    return db.query(MaterialBatch).order_by(
        MaterialBatch.created_at.desc()
    ).all()


@app.get(
    "/admin/handovers",
    dependencies=[Depends(verify_admin)]
)
def admin_get_handovers(
    db: Session = Depends(get_db)
):
    return db.query(BatchHandover).order_by(
        BatchHandover.created_at.desc()
    ).all()


# ==========================================
# RESTRICTED STATUS UPDATE
# ==========================================

@app.put("/requests/{tracking_id}/status")
def update_request_status(
    tracking_id: str,
    update: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can use this status endpoint"
        )

    collection = db.query(DBCollectionRequest).filter(
        DBCollectionRequest.tracking_id == tracking_id
    ).first()

    if not collection:
        raise HTTPException(
            status_code=404,
            detail="Collection request not found"
        )

    allowed_transitions = {
        "Requested": "Assigned",
        "Assigned": "Scheduled",
        "Scheduled": "Collected",
        "Collected": "Received"
    }

    expected_status = allowed_transitions.get(collection.status)

    if update.status != expected_status:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition. Expected: {expected_status}"
        )

    collection.status = update.status

    add_history(
        db,
        tracking_id,
        update.status,
        update.remarks,
        current_user
    )

    db.commit()

    return {
        "message": "Status updated successfully",
        "tracking_id": tracking_id,
        "current_status": collection.status
    }

@app.post("/admin/setup-admin-once")
def setup_admin_once(
    data: dict = Body(...),
    x_admin_key: str = Header(...),
    db: Session = Depends(get_db)
):
    if not ADMIN_API_KEY or not secrets.compare_digest(
        x_admin_key, ADMIN_API_KEY
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid admin setup key"
        )

    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    full_name = str(data.get("full_name", "E-Cycle Admin")).strip()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")

    if len(password) < 10:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 10 characters"
        )

    user = db.query(User).filter(User.email == email).first()

    if user:
        user.role = "admin"
        user.is_active = 1
        user.password_hash = password_hasher.hash(password)
    else:
        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hasher.hash(password),
            role="admin",
            is_active=1
        )
        db.add(user)

    db.commit()

    return {
        "message": "Admin account created successfully",
        "email": email,
        "role": "admin"
    }
