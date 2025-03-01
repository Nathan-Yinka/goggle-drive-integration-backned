import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.controllers.auth_controller import router as auth_router
from app.controllers.drive_controller import router as drive_router
from app.database import engine, Base
from fastapi.staticfiles import StaticFiles
import os

# Ensure MySQL tables are created
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Google Drive Integration API",
    description="Google Drive authentication, file uploads, and central drive management.",
    version="1.0.0",
)

# Ensure 'static' directory exists before mounting
STATIC_DIR = "static"
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)  # Create it if missing
    
# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routes
app.include_router(auth_router)
app.include_router(drive_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
