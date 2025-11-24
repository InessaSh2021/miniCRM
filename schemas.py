from pydantic import BaseModel
from typing import Optional

class LeadCreate(BaseModel):
    external_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class ContactResponse(BaseModel):
    contact_id: int
    lead_id: int
    operator_id: Optional[int] = None