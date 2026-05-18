"""
CallGraph AI — FastAPI Application Entry Point
Initializes services, loads config, and starts the server.
"""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.voice_router import router as voice_router
from app.agent.graph import create_agent
from app.services.tts_service import ElevenLabsTTS

# ─── Load Environment ────────────────────────────────────────────

# Load .env from backend directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pFZP5JQG7iQjIQuC4Bku")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

# ─── Logging ─────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── FastAPI App ─────────────────────────────────────────────────

app = FastAPI(
    title="CallGraph AI",
    description="Real-time voice AI agent with configurable identity and context",
    version="0.1.0",
)

# CORS — allow frontend (served separately or same origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Startup ─────────────────────────────────────────────────────


@app.on_event("startup")
async def startup():
    """Initialize all services on startup."""
    logger.info("=" * 50)
    logger.info("  CallGraph AI starting up...")
    logger.info("=" * 50)

    # Validate API keys
    missing = []
    if not OPENAI_API_KEY:
        missing.append("OPENAI_API_KEY")
    if not ELEVENLABS_API_KEY:
        missing.append("ELEVENLABS_API_KEY")
    if not DEEPGRAM_API_KEY:
        missing.append("DEEPGRAM_API_KEY")

    if missing:
        logger.warning(f"Missing API keys: {', '.join(missing)}")
        logger.warning("Add them to backend/.env file")

    # Create agent
    agent, system_prompt = create_agent(OPENAI_API_KEY)
    app.state.agent = agent
    logger.info("Agent initialized")

    # Create TTS service (now uses OpenAI TTS — no ElevenLabs account needed)
    app.state.tts_service = ElevenLabsTTS(
        api_key=OPENAI_API_KEY,
    )
    logger.info(f"TTS initialized (voice: {ELEVENLABS_VOICE_ID})")

    # Store Deepgram key for per-session STT connections
    app.state.deepgram_api_key = DEEPGRAM_API_KEY

    logger.info("All services ready!")
    logger.info("=" * 50)


# ─── Routes ──────────────────────────────────────────────────────

# Voice WebSocket
app.include_router(voice_router)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")

    @app.get("/")
    async def serve_frontend():
        """Serve the frontend index.html."""
        return FileResponse(str(FRONTEND_DIR / "index.html"))


# Health check
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "services": {
            "openai": bool(OPENAI_API_KEY),
            "elevenlabs": bool(ELEVENLABS_API_KEY),
            "deepgram": bool(DEEPGRAM_API_KEY),
        },
    }
