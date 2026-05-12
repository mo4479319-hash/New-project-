"""
LLM integration using Google Gemini.
Handles intent classification, website creation, and website editing.
"""

import json
import re
from typing import Optional

import google.generativeai as genai

from app.core.config import get_settings
from app.core.prompts import (
    INTENT_CLASSIFICATION_PROMPT,
    WEBSITE_CREATE_SYSTEM_PROMPT,
    WEBSITE_EDIT_SYSTEM_PROMPT,
)
from app.models.schemas import IntentClassification, ParsedLLMResponse

# Model to use (Gemini 2.0 Flash is free tier)
MODEL_NAME = "gemini-2.0-flash"


def _get_model(system_instruction: Optional[str] = None) -> genai.GenerativeModel:
    settings = get_settings()
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_instruction,
    )


async def classify_intent(message: str, history: str = "") -> IntentClassification:
    """Classify user message intent: create_website, update_website, or general."""
    model = _get_model()
    prompt = INTENT_CLASSIFICATION_PROMPT.format(message=message, history=history)

    response = await model.generate_content_async(prompt)
    text = response.text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
        return IntentClassification(
            intent=data.get("intent", "general"),
            response=data.get("response", ""),
        )
    except json.JSONDecodeError:
        return IntentClassification(intent="general", response=text[:200])


async def create_website(business_context: str) -> ParsedLLMResponse:
    """Generate a new website from a business description."""
    model = _get_model(system_instruction=WEBSITE_CREATE_SYSTEM_PROMPT)
    response = await model.generate_content_async(business_context)
    return _parse_llm_response(response.text)


async def edit_website(
    user_message: str,
    current_backbone: dict,
    current_files: list[dict],
) -> ParsedLLMResponse:
    """Edit an existing website based on user instructions."""
    model = _get_model(system_instruction=WEBSITE_EDIT_SYSTEM_PROMPT)

    # Build context with current state
    files_text = ""
    for f in current_files:
        files_text += f"\n=== CURRENT FILE: {f['file_path']} ===\n{f['content']}\n=== END CURRENT FILE ===\n"

    prompt = f"""Current website backbone:
```json
{json.dumps(current_backbone, indent=2)}
```

Current website files:
{files_text}

User's edit request: {user_message}
"""
    response = await model.generate_content_async(prompt)
    return _parse_llm_response(response.text)


def _parse_llm_response(text: str) -> ParsedLLMResponse:
    """Parse LLM response to extract description, files, and backbone."""
    # Extract files
    files = []
    file_pattern = r"=== FILE: (.+?) ===\n(.*?)\n=== END FILE ==="
    for match in re.finditer(file_pattern, text, re.DOTALL):
        files.append({
            "file_path": match.group(1).strip(),
            "content": match.group(2).strip(),
        })

    # Extract backbone
    backbone = {}
    backbone_pattern = r"=== BACKBONE ===\n(.*?)\n=== END BACKBONE ==="
    backbone_match = re.search(backbone_pattern, text, re.DOTALL)
    if backbone_match:
        raw = backbone_match.group(1).strip()
        # Strip markdown fences if LLM wraps it
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        try:
            backbone = json.loads(raw)
        except json.JSONDecodeError:
            pass

    # Extract description (everything before the first file marker)
    desc_end = text.find("=== FILE:")
    if desc_end == -1:
        desc_end = text.find("=== BACKBONE")
    description = text[:desc_end].strip() if desc_end > 0 else text[:200].strip()

    return ParsedLLMResponse(
        description=description,
        files=files,
        backbone=backbone,
    )
