from sqlalchemy import Column, String, DateTime
from datetime import datetime
from app.database import Base

class UserToken(Base):
    __tablename__ = "user_tokens"

    user_id = Column(String(255), primary_key=True, index=True)  # ✅ Specify length
    access_token = Column(String(2048), nullable=False)  # ✅ Specify length (Longer for OAuth tokens)
    refresh_token = Column(String(2048), nullable=True)  # ✅ Optional, but still needs a length
    created_at = Column(DateTime, default=datetime.utcnow)
