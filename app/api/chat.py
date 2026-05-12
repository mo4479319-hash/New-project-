"""
Chat endpoint — the main interface for creating and editing websites.
Users send messages, the AI classifies intent and generates/edits the website.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.core.config import get_supabase
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat import handle_chat_message

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, user: dict = Depends(get_current_user)):
    """
    Send a message to create or edit a website.

    The AI will:
    1. Classify the intent (create_website, update_website, general)
    2. Generate or edit website files accordingly
    3. Save the new configuration version
    4. Return the response with updated backbone and files
    """
    user_id = user["sub"]

    # Verify user owns this business
    sb = get_supabase()
    biz = (
        sb.table("businesses")
        .select("id")
        .eq("id", str(body.business_id))
        .eq("user_id", user_id)
        .execute()
    )
    if not biz.data:
        raise HTTPException(status_code=404, detail="Business not found")

    result = await handle_chat_message(
        user_id=user_id,
        business_id=str(body.business_id),
        message=body.message,
        conversation_id=str(body.conversation_id) if body.conversation_id else None,
    )
    return result
