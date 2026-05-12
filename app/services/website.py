"""
Website backbone and configuration management.
Handles creating, updating, and versioning website configurations.

Key design (from kora): configurations are IMMUTABLE.
Every edit creates a new row. This gives us undo, audit trail,
and conversation-linked changes for free.
"""

import json
from typing import Any, Optional
from uuid import UUID

from app.core.config import get_supabase


def build_initial_backbone(business: dict) -> dict:
    """
    Build an initial website backbone from business info.
    This is the semantic "what" of the website — content and structure,
    not the "how" (HTML/CSS implementation).
    """
    return {
        "business": {
            "name": business.get("name", ""),
            "description": business.get("description", ""),
            "phone": business.get("phone", ""),
            "email": business.get("email", ""),
            "address": business.get("address", ""),
            "city": business.get("city", ""),
            "state": business.get("state", ""),
            "country": business.get("country", ""),
        },
        "branding": {
            "primaryColor": "#3B82F6",
            "secondaryColor": "#1E40AF",
            "accentColor": "#F59E0B",
            "fontFamily": "Inter, sans-serif",
            "logo": business.get("logo_url", ""),
        },
        "sections": [
            {
                "type": "hero",
                "headline": f"Welcome to {business.get('name', 'Our Business')}",
                "subheading": business.get("description", ""),
                "image": "",
            },
            {
                "type": "about",
                "title": "About Us",
                "text": business.get("description", ""),
            },
            {
                "type": "contact",
                "title": "Contact Us",
                "phone": business.get("phone", ""),
                "email": business.get("email", ""),
                "address": business.get("address", ""),
            },
        ],
    }


def compute_json_patch(old: dict, new: dict, path: str = "") -> list[dict]:
    """
    Compute a simplified RFC 6902 JSON Patch between two dicts.
    Returns a list of patch operations (add, replace, remove).
    """
    ops: list[dict] = []

    all_keys = set(list(old.keys()) + list(new.keys()))
    for key in all_keys:
        current_path = f"{path}/{key}"

        if key not in old:
            ops.append({"op": "add", "path": current_path, "value": new[key]})
        elif key not in new:
            ops.append({"op": "remove", "path": current_path})
        elif old[key] != new[key]:
            if isinstance(old[key], dict) and isinstance(new[key], dict):
                ops.extend(compute_json_patch(old[key], new[key], current_path))
            else:
                ops.append({"op": "replace", "path": current_path, "value": new[key]})

    return ops


def get_latest_config(business_id: str, environment: str = "staging") -> Optional[dict]:
    """Fetch the most recent configuration for a business + environment."""
    sb = get_supabase()
    result = (
        sb.table("website_configurations")
        .select("*")
        .eq("business_id", business_id)
        .eq("environment", environment)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def save_config(
    business_id: str,
    user_id: str,
    backbone: dict,
    environment: str = "staging",
    difference: Optional[list[dict]] = None,
    message_id: Optional[str] = None,
) -> dict:
    """
    Save a new website configuration (immutable insert).
    Never updates existing rows — always creates a new version.
    """
    sb = get_supabase()
    row = {
        "business_id": business_id,
        "user_id": user_id,
        "backbone": backbone,
        "environment": environment,
    }
    if difference is not None:
        row["difference"] = difference
    if message_id is not None:
        row["message_id"] = message_id

    result = sb.table("website_configurations").insert(row).execute()
    return result.data[0]


def save_files(configuration_id: str, files: list[dict]) -> list[dict]:
    """Save generated website files linked to a configuration."""
    if not files:
        return []
    sb = get_supabase()
    rows = [
        {
            "configuration_id": configuration_id,
            "file_path": f["file_path"],
            "content": f["content"],
        }
        for f in files
    ]
    result = sb.table("website_files").insert(rows).execute()
    return result.data


def get_files_for_config(configuration_id: str) -> list[dict]:
    """Get all files for a specific configuration version."""
    sb = get_supabase()
    result = (
        sb.table("website_files")
        .select("file_path, content")
        .eq("configuration_id", configuration_id)
        .execute()
    )
    return result.data


def get_config_history(business_id: str, environment: str = "staging", limit: int = 20) -> list[dict]:
    """Get configuration version history for a business."""
    sb = get_supabase()
    result = (
        sb.table("website_configurations")
        .select("id, environment, difference, message_id, created_at")
        .eq("business_id", business_id)
        .eq("environment", environment)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data
