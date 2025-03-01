from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse, RedirectResponse
from app.database import get_db
from app.services.auth_service import generate_auth_url, handle_oauth_callback,check_google_auth_status_service,get_google_auth_token_service
from app.middleware import get_current_user
from fastapi import HTTPException

router = APIRouter()

@router.get("/auth")
async def google_auth(
    user_id: str = Depends(get_current_user),
    callback_url: str = Query(..., description="Frontend callback URL"),
    db: Session = Depends(get_db)
):
    """
    Generates a Google authentication URL with a secure OAuth state.
    The frontend must provide `callback_url` as a query parameter.
    """
    try:
        auth_url = generate_auth_url(user_id, callback_url)
        return JSONResponse(content={"authUrl": auth_url})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@router.get("/auth/callback")
async def google_auth_callback(
    code: str = Query(..., description="OAuth authorization code"),
    state: str = Query(..., description="OAuth state parameter"),
    db: Session = Depends(get_db)
):
    """
    Handles the OAuth callback and retrieves the access token.
    """
    try:
        token,redirect_url = handle_oauth_callback(code, state, db)
        redirect_url = f"http://localhost:5173/callback" if not redirect_url else redirect_url
        return RedirectResponse(redirect_url)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})


@router.get("/auth/status")
async def check_google_auth_status(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Checks if the user's stored OAuth token is valid by making a test request to Google Drive API.
    If expired, it attempts to refresh it.
    """
    is_connected = check_google_auth_status_service(db, user_id)
    return JSONResponse(content={"isConnected": is_connected})

@router.get("/auth/token")
async def get_google_auth_token(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the stored Google OAuth token if it is valid.
    If expired, it tries to refresh it first.
    """
    token = get_google_auth_token_service(db, user_id)
    
    if token:
        return JSONResponse(content={"token": token})

    raise HTTPException(status_code=401, detail="Invalid or expired Google OAuth token")