from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware import get_current_user
from app.services.drive_service import (
    list_drive_files, upload_file_to_drive, create_google_file, download_file
)

router = APIRouter()


@router.get("/drive/files")
async def get_drive_files(
    page_token: str = Query(None),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List user's Google Drive files with automatic token refresh."""
    return list_drive_files(db, user_id, page_token)

@router.post("/drive/upload")
async def upload_drive_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a file to Google Drive, ensuring valid token."""
    return upload_file_to_drive(db, user_id, file)

@router.get("/drive/download-file")
async def download_drive_file_endpoint(
    file_id: str = Query(..., description="Google Drive File ID"),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a file from Google Drive and return it as a stream."""
    return download_file(db, user_id, file_id)

@router.post("/drive/create-file")
async def create_file_endpoint(
    title: str = Query(..., description="Title of the file"),
    file_type: str = Query(..., description="File type: 'doc', 'sheet', 'slide', 'form', 'drawing'"),
    user_email: str = Query(..., description="Email of the user to share the file with"),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """API Endpoint to create a new Google Docs, Sheets, Slides, Forms, or Drawings file."""
    return create_google_file(db, user_id, title, file_type, user_email)
