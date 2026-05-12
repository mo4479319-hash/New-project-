"""
Website configuration endpoints.
Read configs, view history, publish (staging → production), and undo.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.core.config import get_supabase
from app.models.schemas import PublishRequest, WebsiteConfigHistoryItem, WebsiteConfigResponse
from app.services.website import (
    get_config_history,
    get_files_for_config,
    get_latest_config,
    save_config,
    save_files,
)

router = APIRouter(prefix="/api/websites", tags=["websites"])


@router.get("/{business_id}", response_model=WebsiteConfigResponse)
async def get_website(business_id: UUID, user: dict = Depends(get_current_user)):
    """Get the latest staging website configuration for a business."""
    _assert_ownership(str(business_id), user["sub"])

    config = get_latest_config(str(business_id), environment="staging")
    if not config:
        raise HTTPException(status_code=404, detail="No website found for this business")

    files = get_files_for_config(config["id"])
    return WebsiteConfigResponse(
        id=config["id"],
        business_id=config["business_id"],
        backbone=config["backbone"],
        environment=config["environment"],
        created_at=config["created_at"],
        files=files,
    )


@router.get("/{business_id}/production", response_model=WebsiteConfigResponse)
async def get_production_website(business_id: UUID, user: dict = Depends(get_current_user)):
    """Get the latest production website configuration."""
    _assert_ownership(str(business_id), user["sub"])

    config = get_latest_config(str(business_id), environment="production")
    if not config:
        raise HTTPException(status_code=404, detail="No published website found")

    files = get_files_for_config(config["id"])
    return WebsiteConfigResponse(
        id=config["id"],
        business_id=config["business_id"],
        backbone=config["backbone"],
        environment=config["environment"],
        created_at=config["created_at"],
        files=files,
    )


@router.get("/{business_id}/history", response_model=list[WebsiteConfigHistoryItem])
async def get_website_history(business_id: UUID, user: dict = Depends(get_current_user)):
    """Get the version history of website configurations."""
    _assert_ownership(str(business_id), user["sub"])
    history = get_config_history(str(business_id))
    return history


@router.post("/{business_id}/publish")
async def publish_website(business_id: UUID, user: dict = Depends(get_current_user)):
    """
    Promote the latest staging config to production.
    Creates a new production config row with the same backbone and files.
    """
    _assert_ownership(str(business_id), user["sub"])

    staging = get_latest_config(str(business_id), environment="staging")
    if not staging:
        raise HTTPException(status_code=404, detail="No staging website to publish")

    # Create production config (immutable — new row)
    prod_config = save_config(
        business_id=str(business_id),
        user_id=user["sub"],
        backbone=staging["backbone"],
        environment="production",
    )

    # Copy files to the new production config
    staging_files = get_files_for_config(staging["id"])
    if staging_files:
        save_files(prod_config["id"], staging_files)

    return {
        "message": "Website published to production",
        "configuration_id": prod_config["id"],
    }


@router.post("/{business_id}/undo")
async def undo_website(business_id: UUID, user: dict = Depends(get_current_user)):
    """
    Undo the last website edit by reverting to the previous staging version.
    Since configs are immutable, we just create a new config with the previous backbone.
    """
    _assert_ownership(str(business_id), user["sub"])

    sb = get_supabase()
    # Get the two most recent staging configs
    result = (
        sb.table("website_configurations")
        .select("*")
        .eq("business_id", str(business_id))
        .eq("environment", "staging")
        .order("created_at", desc=True)
        .limit(2)
        .execute()
    )
    if not result.data or len(result.data) < 2:
        raise HTTPException(status_code=400, detail="Nothing to undo — no previous version exists")

    previous = result.data[1]  # second most recent

    # Create a new config with the previous backbone (immutable append)
    reverted = save_config(
        business_id=str(business_id),
        user_id=user["sub"],
        backbone=previous["backbone"],
        environment="staging",
    )

    # Copy files from previous version
    prev_files = get_files_for_config(previous["id"])
    if prev_files:
        save_files(reverted["id"], prev_files)

    return {
        "message": "Reverted to previous version",
        "configuration_id": reverted["id"],
    }


def _assert_ownership(business_id: str, user_id: str):
    """Verify the user owns this business."""
    sb = get_supabase()
    result = (
        sb.table("businesses")
        .select("id")
        .eq("id", business_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Business not found")
