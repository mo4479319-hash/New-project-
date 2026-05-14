"""
Business CRUD endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.core.config import get_supabase
from app.models.schemas import BusinessCreate, BusinessResponse

router = APIRouter(prefix="/api/businesses", tags=["businesses"])


@router.post("/", response_model=BusinessResponse)
async def create_business(body: BusinessCreate, user: dict = Depends(get_current_user)):
    """Create a new business for the authenticated user."""
    sb = get_supabase()
    row = body.model_dump(exclude_none=True)
    row["user_id"] = user["sub"]

    result = sb.table("businesses").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create business")
    return result.data[0]


@router.get("/{business_id}", response_model=BusinessResponse)
async def get_business(business_id: UUID, user: dict = Depends(get_current_user)):
    """Get a business by ID (must belong to the authenticated user)."""
    sb = get_supabase()
    result = (
        sb.table("businesses")
        .select("*")
        .eq("id", str(business_id))
        .eq("user_id", user["sub"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Business not found")
    return result.data[0]


@router.get("/", response_model=list[BusinessResponse])
async def list_businesses(user: dict = Depends(get_current_user)):
    """List all businesses for the authenticated user."""
    sb = get_supabase()
    result = (
        sb.table("businesses")
        .select("*")
        .eq("user_id", user["sub"])
        .order("created_at", desc=True)
        .execute()
    )
    return result.data
