import datetime
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    String,
    DateTime,
    Text,
)
from pydantic import BaseModel, Field
from typing import Optional

# Synchronous Database URL for Alembic
DATABASE_URL = "postgresql+psycopg2://postgres:Theonly***4me@localhost/contractor_leads_bot_db"

metadata = MetaData()

# Contractors Table Definition
contractors = Table(
    "contractors",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("business_name", String(255), nullable=False),
    Column("contact_name", String(255)),
    Column("phone_number", String(50)),
    Column("email", String(255)),
    Column("knowledge_base", Text),
    Column("created_at", DateTime, default=datetime.datetime.utcnow),
)

# Leads Table Definition
leads = Table(
    "leads",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("contractor_id", Integer, nullable=False),
    Column("visitor_name", String(255)),
    Column("visitor_phone", String(50)),
    Column("visitor_email", String(255)),
    Column("inquiry", Text, nullable=False),
    Column("status", String(50), default="new"),
    Column("captured_at", DateTime, default=datetime.datetime.utcnow),
)

# Pydantic Models (for API data validation)
class LeadBase(BaseModel):
    visitor_name: Optional[str] = None
    visitor_phone: Optional[str] = None
    visitor_email: Optional[str] = None
    inquiry: str

class LeadCreate(LeadBase):
    contractor_id: int

class Lead(LeadBase):
    id: int
    contractor_id: int
    status: str
    captured_at: datetime.datetime

    class Config:
        from_attributes = True

class ContractorBase(BaseModel):
    business_name: str
    contact_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    knowledge_base: Optional[str] = None

class ContractorCreate(ContractorBase):
    pass

class Contractor(ContractorBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True