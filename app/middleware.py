from fastapi import Request, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.user_repo import get_user_by_token

async def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    Extracts user from 'User-ID' header. 
    Falls back to user_id = 1 if not provided.
    """
    user_id = request.headers.get("User-ID")  # Extract User-ID from headers

    if user_id:
        try:
            user_id = int(user_id)  # Ensure it's an integer
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid User-ID format")

    return user_id or 1  # ✅ Use extracted user_id or fallback to 1
