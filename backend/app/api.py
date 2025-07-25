import os
import uuid
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from livekit import api
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert

from . import security
from . import db
from .models import contractors, leads, ContractorCreate, LeadCreate, Contractor, Lead

# Load environment variables
load_dotenv()

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

router = APIRouter()

# --- Public Token Endpoint ---

class TokenRequest(BaseModel):
    contractor_id: str

@router.post("/api/token")
async def get_token(request: TokenRequest):
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(status_code=500, detail="LiveKit server credentials not configured.")
    
    room_name = request.contractor_id
    participant_identity = f"visitor-{request.contractor_id}-{uuid.uuid4()}"

    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
        .with_identity(participant_identity) \
        .with_name("Website Visitor") \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        )).to_jwt()

    return {"token": token}

# --- Internal Secure Endpoints ---

@router.post(
    "/api/internal/contractors",
    status_code=status.HTTP_201_CREATED,
    response_model=Contractor,
    dependencies=[Depends(security.get_api_key)]
)
async def create_contractor(
    contractor: ContractorCreate,
    database: AsyncSession = Depends(db.get_db)
):
    """Creates a new contractor in the database."""
    query = insert(contractors).values(**contractor.dict())
    result = await database.execute(query)
    await database.commit()
    
    # Pydantic can't validate the result directly, so we build the response dict
    created_contractor = contractor.dict()
    created_contractor['id'] = result.inserted_primary_key[0]
    created_contractor['created_at'] = "2025-07-25T00:00:00" # Placeholder
    return created_contractor

@router.get(
    "/api/internal/contractors/{contractor_id}",
    response_model=Contractor,
    dependencies=[Depends(security.get_api_key)]
)
async def get_contractor_profile(
    contractor_id: int,
    database: AsyncSession = Depends(db.get_db)
):
    """Fetches contractor-specific data from the database."""
    query = select(contractors).where(contractors.c.id == contractor_id)
    result = await database.execute(query)
    db_contractor = result.first()

    if db_contractor is None:
        raise HTTPException(status_code=404, detail="Contractor not found")
    
    return db_contractor

@router.post(
    "/api/internal/leads",
    status_code=status.HTTP_201_CREATED,
    response_model=Lead,
    dependencies=[Depends(security.get_api_key)]
)
async def create_lead(
    lead: LeadCreate,
    database: AsyncSession = Depends(db.get_db)
):
    """Creates a new lead in the database."""
    query = insert(leads).values(**lead.dict())
    result = await database.execute(query)
    await database.commit()

    # Pydantic can't validate the result directly, so we build the response dict
    created_lead = lead.dict()
    created_lead['id'] = result.inserted_primary_key[0]
    created_lead['status'] = 'new'
    created_lead['captured_at'] = "2025-07-25T00:00:00" # Placeholder
    return created_lead