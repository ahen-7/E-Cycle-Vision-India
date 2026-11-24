from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
bearer_scheme = HTTPBearer()
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from uuid import uuid4
from fastapi import UploadFile, File
from pathlib import Path
import shutil
import os
import secrets
from fastapi import Header
from datetime import datetime,timedelta,timezone
from fastapi.responses import FileResponse
import jwt
from pwdlib import PasswordHash
from database import get_db
from models import PartnerOffer
from models import CollectionRequest as DBCollectionRequest
from models import TrackingHistory, Partner, PartnerApplication,User
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
    AuthResponse
)

ADMIN_API_KEY = os.getenv("ECYCLE_ADMIN_KEY")
JWT_SECRET_KEY = os.getenv("ECYCLE_JWT_SECRET")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

password_hasher = PasswordHash.recommended()

app = FastAPI(
    title="E-Cycle Vision API",
    description="Nationwide E-Waste Collection and Traceability Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Welcome to E-Cycle Vision",
        "platform": "Nationwide E-Waste Management",
        "status": "Running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}

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

# Create a new collection request

@app.post("/requests", response_model=CollectionRequestResponse)
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

    db.add(
        TrackingHistory(
            tracking_id=tracking_id,
            status="Requested",
            remarks="Collection request submitted"
        )
    )

    db.commit()
    db.refresh(new_request)

    return new_request
# Retrieve a collection request using its tracking ID

@app.get("/requests/{tracking_id}", response_model=CollectionRequestResponse)
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

    # Only the request owner or an admin can view the details
    if (
        current_user.role != "admin"
        and request.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this collection request"
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

    # Only the owner or an admin can view tracking history
    if (
        current_user.role != "admin"
        and request.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this tracking history"
        )

    history = db.query(TrackingHistory).filter(
        TrackingHistory.tracking_id == tracking_id
    ).order_by(TrackingHistory.updated_at.asc()).all()

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
# Register a collection partner
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
        state=partner.state,
        district=partner.district,
        city=partner.city,
        pincode=partner.pincode,
        accepted_categories=partner.accepted_categories,
        capacity=partner.capacity,
        is_active=1,
        is_demo=1
    )

    db.add(new_partner)
    db.commit()
    db.refresh(new_partner)

    return new_partner

# View all collection partners
@app.get("/partners", response_model=list[PartnerResponse])
def get_partners(db: Session = Depends(get_db)):
    return db.query(Partner).filter(
        Partner.is_active == 1
    ).all()

# Recommend suitable collection partners

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
        raise HTTPException(status_code=404, detail="Request not found")

    if current_user.role not in ["admin"] and collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    partners = db.query(Partner).filter(
        Partner.is_active == 1
    ).all()

    recommendations = []

    for partner in partners:
        # Only verified organisations or clearly labelled demo partners
        if partner.verification_status != "Verified" and partner.is_demo != 1:
            continue

        if partner.state.strip().lower() != collection.state.strip().lower():
            continue

        accepted = [
            c.strip().lower()
            for c in partner.accepted_categories.split(",")
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

# Assign a collection request to a partner

@app.post("/requests/{tracking_id}/offer/{partner_id}")
def offer_request_to_partner(
    tracking_id: str,
    partner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    collection = db.query(DBCollectionRequest).filter(
        DBCollectionRequest.tracking_id == tracking_id
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Request not found")

    if collection.status not in ["Requested", "Matching"]:
        raise HTTPException(status_code=400, detail="Request is not available")

    partner = db.query(Partner).filter(
        Partner.id == partner_id,
        Partner.is_active == 1
    ).first()

    if not partner:
        raise HTTPException(status_code=404, detail="Active partner not found")

    if partner.verification_status != "Verified" and partner.is_demo != 1:
        raise HTTPException(status_code=400, detail="Partner is not verified")

    if partner.state.strip().lower() != collection.state.strip().lower():
        raise HTTPException(status_code=400, detail="Location mismatch")

    accepted = [
        c.strip().lower()
        for c in partner.accepted_categories.split(",")
    ]

    if collection.device_category.strip().lower() not in accepted:
        raise HTTPException(status_code=400, detail="Device category not accepted")

    if partner.capacity < collection.quantity:
        raise HTTPException(status_code=400, detail="Insufficient capacity")

    existing = db.query(PartnerOffer).filter(
        PartnerOffer.request_id == collection.id,
        PartnerOffer.partner_id == partner.id,
        PartnerOffer.status.in_(["Offered", "Accepted"])
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="An active offer already exists")

    offer = PartnerOffer(
        request_id=collection.id,
        partner_id=partner.id,
        status="Offered",
        matching_reasons="Suitable location, category and capacity"
    )

    db.add(offer)

    db.add(TrackingHistory(
        tracking_id=tracking_id,
        status="Offer Sent",
        remarks=f"Collection offer sent to {partner.partner_name}",
        actor_id=current_user.id,
        actor_role="admin",
        partner_id=partner.id
    ))

    db.commit()

    return {
        "message": "Offer sent successfully",
        "tracking_id": tracking_id,
        "partner_name": partner.partner_name,
        "offer_status": "Offered"
    }

# Update collection request status
@app.put("/requests/{tracking_id}/status")
def update_request_status(
    tracking_id: str,
    update: StatusUpdate,
    db: Session = Depends(get_db)
):
    request = db.query(DBCollectionRequest).filter(
        DBCollectionRequest.tracking_id == tracking_id
    ).first()

    if not request:
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

    expected_status = allowed_transitions.get(request.status)

    if update.status != expected_status:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition. Expected: {expected_status}"
        )

    request.status = update.status

    history_entry = TrackingHistory(
        tracking_id=tracking_id,
        status=update.status,
        remarks=update.remarks
    )

    db.add(history_entry)
    db.commit()
    db.refresh(request)

    return {
        "message": "Status updated successfully",
        "tracking_id": tracking_id,
        "current_status": request.status
    }

@app.post("/partner-applications", response_model=PartnerApplicationResponse)
def submit_partner_application(
    application: PartnerApplicationCreate,
    db: Session = Depends(get_db)
):
    new_application = PartnerApplication(
        organisation_name=application.organisation_name,
        contact_person=application.contact_person,
        phone=application.phone,
        email=application.email,
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
        status="Pending Verification"
    )

    db.add(new_application)
    db.commit()
    db.refresh(new_application)

    return new_application
UPLOAD_DIR = Path("uploads/partner_documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
@app.get(
    "/admin/partner-applications",
    dependencies=[Depends(verify_admin)]
)
def get_partner_applications(db: Session = Depends(get_db)):
    applications = db.query(PartnerApplication).order_by(
        PartnerApplication.created_at.desc()
    ).all()

    return applications

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
        raise HTTPException(status_code=404, detail="Application not found")

    if application.status != "Pending Verification":
        raise HTTPException(status_code=400, detail="Application already reviewed")

    if not application.document_path or not Path(application.document_path).is_file():
        raise HTTPException(
            status_code=400,
            detail="A valid supporting document is required"
        )

    if not notes or len(notes.strip()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Provide at least 20 characters of verification notes"
        )

    # Prevent duplicate login accounts
    existing_user = db.query(User).filter(
        User.email == application.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists"
        )

    # Create the organisation's partner record
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
    verification_notes=notes,
    verified_at=datetime.now(timezone.utc),
    is_active=1,
    is_demo=0,
    latitude=application.latitude,
    longitude=application.longitude,
)

    db.add(new_partner)
    db.flush()

    # Generate a unique temporary login password
    temporary_password = secrets.token_urlsafe(12)

    # Create the linked partner login
    partner_user = User(
        full_name=application.contact_person,
        email=application.email,
        password_hash=password_hasher.hash(temporary_password),
        role="partner",
        partner_id=new_partner.id,
        is_active=1
    )

    db.add(partner_user)

    application.status = "Approved"
    application.verification_notes = notes.strip()
    application.verified_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Partner application approved and account created",
        "application_id": application.id,
        "partner_id": new_partner.id,
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
        raise HTTPException(status_code=404, detail="Application not found")

    if application.status != "Pending Verification":
        raise HTTPException(status_code=400, detail="Application already reviewed")

    application.status = "Rejected"
    application.verification_notes = reason
    application.verified_at = datetime.utcnow()

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


bearer_scheme = HTTPBearer()




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

    token = create_access_token(new_user)

    return {
        "access_token": token,
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

    token = create_access_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name
    }


@app.get("/auth/me")
def get_my_account(
    current_user: User = Depends(get_current_user)
):
    return {
    "access_token": token,
    "token_type": "bearer",
    "role": user.role,
    "full_name": user.full_name,
    "partner_id": user.partner_id
}

@app.get("/partner/requests")
def get_partner_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "partner" or not current_user.partner_id:
        raise HTTPException(status_code=403, detail="Partner access required")

    offers = db.query(PartnerOffer, DBCollectionRequest).join(
        DBCollectionRequest,
        PartnerOffer.request_id == DBCollectionRequest.id
    ).filter(
        PartnerOffer.partner_id == current_user.partner_id
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


@app.post("/partner/offers/{offer_id}/respond")
def respond_to_offer(
    offer_id: int,
    decision: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "partner" or not current_user.partner_id:
        raise HTTPException(status_code=403, detail="Partner access required")

    if decision.lower() not in ["accept", "decline"]:
        raise HTTPException(status_code=400, detail="Decision must be accept or decline")

    offer = db.query(PartnerOffer).filter(
        PartnerOffer.id == offer_id,
        PartnerOffer.partner_id == current_user.partner_id
    ).first()

    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    if offer.status != "Offered":
        raise HTTPException(status_code=400, detail="Offer already responded to")

    collection = db.query(DBCollectionRequest).filter(
        DBCollectionRequest.id == offer.request_id
    ).first()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection request not found")

    partner = db.query(Partner).filter(
        Partner.id == current_user.partner_id,
        Partner.is_active == 1
    ).first()

    if not partner:
        raise HTTPException(status_code=403, detail="Partner account inactive")

    if decision.lower() == "accept":
        if collection.assigned_partner_id is not None:
            raise HTTPException(status_code=409, detail="Request already accepted by another partner")

        if partner.capacity < collection.quantity:
            raise HTTPException(status_code=400, detail="Insufficient partner capacity")

        offer.status = "Accepted"
        collection.assigned_partner_id = partner.id
        collection.assigned_partner = partner.partner_name
        collection.status = "Accepted"

        history_status = "Partner Accepted"

    else:
        offer.status = "Declined"
        history_status = "Partner Declined"

    offer.responded_at = datetime.now(timezone.utc)

    db.add(TrackingHistory(
        tracking_id=collection.tracking_id,
        status=history_status,
        remarks=f"{partner.partner_name} {decision.lower()}ed the collection offer",
        actor_id=current_user.id,
        actor_role="partner",
        partner_id=partner.id
    ))

    db.commit()

    return {
        "message": f"Offer {decision.lower()}ed successfully",
        "offer_id": offer.id,
        "offer_status": offer.status,
        "tracking_id": collection.tracking_id
    }
