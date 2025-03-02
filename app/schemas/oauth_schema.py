from pydantic import BaseModel


class OAuthCallbackRequest(BaseModel):
    """Schema for OAuth callback request."""
    code: str
    state: str