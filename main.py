import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Receivable

app = FastAPI(title="DUX Receivables API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "DUX Backend Running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

# -----------------------------
# Receivables Endpoints
# -----------------------------

class ReceivableListItem(BaseModel):
    id: str
    nf_value: float
    requested_value: float
    estimated_date: Optional[str] = None
    status: str

@app.get("/api/receivables", response_model=List[ReceivableListItem])
def list_receivables(limit: int = 50):
    docs = get_documents("receivable", {}, limit)
    items: List[ReceivableListItem] = []
    for d in docs:
        est = d.get("estimated_date")
        if hasattr(est, 'isoformat'):
            est = est.isoformat()
        items.append(ReceivableListItem(
            id=str(d.get("_id")),
            nf_value=float(d.get("nf_value", 0)),
            requested_value=float(d.get("requested_value", 0)),
            estimated_date=est,
            status=d.get("status", "received")
        ))
    return items

@app.get("/api/receivables/{receivable_id}")
def get_receivable(receivable_id: str):
    try:
        from bson import ObjectId
    except Exception:
        raise HTTPException(status_code=500, detail="bson not available")
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        doc = db["receivable"].find_one({"_id": ObjectId(receivable_id)})
    except Exception:
        doc = None
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc["id"] = str(doc.pop("_id"))
    return doc

@app.post("/api/receivables")
async def create_receivable(
    # Step 1
    name: str = Form(...),
    email: str = Form(...),
    whatsapp: str = Form(...),
    cnpj: str = Form(...),
    company: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    # Step 2
    nf_number: str = Form(...),
    nf_series: Optional[str] = Form(None),
    nf_value: float = Form(...),
    nf_date: str = Form(...),
    taker_cnpj: str = Form(...),
    nf_xml: Optional[UploadFile] = File(None),
    # Step 3
    nf_pdf: Optional[UploadFile] = File(None),
    contract_pdf: Optional[UploadFile] = File(None),
    attachments: Optional[List[UploadFile]] = File(None),
    # Step 4
    requested_value: float = Form(...),
    bank: str = Form(...),
    agency: str = Form(...),
    account: str = Form(...),
    receivable_type: str = Form("duplicata"),
    notes: Optional[str] = Form(None)
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    async def safe_read(file: UploadFile) -> bytes:
        MAX = 10 * 1024 * 1024
        data = await file.read()
        if len(data) > MAX:
            raise HTTPException(status_code=413, detail=f"File {file.filename} too large")
        return data

    async def file_to_ref(f: Optional[UploadFile]) -> Optional[dict]:
        if not f:
            return None
        content = await safe_read(f)
        return {
            "filename": f.filename,
            "content_type": f.content_type,
            "size": len(content) if content else None,
            "url": None
        }

    xml_ref = await file_to_ref(nf_xml)
    pdf_ref = await file_to_ref(nf_pdf)
    contract_ref = await file_to_ref(contract_pdf)

    attach_refs: Optional[List[dict]] = None
    if attachments:
        attach_refs = []
        for a in attachments:
            attach_refs.append(await file_to_ref(a))

    payload = {
        "name": name,
        "email": email,
        "whatsapp": whatsapp,
        "cnpj": cnpj,
        "company": company,
        "role": role,
        "nf_number": nf_number,
        "nf_series": nf_series,
        "nf_value": float(nf_value),
        "nf_date": datetime.fromisoformat(nf_date).date(),
        "taker_cnpj": taker_cnpj,
        "nf_xml": xml_ref,
        "nf_pdf": pdf_ref,
        "contract_pdf": contract_ref,
        "attachments": attach_refs,
        "requested_value": float(requested_value),
        "bank": bank,
        "agency": agency,
        "account": account,
        "receivable_type": receivable_type,
        "notes": notes,
        "status": "received",
        "estimated_date": None,
    }

    try:
        receivable = Receivable(**payload)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    new_id = create_document("receivable", receivable)
    return {"id": new_id, "status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
