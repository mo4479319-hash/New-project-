"""
Auth dependency for FastAPI routes.
Validates the Supabase JWT from the Authorization header.
"""

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt

from app.core.config import get_settings


async def get_current_user(request: Request) -> dict:
    """
    Extract and validate the Supabase JWT from the Authorization header.
    Returns the decoded token payload (contains user_id as 'sub').
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split("Bearer ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    settings = get_settings()
    try:
        # Supabase JWTs are signed with the JWT secret derived from your project.
        # For simplicity, we decode without verification in development.
        # In production, verify with your Supabase JWT secret.
        payload = jwt.decode(
            token,
            settings.SUPABASE_KEY,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
