"""
AI Website Builder — FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.businesses import router as businesses_router
from app.api.chat import router as chat_router
from app.api.websites import router as websites_router

app = FastAPI(
    title="AI Website Builder",
    description="Chat with AI to create and manage websites for your business.",
    version="1.0.0",
)

# CORS — allow React frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(businesses_router)
app.include_router(chat_router)
app.include_router(websites_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
