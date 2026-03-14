import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# We use SQLite for local development, easily replaceable with PostgreSQL for production
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./downloads/petitions.db")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if "sqlite" in DB_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Petition(Base):
    __tablename__ = "petitions"

    id = Column(Integer, primary_key=True, index=True)
    tag = Column(String, unique=True, index=True, nullable=False) # e.g. "EX29.14" or "SaveTheBikeLanes"
    title = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    signatures = relationship("Signature", back_populates="petition")

class Signature(Base):
    __tablename__ = "signatures"

    id = Column(Integer, primary_key=True, index=True)
    petition_id = Column(Integer, ForeignKey("petitions.id"), nullable=False)
    name = Column(String, nullable=False)
    postal_code = Column(String, nullable=False) # Should be validated before insertion
    signed_at = Column(DateTime, default=datetime.utcnow)

    petition = relationship("Petition", back_populates="signatures")

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
