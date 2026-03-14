import re
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from web.database import get_db, Petition, Signature

app = FastAPI(title="CivicClaw Petition Service")

# Allow Github Pages frontend to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://caellumyhl.github.io"], 
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- Pydantic Schemas for Validation ---

class PetitionCreate(BaseModel):
    tag: str = Field(..., description="Unique shorthand for the topic (e.g., EX29.14)")
    title: str = Field(..., description="Display title for the petition")
    summary: str = Field(..., description="Short explanation of the cause")

class PetitionResponse(PetitionCreate):
    id: int
    signature_count: int

    class Config:
        from_attributes = True

class SignatureCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., description="Canadian Postal Code (e.g., M5V 2H1)")

# --- Endpoints ---

@app.post("/petitions", response_model=PetitionResponse, status_code=status.HTTP_201_CREATED)
def create_petition(petition: PetitionCreate, db: Session = Depends(get_db)):
    """Creates a new petition tag securely."""
    existing = db.query(Petition).filter(Petition.tag == petition.tag).first()
    if existing:
        raise HTTPException(status_code=400, detail="Petition tag already exists.")
    
    db_petition = Petition(
        tag=petition.tag,
        title=petition.title,
        summary=petition.summary
    )
    db.add(db_petition)
    db.commit()
    db.refresh(db_petition)
    
    return {**db_petition.__dict__, "signature_count": 0}

@app.get("/petitions/{tag}", response_model=PetitionResponse)
def get_petition(tag: str, db: Session = Depends(get_db)):
    """Fetches a specific petition and its signature count."""
    db_petition = db.query(Petition).filter(Petition.tag == tag).first()
    if not db_petition:
        raise HTTPException(status_code=404, detail="Petition not found")
    
    count = db.query(Signature).filter(Signature.petition_id == db_petition.id).count()
    return {**db_petition.__dict__, "signature_count": count}

@app.post("/petitions/{tag}/sign", status_code=status.HTTP_201_CREATED)
def sign_petition(tag: str, signature: SignatureCreate, db: Session = Depends(get_db)):
    """Securely adds a signature to a petition, validating the postal code."""
    db_petition = db.query(Petition).filter(Petition.tag == tag).first()
    if not db_petition:
        raise HTTPException(status_code=404, detail="Petition not found")

    # Validate Canadian Postal Code (A1A 1A1 or A1A1A1 format)
    pc_pattern = re.compile(r"^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$")
    if not pc_pattern.match(signature.postal_code):
        raise HTTPException(status_code=400, detail="Invalid Canadian Postal Code format.")

    # Prevent duplicate signatures (simple Name + Postal combination check)
    formatted_pc = signature.postal_code.replace(" ", "").upper()
    existing_sig = db.query(Signature).filter(
        Signature.petition_id == db_petition.id,
        Signature.name.ilike(signature.name),
        Signature.postal_code == formatted_pc
    ).first()

    if existing_sig:
        raise HTTPException(status_code=400, detail="You have already signed this petition.")

    db_signature = Signature(
        petition_id=db_petition.id,
        name=signature.name,
        postal_code=formatted_pc
    )
    db.add(db_signature)
    db.commit()
    
    return {"message": "Signature recorded securely.", "petition_tag": tag}

if __name__ == "__main__":
    import uvicorn
    # Make sure to run from the `src` directory so imports work
    uvicorn.run(app, host="0.0.0.0", port=8000)
