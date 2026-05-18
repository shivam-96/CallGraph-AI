"""
Deepgram Streaming STT Service
Connects to Deepgram's WebSocket API for real-time speech-to-text.
Audio chunks are forwarded as they arrive for minimum latency.
"""

import asyncio
import json
import logging
import websockets

logger = logging.getLogger(__name__)


class DeepgramSTT:
    """Streaming speech-to-text using Deepgram's live WebSocket API."""

    def __init__(self, api_key: str, language: str = "en-IN"):
        self.api_key = api_key
        self.language = language
        self.ws = None
        self.transcript_parts: list[str] = []
        self._receiver_task: asyncio.Task | None = None
        self._done_event = asyncio.Event()

    async def start(self):
        """Open a streaming connection to Deepgram."""
        url = (
            "wss://api.deepgram.com/v1/listen"
            f"?model=nova-2"
            f"&language={self.language}"
            "&smart_format=true"
            "&interim_results=false"
            "&endpointing=150"
        )
        headers = {"Authorization": f"Token {self.api_key}"}

        self.transcript_parts = []
        self._done_event.clear()

        try:
            self.ws = await websockets.connect(url, additional_headers=headers)
            self._receiver_task = asyncio.create_task(self._receive_loop())
            logger.info("Deepgram STT connection opened")
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            raise

    async def _receive_loop(self):
        """Listen for transcript results from Deepgram."""
        try:
            async for msg in self.ws:
                data = json.loads(msg)
                msg_type = data.get("type", "")

                if msg_type == "Results":
                    channel = data.get("channel", {})
                    alternatives = channel.get("alternatives", [{}])
                    transcript = alternatives[0].get("transcript", "")
                    is_final = data.get("is_final", False)

                    if is_final and transcript.strip():
                        self.transcript_parts.append(transcript.strip())
                        logger.debug(f"STT partial: {transcript.strip()}")

                elif msg_type == "Metadata":
                    logger.debug(f"Deepgram metadata: {data}")

        except websockets.exceptions.ConnectionClosed:
            logger.debug("Deepgram connection closed")
        except Exception as e:
            logger.error(f"Deepgram receive error: {e}")
        finally:
            self._done_event.set()

    async def send_audio(self, audio_bytes: bytes):
        """Forward an audio chunk to Deepgram."""
        if self.ws:
            try:
                await self.ws.send(audio_bytes)
            except Exception as e:
                logger.error(f"Error sending audio to Deepgram: {e}")

    async def finish(self) -> str:
        """Signal end of audio and return the full transcript."""
        if self.ws:
            try:
                # Tell Deepgram we're done sending audio
                await self.ws.send(json.dumps({"type": "CloseStream"}))
            except Exception:
                pass

        # Wait for receiver to finish processing (max 3 seconds)
        try:
            await asyncio.wait_for(self._done_event.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            logger.warning("Deepgram receiver timed out")

        await self.close()
        full_transcript = " ".join(self.transcript_parts)
        logger.info(f"Final transcript: {full_transcript}")
        return full_transcript

    async def close(self):
        """Clean up the connection."""
        if self._receiver_task and not self._receiver_task.done():
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass

        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
