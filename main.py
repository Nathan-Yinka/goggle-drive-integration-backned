import os
from fastapi import FastAPI,HTTPException
from fastapi.responses import JSONResponse

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

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc: HTTPException):
    """
    Overrides FastAPI's default error format to use 'message' instead of 'detail'.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},  # Rename 'detail' to 'message'
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
    expose_headers=["Content-Disposition"]
)

# Include Routes
app.include_router(auth_router)
app.include_router(drive_router)

@app.get("/", tags=["Health Check"])
async def root():
    """
    Health check endpoint to confirm the API is running.
    """
    return {"message": "Google Drive Integration API is running successfully 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
