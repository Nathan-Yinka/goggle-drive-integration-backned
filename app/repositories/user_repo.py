import requests
from sqlalchemy.orm import Session
from app.models.user_token import UserToken
from fastapi import HTTPException
from app.config import CLIENT_ID,CLIENT_SECRET

def get_user_token(db: Session, user_id: str):
    return db.query(UserToken).filter(UserToken.user_id == user_id).first()

def get_user_by_token(db: Session, user_id: str):
    """Retrieve user authentication details by user ID."""
    return db.query(UserToken).filter(UserToken.user_id == user_id).first()

def get_user_google_token(db: Session, user_id: str):
    """
    Retrieve the user's stored Google OAuth access token.
    """
    token_entry = db.query(UserToken).filter(UserToken.user_id == user_id).first()
    return token_entry.access_token if token_entry else None

def save_user_token(db: Session, user_id: str, access_token: str, refresh_token: str = None):
    """Save or update user authentication tokens in the database."""
    user_token = db.query(UserToken).filter(UserToken.user_id == user_id).first()

    if user_token:
        user_token.access_token = access_token
        if refresh_token:
            user_token.refresh_token = refresh_token
    else:
        user_token = UserToken(user_id=user_id, access_token=access_token, refresh_token=refresh_token)
        db.add(user_token)
    
    db.commit()
    db.refresh(user_token)
    return user_token

def remove_invalid_token(db: Session, user_id: str):
    """
    Remove an invalid OAuth token from the database.
    """
    db.query(UserToken).filter(UserToken.user_id == user_id).delete()
    db.commit()

def refresh_access_token(db: Session, user_id: str):
    """
    Refresh the access token using the refresh token.
    """
    user_token = db.query(UserToken).filter(UserToken.user_id == user_id).first()

    if not user_token or not user_token.refresh_token:
        raise HTTPException(status_code=401, detail="User not authenticated or missing refresh token")
    
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": user_token.refresh_token,
        "grant_type": "refresh_token",
    }

    response = requests.post(token_url, data=payload)
    if response.status_code == 200:
        new_tokens = response.json()
        save_user_token(db, user_id, new_tokens["access_token"], user_token.refresh_token)
        return new_tokens["access_token"]
    
    else:
        remove_invalid_token(db, user_id)  # ❌ Token refresh failed, remove old token
        raise HTTPException(status_code=401, detail="Failed to refresh access token")