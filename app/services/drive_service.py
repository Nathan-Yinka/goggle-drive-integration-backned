import io
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from fastapi import HTTPException,UploadFile
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from app.repositories.user_repo import get_user_token, save_user_token
from app.config import CENTRAL_DRIVE_FOLDER_ID, CLIENT_ID, CLIENT_SECRET

MIME_TYPES = {
    "doc": "application/vnd.google-apps.document",
    "sheet": "application/vnd.google-apps.spreadsheet",
    "slide": "application/vnd.google-apps.presentation",
    "form": "application/vnd.google-apps.form",
    "drawing": "application/vnd.google-apps.drawing"
}

EXPORT_FORMATS = {
    "application/vnd.google-apps.document": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "application/vnd.google-apps.spreadsheet": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    "application/vnd.google-apps.presentation": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
}

CONVERSION_MAP = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "application/vnd.google-apps.document",  # DOCX → Google Doc
    "text/plain": "application/vnd.google-apps.document",  # TXT → Google Doc
    "application/pdf": "application/vnd.google-apps.document",  # PDF → Google Doc
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "application/vnd.google-apps.spreadsheet",  # XLSX → Google Sheet
    "text/csv": "application/vnd.google-apps.spreadsheet",  # CSV → Google Sheet
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "application/vnd.google-apps.presentation"  # PPTX → Google Slides
}


user_page_tokens = {}


def get_drive_service(db: Session, user_id: str):
    """Authenticate the user and return Google Drive API service with auto-refresh support."""
    
    user_token = get_user_token(db, user_id)
    if not user_token:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # ✅ Create full credentials with refresh support
    credentials = Credentials(
        token=user_token.access_token,
        refresh_token=user_token.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    # 🔹 If token is expired, refresh it automatically
    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())  # Automatically refresh the token
            save_user_token(db, user_id, credentials.token, credentials.refresh_token)
        except Exception as e:
            raise HTTPException(status_code=401, detail="Failed to refresh access token. Please log in again.")

    return build("drive", "v3", credentials=credentials)

def list_drive_files(db: Session, user_id: str, page_token: str = None):
    """List files from Google Drive, ensuring token is valid."""
    drive_service = get_drive_service(db, user_id)
    
    response = drive_service.files().list(
        pageSize=10,
        fields="nextPageToken, files(id, name, mimeType, webViewLink)",
        pageToken=page_token
    ).execute()

    return {
        "files": response.get("files", []),
        "nextPageToken": response.get("nextPageToken")
    }

# def list_drive_files(db: Session, user_id: str, page_token: str = None, prev: bool = False):
#     """
#     List files from Google Drive, supporting pagination.
    
#     - If `prev=True`, retrieves the last stored page token for previous navigation.
#     - Stores history of page tokens for navigation.
#     """

#     drive_service = get_drive_service(db, user_id)

#     # Get the user's stored page history (default to an empty list)
#     page_history = user_page_tokens.get(user_id, [])
#     print(page_history)
#     print(page_history)
#     print(page_history)
#     print(page_history)

#     # If this is the first request (no `page_token` and `prev=False`), clear history
#     if not page_token and not prev:
#         user_page_tokens[user_id] = []  # Reset history

#     if prev:
#         if not page_history:
#             raise HTTPException(status_code=400, detail="No previous page available")
        
#         # Get the last stored token and remove it from history
#         page_token = page_history.pop()
#         user_page_tokens[user_id] = page_history  # Update history

#     response = drive_service.files().list(
#         pageSize=10,
#         fields="nextPageToken, files(id, name, mimeType, webViewLink)",
#         pageToken=page_token
#     ).execute()

#     # Save the `nextPageToken` for future navigation (only if not going back)
#     next_page_token = response.get("nextPageToken")
#     if next_page_token and not prev:
#         page_history.append(next_page_token)
#         user_page_tokens[user_id] = page_history  # Store history

#     return {
#         "files": response.get("files", []),
#         "nextPageToken": next_page_token,
#         "hasPreviousPage": len(page_history) > 0  # True only if there is history
#     }


def upload_file_to_drive(db: Session, user_id: str, file: UploadFile):
    """Upload a file to Google Drive, convert it when possible, and return correct edit/view links."""
    drive_service = get_drive_service(db, user_id)

    try:
        file_stream = io.BytesIO(file.file.read())  # Read file into memory
        media = MediaIoBaseUpload(file_stream, mimetype=file.content_type, resumable=True)

        converted_mimeType = CONVERSION_MAP.get(file.content_type, file.content_type)
        print(file.content_type)
        print(converted_mimeType)

        file_metadata = {
            "name": file.filename,
            "mimeType": converted_mimeType,
            # "parents": [CENTRAL_DRIVE_FOLDER_ID] if CENTRAL_DRIVE_FOLDER_ID else None,
        }

        # ✅ Upload file
        uploaded_file = drive_service.files().create(
            body=file_metadata, media_body=media, fields="id, mimeType"
        ).execute()
        file_id = uploaded_file["id"]
        uploaded_mime_type = uploaded_file["mimeType"]
         # ✅ Set file to view-only
        permission = {
            "type": "anyone",
            "role": "reader"  # This ensures view-only access
        }
        drive_service.permissions().create(fileId=file_id, body=permission).execute()
        # ✅ Ensure it opens in the correct Google Editor
        open_links = {
            "application/vnd.google-apps.document": f"https://docs.google.com/document/d/{file_id}/edit",
            "application/vnd.google-apps.spreadsheet": f"https://docs.google.com/spreadsheets/d/{file_id}/edit",
            "application/vnd.google-apps.presentation": f"https://docs.google.com/presentation/d/{file_id}/edit",
        }

        edit_link = open_links.get(uploaded_mime_type, f"https://drive.google.com/file/d/{file_id}/view")
        view_link = f"https://docs.google.com/document/d/{file_id}/view"

        return JSONResponse(content={
            "fileId": file_id,
            "fileName": file.filename,
            "editLink": edit_link,  # ✅ Now correctly opens in Docs, Sheets, or Slides
            "viewLink": view_link
        })

    except HttpError as error:
        raise HTTPException(status_code=500, detail=f"Google Drive API error: {error}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# def upload_file_to_drive(db: Session, user_id: str, file: UploadFile):
#     """Upload a file to Google Drive, restrict it to view-only, and ensure it opens in Google Docs."""
#     drive_service = get_drive_service(db, user_id)

#     try:
#         file_stream = io.BytesIO(file.file.read())  # Read file into memory
#         media = MediaIoBaseUpload(file_stream, mimetype=file.content_type, resumable=True)

#         converted_mimeType = CONVERSION_MAP.get(file.content_type, file.content_type)

#         file_metadata = {
#             "name": file.filename,
#             "mimeType": converted_mimeType,
#         }

#         # ✅ Upload file
#         uploaded_file = drive_service.files().create(
#             body=file_metadata, media_body=media, fields="id, mimeType"
#         ).execute()
#         file_id = uploaded_file["id"]
#         uploaded_mime_type = uploaded_file["mimeType"]

#         # ✅ Enforce view-only access
#         permission = {
#             "type": "anyone",
#             "role": "reader"  # Ensures only viewing, no editing
#         }
#         drive_service.permissions().create(fileId=file_id, body=permission).execute()

#         # ✅ Ensure it only opens in Google Docs for viewing
#         view_link = f"https://docs.google.com/document/d/{file_id}/view"

#         return JSONResponse(content={
#             "fileId": file_id,
#             "fileName": file.filename,
#             "viewLink": view_link  # ✅ Forces view mode in Google Docs
#         })

#     except HttpError as error:
#         raise HTTPException(status_code=500, detail=f"Google Drive API error: {error}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

def create_google_file(db: Session, user_id: str, title: str, file_type: str, user_email: str):
    """Create a new Google Docs, Sheets, Slides, Forms, or Drawings file."""
    drive_service = get_drive_service(db, user_id)

    if file_type not in MIME_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")

    try:
        file_metadata = {
            "name": title,
            "mimeType": MIME_TYPES[file_type]
        }
        created_file = drive_service.files().create(body=file_metadata).execute()
        file_id = created_file.get("id")

        # Share file with the user
        permission = {
            "type": "user",
            "role": "writer",
        }
        if user_email:
            permission['emailAddress'] = user_email
        if  user_email:
            drive_service.permissions().create(fileId=file_id, body=permission, sendNotificationEmail=True).execute()

        # Generate edit and embed URLs
        base_url = "https://docs.google.com/"
        file_type_paths = {
            "doc": "document",
            "sheet": "spreadsheets",
            "slide": "presentation",
            "form": "forms",
            "drawing": "drawings"
        }

        edit_url = f"{base_url}{file_type_paths[file_type]}/d/{file_id}/edit"
        embed_url = f"{base_url}{file_type_paths[file_type]}/d/{file_id}/preview"

        return {
            "message": f"Google {file_type} created successfully",
            "fileId": file_id,
            "editLink": edit_url,
            "embedLink": embed_url,
            "sharedWith": user_email
        }

    except HttpError as error:
        raise HTTPException(status_code=500, detail=str(error))

def download_file(db: Session, user_id: str, file_id: str):
    """Download a file from Google Drive and return it as a stream."""
    drive_service = get_drive_service(db, user_id)

    try:
        # Fetch file metadata
        file_metadata = drive_service.files().get(fileId=file_id).execute()
        file_name = file_metadata["name"]
        mime_type = file_metadata["mimeType"]

        # Handle export for Google Docs, Sheets, and Slides
        if mime_type in EXPORT_FORMATS:
            export_mime, file_extension = EXPORT_FORMATS[mime_type]
            file_data = drive_service.files().export(fileId=file_id, mimeType=export_mime).execute()
            final_mime_type = export_mime
        else:
            # Download normal files
            request = drive_service.files().get_media(fileId=file_id)
            file_data = request.execute()
            file_extension = ""  # Keep original extension
            final_mime_type = mime_type

        # Ensure correct filename extension
        sanitized_file_name = file_name.replace(" ", "_") + file_extension
        file_stream = io.BytesIO(file_data)

        return StreamingResponse(file_stream, media_type=final_mime_type, headers={
            "Content-Disposition": f'attachment; filename="{sanitized_file_name}"',
            "Content-Type": final_mime_type
        })

    except HttpError as error:
        raise HTTPException(status_code=500, detail=f"Google Drive API error: {error}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
