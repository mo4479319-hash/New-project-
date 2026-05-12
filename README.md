# AI Website Builder

A simplified AI-powered website creation and management system. Users chat with an AI to create and edit websites for their businesses.

## Architecture

- **Backend**: Python + FastAPI
- **Database**: Supabase (PostgreSQL)
- **Auth**: Supabase Auth (JWT)
- **AI/LLM**: Google Gemini (free tier)
- **Frontend**: React (consumes these APIs)

## Core Concept: The Backbone

The "backbone" is a JSON document that represents a website's content and structure. It's template-agnostic — the same backbone can render as HTML, React, or any other format.

```json
{
  "business": { "name": "...", "phone": "...", "email": "..." },
  "branding": { "primaryColor": "#...", "logo": "..." },
  "sections": [
    { "type": "hero", "headline": "...", "image": "..." },
    { "type": "about", "text": "..." },
    { "type": "contact", "phone": "...", "email": "..." }
  ]
}
```

Every edit creates a **new configuration row** (immutable history). This enables undo, audit trails, and conversation-linked changes.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy env template and fill in your keys
cp .env.example .env

# 3. Run Supabase migrations (or apply via Supabase dashboard)
# See supabase/migrations/

# 4. Start the server
uvicorn app.main:app --reload
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/businesses` | Create a business |
| GET | `/api/businesses/{id}` | Get business details |
| POST | `/api/chat` | Chat to create/edit website |
| GET | `/api/websites/{business_id}` | Get latest website config |
| GET | `/api/websites/{business_id}/history` | Get config version history |
| POST | `/api/websites/{business_id}/publish` | Promote staging to production |
| POST | `/api/websites/{business_id}/undo` | Revert to previous version |

## Project Structure

```
app/
  main.py              # FastAPI app entry point
  core/
    config.py          # Settings & Supabase client
    prompts.py         # LLM system prompts
  api/
    businesses.py      # Business CRUD endpoints
    chat.py            # Chat endpoint (create/edit website)
    websites.py        # Website config endpoints
  models/
    schemas.py         # Pydantic request/response models
  services/
    llm.py             # LLM integration (Gemini)
    website.py         # Website backbone logic
    chat.py            # Chat orchestration
supabase/
  migrations/
    001_initial.sql    # Database schema
```

## Environment Variables

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
GEMINI_API_KEY=your-gemini-api-key
```
