"""
Chat orchestration service.
Handles the full flow: classify intent → create/edit website → save results.
This is the simplified equivalent of kora's AgentOrchestrator.
"""

import json
from typing import Optional
from uuid import UUID

from app.core.config import get_supabase
from app.models.schemas import ChatResponse
from app.services import llm
from app.services.website import (
    build_initial_backbone,
    compute_json_patch,
    get_files_for_config,
    get_latest_config,
    save_config,
    save_files,
)


async def handle_chat_message(
    user_id: str,
    business_id: str,
    message: str,
    conversation_id: Optional[str] = None,
) -> ChatResponse:
    """
    Main chat handler. Classifies intent and routes to the appropriate flow.

    Flow:
    1. Ensure conversation exists
    2. Save user message
    3. Classify intent (create_website / update_website / general)
    4. Route to handler
    5. Save assistant response
    6. Return result
    """
    sb = get_supabase()

    # 1. Ensure conversation exists
    if conversation_id:
        conv = sb.table("conversations").select("id").eq("id", conversation_id).execute()
        if not conv.data:
            conversation_id = None

    if not conversation_id:
        conv = (
            sb.table("conversations")
            .insert({"business_id": business_id, "user_id": user_id, "title": message[:100]})
            .execute()
        )
        conversation_id = conv.data[0]["id"]

    # 2. Save user message
    user_msg = (
        sb.table("messages")
        .insert({
            "conversation_id": conversation_id,
            "role": "user",
            "content": message,
        })
        .execute()
    )
    user_msg_id = user_msg.data[0]["id"]

    # 3. Classify intent with recent history
    history = _get_recent_history(conversation_id, limit=6)
    intent_result = await llm.classify_intent(message, history=history)

    # 4. Route by intent
    if intent_result.intent == "create_website":
        result = await _handle_create_website(
            user_id=user_id,
            business_id=business_id,
            message=message,
            conversation_id=conversation_id,
            message_id=user_msg_id,
        )
    elif intent_result.intent == "update_website":
        result = await _handle_update_website(
            user_id=user_id,
            business_id=business_id,
            message=message,
            conversation_id=conversation_id,
            message_id=user_msg_id,
        )
    else:
        # General chat — just return the acknowledgement
        result = ChatResponse(
            conversation_id=UUID(conversation_id),
            message=intent_result.response or "Hi! I can help you create and edit websites. What would you like to do?",
            intent="general",
        )

    # 5. Save assistant response
    sb.table("messages").insert({
        "conversation_id": conversation_id,
        "role": "assistant",
        "content": result.message,
        "metadata": {
            "intent": result.intent,
            "has_backbone": result.backbone is not None,
            "file_count": len(result.files) if result.files else 0,
        },
    }).execute()

    return result


async def _handle_create_website(
    user_id: str,
    business_id: str,
    message: str,
    conversation_id: str,
    message_id: str,
) -> ChatResponse:
    """Handle website creation from scratch."""
    sb = get_supabase()

    # Fetch business details for context
    biz = sb.table("businesses").select("*").eq("id", business_id).execute()
    if not biz.data:
        return ChatResponse(
            conversation_id=UUID(conversation_id),
            message="Business not found. Please create a business first.",
            intent="create_website",
        )

    business = biz.data[0]

    # Build context prompt for the LLM
    context = f"""Create a website for this business:

Business Name: {business.get('name', '')}
Type: {business.get('type', 'business')}
Description: {business.get('description', '')}
Phone: {business.get('phone', '')}
Email: {business.get('email', '')}
Address: {business.get('address', '')}
City: {business.get('city', '')}
State: {business.get('state', '')}

User's additional instructions: {message}

Create a modern, professional website with all the information above.
"""

    # Generate website with LLM
    llm_result = await llm.create_website(context)

    # Save backbone as new configuration
    backbone = llm_result.backbone or build_initial_backbone(business)
    config = save_config(
        business_id=business_id,
        user_id=user_id,
        backbone=backbone,
        environment="staging",
        message_id=message_id,
    )

    # Save generated files
    saved_files = []
    if llm_result.files:
        saved_files = save_files(config["id"], llm_result.files)

    return ChatResponse(
        conversation_id=UUID(conversation_id),
        message=llm_result.description or "Your website has been created! You can preview it now.",
        intent="create_website",
        backbone=backbone,
        files=llm_result.files,
    )


async def _handle_update_website(
    user_id: str,
    business_id: str,
    message: str,
    conversation_id: str,
    message_id: str,
) -> ChatResponse:
    """Handle editing an existing website."""
    # Get current config
    current = get_latest_config(business_id, environment="staging")
    if not current:
        # No website yet — treat as create
        return await _handle_create_website(
            user_id=user_id,
            business_id=business_id,
            message=message,
            conversation_id=conversation_id,
            message_id=message_id,
        )

    old_backbone = current.get("backbone", {})
    current_files = get_files_for_config(current["id"])

    # Edit with LLM
    llm_result = await llm.edit_website(
        user_message=message,
        current_backbone=old_backbone,
        current_files=current_files,
    )

    # Compute diff for audit trail
    new_backbone = llm_result.backbone or old_backbone
    diff = compute_json_patch(old_backbone, new_backbone)

    # Save new configuration version (immutable — never update the old one)
    config = save_config(
        business_id=business_id,
        user_id=user_id,
        backbone=new_backbone,
        environment="staging",
        difference=diff if diff else None,
        message_id=message_id,
    )

    # Save updated files
    if llm_result.files:
        save_files(config["id"], llm_result.files)

    return ChatResponse(
        conversation_id=UUID(conversation_id),
        message=llm_result.description or "Your website has been updated!",
        intent="update_website",
        backbone=new_backbone,
        files=llm_result.files,
    )


def _get_recent_history(conversation_id: str, limit: int = 6) -> str:
    """Get recent conversation history formatted for the LLM."""
    sb = get_supabase()
    result = (
        sb.table("messages")
        .select("role, content")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    if not result.data:
        return ""

    lines = []
    for msg in result.data:
        role = msg["role"].capitalize()
        content = msg["content"][:300]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
