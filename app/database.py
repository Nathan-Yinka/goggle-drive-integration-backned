import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Session management
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base model
Base = declarative_base()
metadata = MetaData()

def get_db():
    db = SessionLocal()
    try:
        yield db  # ✅ Yields session to be used inside routes
    finally:
        db.close()  # ✅ Ensures session is closed after request