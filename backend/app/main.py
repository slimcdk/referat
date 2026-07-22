from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth import router as auth_router
from app.api.meetings import router as meetings_router
from app.api.ws import router as ws_router

app = FastAPI(
    title="Referat API",
    description="Secure backend for the Referat Meeting Analysis web application.",
    version="1.0.0"
)

# CORS middleware configuration (crucial for Angular on port 4200 to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(meetings_router, prefix="/api")
app.include_router(ws_router, prefix="/api")

@app.get("/api/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "service": "Referat API"}
