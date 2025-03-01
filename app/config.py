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

# 🔹 Database Config (Dynamically Handle Password)
DB_CONFIG = {
    "drivername": "mysql+pymysql",
    "username": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD"),  # Can be None if not set
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "3306"),
    "database": os.getenv("DB_NAME", "goggle_drive"),
}

# 🔹 Remove password from DB_CONFIG if it's empty or None
if not DB_CONFIG["password"]:
    DB_CONFIG.pop("password")

# 🔹 Construct DATABASE_URL dynamically
DATABASE_URL = str(URL.create(**DB_CONFIG))

# 🔹 Redis Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Print for debugging
print(f"🔹 Database URL: {DATABASE_URL}")

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

