from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.settings import SystemSettings
from app.schemas.search import SystemSettingsSchema

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("", response_model=SystemSettingsSchema)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(SystemSettings))
    db_settings = result.scalars().first()
    
    # If no settings exist yet, create a default settings entry
    if not db_settings:
        db_settings = SystemSettings(llm_size="small", data_retention_days=30)
        db.add(db_settings)
        await db.commit()
        await db.refresh(db_settings)
        
    return db_settings

@router.put("", response_model=SystemSettingsSchema)
async def update_settings(
    settings_in: SystemSettingsSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(SystemSettings))
    db_settings = result.scalars().first()
    
    if not db_settings:
        db_settings = SystemSettings()
        db.add(db_settings)
        
    db_settings.llm_size = settings_in.llm_size
    db_settings.data_retention_days = settings_in.data_retention_days
    
    await db.commit()
    await db.refresh(db_settings)
    return db_settings
