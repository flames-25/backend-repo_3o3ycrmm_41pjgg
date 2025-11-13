"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import date, datetime

# Identity examples kept for reference
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# --------------------------------------------------
# Receivables Anticipation Module Schemas (DUX)
# --------------------------------------------------

class FileRef(BaseModel):
    filename: str
    url: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None

class Receivable(BaseModel):
    # Step 1: Basic Data
    name: str
    email: EmailStr
    whatsapp: str
    cnpj: str
    company: Optional[str] = None
    role: Optional[str] = None

    # Step 2: Invoice
    nf_number: str
    nf_series: Optional[str] = None
    nf_value: float
    nf_date: date
    taker_cnpj: str
    nf_xml: Optional[FileRef] = None

    # Step 3: Documents
    nf_pdf: Optional[FileRef] = None
    contract_pdf: Optional[FileRef] = None
    attachments: Optional[List[FileRef]] = []

    # Step 4: Financial
    requested_value: float
    bank: str
    agency: str
    account: str
    receivable_type: Literal['duplicata', 'cartao', 'boleto', 'outro'] = 'duplicata'
    notes: Optional[str] = None

    # Meta
    status: Literal['received', 'in_review', 'approved', 'rejected'] = 'received'
    estimated_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
