from pydantic import BaseModel

class DrivePaginationRequest(BaseModel):
    """Schema for requesting file list with pagination"""
    page_token: str = None
    prev: bool = False