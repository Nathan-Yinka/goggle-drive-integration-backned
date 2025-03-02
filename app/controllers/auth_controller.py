from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse, RedirectResponse
from app.database import get_db
from app.services.auth_service import generate_auth_url, handle_oauth_callback,check_google_auth_status_service,get_google_auth_token_service,disconnect_google_account
from app.middleware import get_current_user
from fastapi import HTTPException
from app.schemas.oauth_schema import OAuthCallbackRequest

router = APIRouter()

@router.get("/auth")
async def google_auth(
    user_id: str = Depends(get_current_user),
    callback_url: str = Query(None, description="Frontend callback URL"),
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
    code: str = Query(None, description="OAuth authorization code"),  # Allow None for error cases
    state: str = Query(None, description="OAuth state parameter"),  # Allow None for error cases
    db: Session = Depends(get_db)
):
    """
    Handles the OAuth callback, retrieves the access token, and ensures redirect even on failure.
    """
    # Default callback URL (Ensure this is the correct frontend URL)
    default_redirect_url = "http://localhost:5173/callback"

    try:
        # Ensure code and state exist
        if not code or not state:
            raise ValueError("Missing authorization code or state.")

        # Attempt to process the OAuth callback
        token, redirect_url = handle_oauth_callback(code, state, db)
        
        # Use default redirect if none is provided
        redirect_url = redirect_url or default_redirect_url
        return RedirectResponse(f"{redirect_url}?token={token}")

    except Exception as e:
        # Always redirect, but pass an error message
        error_message = str(e)
        return RedirectResponse(f"{default_redirect_url}?error={error_message}")


@router.post("/auth/callback2")
async def google_auth_callback_post(
    request: OAuthCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Handles the OAuth callback via POST request and returns a JSON response with the token or an error.
    """
    try:
        # Process OAuth token exchange
        token, _ = handle_oauth_callback(request.code, request.state, db)
        return JSONResponse(content={"token": token})

    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    

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

@router.post("/auth/disconnect")
async def disconnect_google_account_endpoint(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    API endpoint to disconnect a user's Google account.
    Calls the service to revoke access and remove stored tokens.
    """
    try:
        message = disconnect_google_account(db, user_id)
        return {"message": message}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))