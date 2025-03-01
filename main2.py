import os
import requests
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse,StreamingResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.errors import HttpError 
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
from googleapiclient.http import MediaIoBaseUpload
import io

# Load environment variables
load_dotenv()


# Initialize FastAPI with Swagger
app = FastAPI(
    title="Google Drive Integration API",
    description="FastAPI backend for Google Drive authentication, file uploads, and central drive management.",
    version="1.0.0",
    docs_url="/",
    redoc_url="/redoc"
)

# 🔹 Enable CORS for Frontend Communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend URL in production (e.g., "http://localhost:5173")
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Allows all headers (Authorization, Content-Type, etc.)
)



# Google API Credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
CENTRAL_DRIVE_FOLDER_ID = os.getenv("CENTRAL_DRIVE_FOLDER_ID")


# print("CLIENT_ID:", CLIENT_ID)
# print("CLIENT_SECRET:", CLIENT_SECRET)
# print("REDIRECT_URI:", REDIRECT_URI)

SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

# Store user tokens in memory (Replace with a database in production)
user_tokens = {}


MIME_TYPES = {
    "doc": "application/vnd.google-apps.document",
    "sheet": "application/vnd.google-apps.spreadsheet",
    "slide": "application/vnd.google-apps.presentation",
    "form": "application/vnd.google-apps.form",
    "drawing": "application/vnd.google-apps.drawing"
}


# 🔹 1️⃣ Generate Google Login URL
@app.get("/auth")
async def google_auth():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = REDIRECT_URI
    auth_url, _ = flow.authorization_url(prompt="consent")
    return JSONResponse(content={"authUrl": auth_url})


# 🔹 2️⃣ Handle OAuth Callback & Store Tokens
@app.get("/auth/callback")
async def google_auth_callback(code: str):
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials

    user_id = "test_user" 
    user_tokens[user_id] = {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
    }

    # return JSONResponse(content={"message": "Authentication successful", "tokens": user_tokens[user_id]})
    # ✅ Redirect back to frontend with the access token
    frontend_redirect_url = f"http://localhost:5173/callback?token={credentials.token}"
    return RedirectResponse(frontend_redirect_url)


# 🔹 3️⃣ Refresh Access Token if Expired
def refresh_access_token(user_id):
    if user_id not in user_tokens:
        raise HTTPException(status_code=401, detail="User not authenticated")

    refresh_token = user_tokens[user_id]["refresh_token"]
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    response = requests.post(token_url, data=payload)
    print("this token in the refresh function is",response.json())
    if response.status_code == 200:
        new_tokens = response.json()
        user_tokens[user_id]["access_token"] = new_tokens["access_token"]
    else:
        raise HTTPException(status_code=401, detail="Failed to refresh token")


# 🔹 4️⃣ List User's Google Drive Files
@app.get("/drive/files")
async def list_drive_files(page_token: str = Query(None, description="Token for the next page")):
    user_id = "test_user"  # Replace with actual user authentication
    refresh_access_token(user_id)  # Ensure access token is valid

    credentials = Credentials(token=user_tokens[user_id]["access_token"])
    drive_service = build("drive", "v3", credentials=credentials)

    response = drive_service.files().list(
        pageSize=10,  # Fetch 10 files at a time
        fields="nextPageToken, files(id, name, mimeType, webViewLink)",
        pageToken=page_token
    ).execute()

    files = response.get("files", [])
    next_page_token = response.get("nextPageToken")  # Token for the next page

    return JSONResponse(content={
        "files": files,
        "nextPageToken": next_page_token  # Use this to fetch the next page
    })


# 🔹 5️⃣ Upload a File to Google Drive
@app.post("/drive/upload")
async def upload_file(file: UploadFile = File(...)):
    """Uploads a file to Google Drive, converts it when possible, and returns correct edit/view links."""
    user_id = "test_user"
    refresh_access_token(user_id)

    credentials = Credentials(token=user_tokens[user_id]["access_token"])
    drive_service = build("drive", "v3", credentials=credentials)

    try:
        file_stream = io.BytesIO(await file.read())  # Read file into memory
        media = MediaIoBaseUpload(file_stream, mimetype=file.content_type, resumable=True)

        # 🔹 **Convert based on file type**
        conversion_map = {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "application/vnd.google-apps.document",  # DOCX ➝ Google Doc
            "text/plain": "application/vnd.google-apps.document",  # TXT ➝ Google Doc
            "application/pdf": "application/vnd.google-apps.document",  # PDF ➝ Google Doc
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "application/vnd.google-apps.spreadsheet",  # XLSX ➝ Google Sheet
            "text/csv": "application/vnd.google-apps.spreadsheet",  # CSV ➝ Google Sheet
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "application/vnd.google-apps.presentation"  # PPTX ➝ Google Slides
        }

        converted_mimeType = conversion_map.get(file.content_type, None)

        file_metadata = {
            "name": file.filename,
            "mimeType": converted_mimeType if converted_mimeType else None,  # Convert if applicable
            # "parents": [CENTRAL_DRIVE_FOLDER_ID]  # Optional: Store inside a folder
        }

        # ✅ Upload file with conversion (if applicable)
        uploaded_file = drive_service.files().create(
            body=file_metadata, media_body=media, fields="id, mimeType"
        ).execute()
        file_id = uploaded_file["id"]
        uploaded_mime_type = uploaded_file["mimeType"]  # Get the actual MIME type after upload

        # ✅ Ensure it opens in the correct Google Editor
        open_links = {
            "application/vnd.google-apps.document": f"https://docs.google.com/document/d/{file_id}/edit",
            "application/vnd.google-apps.spreadsheet": f"https://docs.google.com/spreadsheets/d/{file_id}/edit",
            "application/vnd.google-apps.presentation": f"https://docs.google.com/presentation/d/{file_id}/edit",
        }

        edit_link = open_links.get(uploaded_mime_type, f"https://drive.google.com/file/d/{file_id}/view")
        view_link = f"https://drive.google.com/file/d/{file_id}/view"

        return JSONResponse(content={
            "fileId": file_id,
            "fileName": file.filename,
            "editLink": edit_link,  # ✅ Now correctly opens in Docs, Sheets, or Slides
            "viewLink": view_link
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔹 6️⃣ Create a New File in Central Drive Folder
@app.post("/drive/create-central")
async def create_file_in_central_drive(filename: str = Query(...), mime_type: str = Query(...)):
    user_id = "test_user"  # Replace with actual user authentication
    refresh_access_token(user_id)

    credentials = Credentials(token=user_tokens[user_id]["access_token"])
    drive_service = build("drive", "v3", credentials=credentials)

    file_metadata = {
        "name": filename,
        "mimeType": mime_type,
        "parents": [CENTRAL_DRIVE_FOLDER_ID],  # Place file in central drive folder
    }

    created_file = drive_service.files().create(body=file_metadata).execute()
    
    return JSONResponse(content={"message": "File created in central drive", "fileId": created_file["id"]})


@app.post("/drive/create-file")
async def create_google_file(
    title: str = Query(..., description="Title of the file"),
    file_type: str = Query(..., description="File type: 'doc', 'sheet', 'slide', 'form', 'drawing'"),
    user_email: str = Query(..., description="Email of the user to share the file with")
):
    """
    Creates a new Google Docs, Sheets, Slides, Forms, or Drawings file.
    """

    user_id = "test_user"
    refresh_access_token(user_id)

    credentials = Credentials(token=user_tokens[user_id]["access_token"])
    drive_service = build("drive", "v3", credentials=credentials)

    try:
        if file_type not in MIME_TYPES:
            return JSONResponse(status_code=400, content={"error": "Invalid file type"})

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
            "emailAddress": user_email,
        }
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

        return JSONResponse(content={
            "message": f"Google {file_type} created successfully",
            "fileId": file_id,
            "editLink": edit_url,
            "embedLink": embed_url,
            "sharedWith": user_email
        })

    except HttpError as error:
        return JSONResponse(status_code=500, content={"error": str(error)})


@app.get("/drive/download-file")
async def download_file(file_id: str = Query(..., description="Google Drive File ID")):
    """Download a file from Google Drive and return the filename in the response headers"""
    user_id = "test_user"
    refresh_access_token(user_id)

    credentials = Credentials(token=user_tokens[user_id]["access_token"])
    drive_service = build("drive", "v3", credentials=credentials)

    try:
        # Get file metadata
        file_metadata = drive_service.files().get(fileId=file_id).execute()
        file_name = file_metadata["name"]
        mime_type = file_metadata["mimeType"]

        # Handle export for Google Docs files
        export_formats = {
            "application/vnd.google-apps.document": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
            "application/vnd.google-apps.spreadsheet": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
            "application/vnd.google-apps.presentation": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
        }

        if mime_type in export_formats:
            export_mime, file_extension = export_formats[mime_type]
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))