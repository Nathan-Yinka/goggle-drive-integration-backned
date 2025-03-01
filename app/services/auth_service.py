import uuid
import base64
import json
import logging
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session
import requests
from fastapi import HTTPException
from app.repositories.user_repo import save_user_token,get_user_google_token,refresh_access_token,remove_invalid_token
from app.repositories.state_repo import save_state, get_user_id_by_state, delete_state
from app.config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SCOPES

logger = logging.getLogger(__name__)

GOOGLE_DRIVE_API_TEST_URL = "https://www.googleapis.com/drive/v3/about?fields=user"

def generate_auth_url(user_id: str, callback_url: str) -> str:
    """
    Generates an OAuth URL with a secure state token that includes the callback URL.
    """
    try:
        # Generate a unique state ID
        state = str(uuid.uuid4())

        # Create a state object that includes the callback URL
        state_data = {"state": state, "user_id": user_id, "callback_url": callback_url}
        encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

        # Store the raw `state` and its `encoded_state`
        save_state(state, encoded_state)  # Save both state and encoded state

        # Create Google OAuth Flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "redirect_uris": [REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=SCOPES,
        )
        flow.redirect_uri = REDIRECT_URI

        # Pass only the raw `state` in the URL
        auth_url, _ = flow.authorization_url(
            prompt="consent",
            state=state,  # Send only the raw state
            access_type="offline"
        )

        return auth_url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate authentication URL: {str(e)}")

def handle_oauth_callback(code: str, state: str, db: Session):
    """
    Handles OAuth callback, validates the state, retrieves user info, and stores the access token.
    """
    # Retrieve the encoded state from storage
    encoded_state = get_user_id_by_state(state)
    if not encoded_state:
        logger.warning(f"Invalid or expired OAuth state: {state}")
        raise HTTPException(status_code=400, detail="Invalid or expired authentication state.")

    try:
        # Decode the state to extract user_id and callback_url
        decoded_state = json.loads(base64.urlsafe_b64decode(encoded_state.encode()).decode())
        user_id = decoded_state.get("user_id")
        callback_url = decoded_state.get("callback_url", "http://localhost:5173/callback")

        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid state: Missing user_id")

        # Create OAuth Flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "redirect_uris": [REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=SCOPES,
        )
        flow.redirect_uri = REDIRECT_URI

        # Exchange the authorization code for access token
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Store the user's access and refresh token
        save_user_token(db, user_id, credentials.token, credentials.refresh_token)

        # Remove the used state from storage
        delete_state(state)

        # Return the OAuth access token
        return credentials.token,callback_url

    except Exception as e:
        logger.error(f"Error handling OAuth callback: {e}")
        raise HTTPException(status_code=500, detail="Failed to authenticate user.")

GOOGLE_DRIVE_API_TEST_URL = "https://www.googleapis.com/drive/v3/about?fields=user"

def validate_google_token(db: Session, user_id: str, token: str):
    """
    Tests the provided Google OAuth token by making a request to Google Drive API.
    If the token is expired, attempt to refresh it.
    """
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(GOOGLE_DRIVE_API_TEST_URL, headers=headers)
    if response.status_code == 200:
        return token  # ✅ Token is valid

    elif response.status_code in [401, 403]:  # ❌ Unauthorized or Forbidden (Expired Token)
        try:
            # 🔄 Attempt to refresh the token
            new_token = refresh_access_token(db, user_id)
            return new_token  # ✅ Return new valid token
        except HTTPException:
            remove_invalid_token(db, user_id)  # ❌ Refresh failed, remove token
            return None

    else:
        raise HTTPException(status_code=response.status_code, detail="Unexpected error from Google API")

def check_google_auth_status_service(db: Session, user_id: str):
    """
    Checks if the user has a valid Google OAuth token.
    If expired, it attempts to refresh it.
    """
    token = get_user_google_token(db, user_id)
    print(token,user_id)

    if not token:
        return False  # No token found

    valid_token = validate_google_token(db, user_id, token)

    return valid_token is not None

def get_google_auth_token_service(db: Session, user_id: str):
    """
    Retrieves the stored Google OAuth token if it is valid. 
    If expired, it tries to refresh it first.
    """
    token = get_user_google_token(db, user_id)

    if not token:
        return None

    return validate_google_token(db, user_id, token)