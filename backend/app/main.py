from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.user import User
from app.api.auth import router as auth_router
from app.api.meetings import router as meetings_router
from app.api.ws import router as ws_router
from app.api.search import router as search_router
from app.api.settings import router as settings_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed default admin user if no users exist in the database
    async with async_session_maker() as session:
        try:
            result = await session.execute(select(User))
            user = result.scalars().first()
            if not user:
                print("==================================================")
                print("  📝 REFERAT APP INITIAL STARTUP")
                print("  No users found in database.")
                print("  Seeding default administrator:")
                print("  Email:    admin@referat.io")
                print("  Password: admin_secure_pass_change_me")
                print("==================================================")
                default_user = User(
                    email="admin@referat.io",
                    hashed_password=get_password_hash("admin_secure_pass_change_me")
                )
                session.add(default_user)
                await session.commit()
        except Exception as e:
            print(f"Database startup seeding failed: {str(e)}")
    yield

app = FastAPI(
    title="Referat API",
    description="Secure backend for the Referat Meeting Analysis web application.",
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(search_router, prefix="/api")
app.include_router(settings_router, prefix="/api")

@app.get("/api/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "service": "Referat API"}
