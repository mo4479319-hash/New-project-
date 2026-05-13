"""
Auth dependency for FastAPI routes.
Validates the Supabase JWT by calling supabase.auth.get_user().
"""

from fastapi import HTTPException, Request

from app.core.config import get_supabase


async def get_current_user(request: Request) -> dict:
    """
    Extract the Supabase JWT from the Authorization header and validate it
    via the Supabase Auth API. Returns a dict with 'sub' (user id) and 'email'.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split("Bearer ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token")

    try:
        sb = get_supabase()
        user_response = sb.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"sub": user.id, "email": user.email}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
