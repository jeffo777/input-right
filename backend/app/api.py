import logging

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
from .models import businesses, leads, BusinessCreate, LeadCreate, Business, Lead

# Load environment variables
load_dotenv()

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

router = APIRouter()

# --- Public Token Endpoint ---

class TokenRequest(BaseModel):
    business_id: str
    room_name: str

@router.post("/api/token")
async def get_token(request: TokenRequest):
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(status_code=500, detail="LiveKit server credentials not configured.")
    
    # The room_name is now provided by the frontend for each unique session
    room_name = request.room_name
    participant_identity = f"visitor-{uuid.uuid4()}" # contractor_id is redundant here now

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
    "/api/internal/businesses",
    status_code=status.HTTP_201_CREATED,
    response_model=Business,
    dependencies=[Depends(security.get_api_key)]
)
async def create_business(
    business: BusinessCreate,
    database: AsyncSession = Depends(db.get_db)
):
    """Creates a new business in the database."""
    # Use .model_dump() for Pydantic v2
    query = insert(businesses).values(**business.model_dump())
    try:
        result = await database.execute(query)
        await database.commit()
    except Exception as e:
        logging.error(f"DATABASE ERROR during business creation: {e}", exc_info=True)
        await database.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error creating business.")

    # To return the full object including the server-set created_at, we fetch it back.
    select_query = select(businesses).where(businesses.c.id == result.inserted_primary_key[0])
    new_business_record = await database.execute(select_query)
    db_business = new_business_record.first()

    if not db_business:
        raise HTTPException(status_code=500, detail="Could not retrieve newly created business.")

    return dict(db_business._mapping)

@router.get(
    "/api/internal/businesses/{business_id}",
    response_model=Business,
    dependencies=[Depends(security.get_api_key)]
)
async def get_business_profile(
    business_id: str,
    database: AsyncSession = Depends(db.get_db)
):
    """Fetches business-specific data from the database."""
    query = select(businesses).where(businesses.c.id == business_id)
    result = await database.execute(query)
    db_business = result.first()

    if db_business is None:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return db_business

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
    logging.info(f"Received request to create lead: {lead.model_dump()}")
    
    # Use .model_dump() for Pydantic v2
    query = insert(leads).values(**lead.model_dump())
    
    try:
        result = await database.execute(query)
        await database.commit()
        logging.info(f"Successfully inserted lead with ID: {result.inserted_primary_key[0]}")
    except Exception as e:
        # THIS IS THE CRITICAL LOGGING WE NEED
        logging.error(f"DATABASE ERROR during lead creation: {e}", exc_info=True)
        await database.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")

    # Fetch the newly created lead to return the full object
    select_query = select(leads).where(leads.c.id == result.inserted_primary_key[0])
    new_lead_record = await database.execute(select_query)
    db_lead = new_lead_record.first()

    if not db_lead:
         raise HTTPException(status_code=500, detail="Could not retrieve newly created lead.")

    # Manually convert the SQLAlchemy Row object to a dictionary before returning
    return dict(db_lead._mapping)