from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime


# -------------------
# MEDICINE MODEL
# -------------------
class CreateMedicine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    drug_name: str = Field(index=True)
    drug_type: str  # "tablet" or "syrup"
    nafdac_number: str = Field(index=True)
    manufacturer: str
    golden_box_image_path: str
    golden_blister_image_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

