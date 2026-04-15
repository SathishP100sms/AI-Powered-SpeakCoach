# main.py

import io
import logging
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, field_validator

from model import VoiceAssistant
from utils import get_config

# ── Logging ───────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

# ── API key validation at startup ─────────────────────
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")

# ── Session store ─────────────────────────────────────
# In production replace with Redis or a proper cache with TTL
assistants: dict[str, VoiceAssistant] = {}

VALID_MODES = {"conversation", "grammar", "interview"}
MAX_SESSIONS = 500          # guard against unbounded memory growth
MAX_AUDIO_MB = 10           # reject uploads larger than 10 MB


# ── Lifespan (startup / shutdown) ─────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SpeakCoach API starting up…")
    yield
    logger.info("SpeakCoach API shutting down. Sessions: %d", len(assistants))
    assistants.clear()


# ── App ───────────────────────────────────────────────
app = FastAPI(
    title="SpeakCoach AI",
    description="AI-powered Spoken English Coach — text chat, voice chat, and TTS.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-User-Text", "X-AI-Text", "X-Session-Id"],
)


# ── Request models ────────────────────────────────────
class ChatRequest(BaseModel):
    text: str
    mode: str = "conversation"
    session_id: str | None = None

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}")
        return v

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be empty")
        if len(v) > 2000:
            raise ValueError("text must be 2000 characters or fewer")
        return v


class TTSRequest(BaseModel):
    text: str
    session_id: str | None = None
    mode: str = "conversation"


# ── Session helper ────────────────────────────────────
def get_or_create_assistant(session_id: str, mode_name: str) -> VoiceAssistant:
    """
    Return the existing VoiceAssistant for this session,
    creating one if needed. Also updates the mode if it changed.
    """
    mode_config = get_config(mode_name)

    if session_id not in assistants:
        if len(assistants) >= MAX_SESSIONS:
            # Evict the oldest session (simple FIFO)
            oldest = next(iter(assistants))
            del assistants[oldest]
            logger.warning("Session limit reached. Evicted session %s", oldest)

        assistants[session_id] = VoiceAssistant(API_KEY, mode_config, mode_name)
        logger.info("New session created: %s (mode=%s)", session_id, mode_name)

    else:
        assistants[session_id].update_mode(mode_config, mode_name)

    return assistants[session_id]


# ── Routes ────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "SpeakCoach AI is running 🎤"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "active_sessions": len(assistants)}


# ── Text chat ─────────────────────────────────────────
@app.post("/chat", tags=["Chat"])
async def chat(req: ChatRequest):
    try:
        session_id = req.session_id or str(uuid.uuid4())
        assistant = get_or_create_assistant(session_id, req.mode)
        reply = assistant.ask_llm(req.text)
        return {"text": reply, "session_id": session_id}

    except Exception as e:
        logger.exception("Error in /chat")
        raise HTTPException(status_code=500, detail=str(e))


# ── Speech-to-text ────────────────────────────────────
@app.post("/speech-to-text", tags=["Voice"])
async def speech_to_text(
    file: UploadFile = File(...),
    mode: str = Query(default="conversation"),
    session_id: str | None = Query(default=None),
):
    _check_audio_size(file)
    try:
        session_id = session_id or str(uuid.uuid4())
        assistant = get_or_create_assistant(session_id, mode)
        audio_bytes = await file.read()
        text = assistant.transcribe_audio(audio_bytes)
        return {"text": text, "session_id": session_id}

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Error in /speech-to-text")
        raise HTTPException(status_code=500, detail=str(e))


# ── TTS ───────────────────────────────────────────────
@app.post("/tts", tags=["Voice"])
async def tts(req: TTSRequest):
    try:
        session_id = req.session_id or str(uuid.uuid4())
        assistant = get_or_create_assistant(session_id, req.mode)
        audio_bytes = await assistant.text_to_speech(req.text)

        if not audio_bytes:
            raise HTTPException(status_code=500, detail="TTS produced no audio.")

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/wav",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in /tts")
        raise HTTPException(status_code=500, detail=str(e))


# ── Full voice pipeline ───────────────────────────────
@app.post("/voice-chat", tags=["Voice"])
async def voice_chat(
    file: UploadFile = File(...),
    mode: str = Query(default="conversation"),
    session_id: str | None = Query(default=None),
):
    _check_audio_size(file)
    try:
        session_id = session_id or str(uuid.uuid4())
        assistant = get_or_create_assistant(session_id, mode)

        # 1. STT
        audio_bytes = await file.read()
        user_text = assistant.transcribe_audio(audio_bytes)

        if not user_text:
            raise HTTPException(
                status_code=422,
                detail="Could not transcribe audio. Please speak clearly and try again.",
            )

        # 2. LLM
        ai_text = assistant.ask_llm(user_text)

        # 3. TTS
        audio_response = await assistant.text_to_speech(ai_text)

        return StreamingResponse(
            io.BytesIO(audio_response),
            media_type="audio/wav",
            headers={
                "X-User-Text":  user_text,
                "X-AI-Text":    ai_text,
                "X-Session-Id": session_id,
            },
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Error in /voice-chat")
        raise HTTPException(status_code=500, detail=str(e))


# ── Reset session ─────────────────────────────────────
@app.delete("/session/{session_id}", tags=["Session"])
def delete_session(session_id: str):
    if session_id in assistants:
        del assistants[session_id]
        return {"message": f"Session {session_id} deleted."}
    raise HTTPException(status_code=404, detail="Session not found.")


# ── Helpers ───────────────────────────────────────────
def _check_audio_size(file: UploadFile) -> None:
    """Reject files that declare a content-length above the limit."""
    content_length = file.size  # available in Starlette ≥ 0.20
    if content_length and content_length > MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Audio file too large. Maximum size is {MAX_AUDIO_MB} MB.",
        )
