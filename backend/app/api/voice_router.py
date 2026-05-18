"""
Voice WebSocket Router
Handles the full voice pipeline: Audio → STT → Agent → TTS → Audio
"""

import json
import logging
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.stt_service import DeepgramSTT
from app.services.tts_service import ElevenLabsTTS
from app.agent.graph import run_agent

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/voice")
async def voice_endpoint(
    websocket: WebSocket,
    # These are injected via app.state (set in main.py)
):
    """
    Main voice pipeline WebSocket endpoint.

    Protocol:
        Client → Server:
            - {"type": "start"} — begin recording
            - Binary frames   — audio chunks (webm/opus)
            - {"type": "stop"}  — end recording

        Server → Client:
            - {"type": "transcript", "text": "..."} — user's speech text
            - {"type": "agent_text", "text": "..."}  — agent's response text
            - {"type": "audio_start"}                 — TTS audio beginning
            - Binary frames                           — mp3 audio chunks
            - {"type": "audio_end"}                   — TTS audio complete
            - {"type": "error", "message": "..."}     — error occurred
    """
    await websocket.accept()
    logger.info("WebSocket connection opened")

    # Get services from app state
    app = websocket.app
    deepgram_key = app.state.deepgram_api_key
    tts: ElevenLabsTTS = app.state.tts_service
    agent = app.state.agent

    # Per-session conversation history
    conversation_history: list[dict] = []
    stt: DeepgramSTT | None = None

    try:
        while True:
            data = await websocket.receive()

            # ── Text messages (control) ──────────────────────────
            if "text" in data:
                msg = json.loads(data["text"])
                msg_type = msg.get("type", "")

                if msg_type == "start":
                    # Start a new STT session
                    stt = DeepgramSTT(api_key=deepgram_key)
                    await stt.start()
                    logger.info("Recording started")

                elif msg_type == "stop":
                    if not stt:
                        await websocket.send_json(
                            {"type": "error", "message": "No active recording"}
                        )
                        continue

                    # ── Step 1: Finish STT and get transcript ────
                    t0 = time.perf_counter()
                    transcript = await stt.finish()
                    stt_time = time.perf_counter() - t0
                    stt = None

                    logger.info(f"STT completed in {stt_time:.2f}s: {transcript}")

                    # Send transcript to client
                    await websocket.send_json(
                        {"type": "transcript", "text": transcript}
                    )

                    if not transcript.strip():
                        await websocket.send_json(
                            {"type": "error", "message": "No speech detected"}
                        )
                        continue

                    # Add to conversation history
                    conversation_history.append(
                        {"role": "user", "content": transcript}
                    )

                    # ── Step 2: Run the agent ────────────────────
                    t1 = time.perf_counter()
                    response_text = await run_agent(
                        agent, conversation_history, transcript
                    )
                    agent_time = time.perf_counter() - t1

                    logger.info(
                        f"Agent responded in {agent_time:.2f}s: {response_text[:80]}"
                    )

                    # Add to conversation history
                    conversation_history.append(
                        {"role": "assistant", "content": response_text}
                    )

                    # Send agent text to client
                    await websocket.send_json(
                        {"type": "agent_text", "text": response_text}
                    )

                    # ── Step 3: Stream TTS audio ─────────────────
                    t2 = time.perf_counter()
                    await websocket.send_json({"type": "audio_start"})

                    chunk_count = 0
                    async for audio_chunk in tts.stream(response_text):
                        await websocket.send_bytes(audio_chunk)
                        chunk_count += 1

                    await websocket.send_json({"type": "audio_end"})
                    tts_time = time.perf_counter() - t2

                    total_time = time.perf_counter() - t0
                    logger.info(
                        f"Pipeline complete — STT: {stt_time:.2f}s, "
                        f"Agent: {agent_time:.2f}s, TTS: {tts_time:.2f}s "
                        f"({chunk_count} chunks), Total: {total_time:.2f}s"
                    )

                    # Send timing info to client (for debugging)
                    await websocket.send_json({
                        "type": "timing",
                        "stt_ms": round(stt_time * 1000),
                        "agent_ms": round(agent_time * 1000),
                        "tts_ms": round(tts_time * 1000),
                        "total_ms": round(total_time * 1000),
                    })

            # ── Binary messages (audio chunks) ───────────────────
            elif "bytes" in data:
                if stt:
                    await stt.send_audio(data["bytes"])

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        if stt:
            await stt.close()
        logger.info("WebSocket session cleaned up")
