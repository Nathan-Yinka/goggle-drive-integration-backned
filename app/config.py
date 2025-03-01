import os
from dotenv import load_dotenv
from sqlalchemy.engine.url import URL

# Load environment variables from .env file
load_dotenv()

# 🔹 FastAPI Config
APP_NAME = "Google Drive Integration API"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "FastAPI backend for Google Drive authentication, file uploads, and management."
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

DB_CONFIG = {
    "drivername": "mysql+pymysql",
    "username": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD"),  # Can be None or empty
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "3306"),
    "database": os.getenv("DB_NAME", "google_drive"),
}

# Construct the connection URL manually to avoid password masking issues
if DB_CONFIG["password"]:
    DATABASE_URL = f"{DB_CONFIG['drivername']}://{DB_CONFIG['username']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
else:
    DATABASE_URL = f"{DB_CONFIG['drivername']}://{DB_CONFIG['username']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

print("Database URL:", DATABASE_URL)  # Debugging purpose


# 🔹 Google API Credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
CENTRAL_DRIVE_FOLDER_ID = os.getenv("CENTRAL_DRIVE_FOLDER_ID")

# 🔹 Security & Auth Config
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")  # Change this in production
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# 🔹 CORS Settings
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")  # Example: "http://localhost:5173,http://example.com"

# 🔹 Server Port
PORT = int(os.getenv("PORT", 8000))

# 🔹 Logging Config
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")