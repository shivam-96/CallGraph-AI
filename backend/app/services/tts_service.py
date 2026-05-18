"""
OpenAI Streaming TTS Service
Converts text to speech using OpenAI's TTS API and yields audio chunks
as they arrive — first byte starts playing before the full audio is ready.
"""

import asyncio
import logging
import queue
import threading
from typing import AsyncGenerator
from openai import OpenAI

logger = logging.getLogger(__name__)


class ElevenLabsTTS:
    """
    Text-to-speech using OpenAI TTS streaming API.
    Class name kept as ElevenLabsTTS to avoid changing imports elsewhere.
    """

    def __init__(self, api_key: str, voice_id: str = "nova"):
        self.client = OpenAI(api_key=api_key)
        # nova = warm, natural female voice — best for Indian English
        # Options: alloy, ash, coral, echo, fable, onyx, nova, sage, shimmer
        self.voice = "nova"
        # tts-1 = fastest | tts-1-hd = highest quality (slower)
        self.model_id = "tts-1"

    async def stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Convert text to speech and yield mp3 audio chunks as they arrive.
        Uses a thread + queue so chunks are sent to the client immediately,
        dramatically reducing time-to-first-audio.
        """
        if not text.strip():
            return

        logger.info(f"TTS generating for: {text[:80]}...")

        chunk_queue: queue.Queue = queue.Queue()

        def _stream_in_thread():
            """Run sync OpenAI streaming in a background thread."""
            try:
                with self.client.audio.speech.with_streaming_response.create(
                    model=self.model_id,
                    voice=self.voice,
                    input=text,
                    response_format="mp3",
                    speed=1.0,
                ) as response:
                    for chunk in response.iter_bytes(chunk_size=2048):
                        if chunk:
                            chunk_queue.put(chunk)
            except Exception as e:
                logger.error(f"TTS thread error: {e}")
                chunk_queue.put(e)  # Signal error
            finally:
                chunk_queue.put(None)  # Signal done

        # Start streaming in background thread so we don't block the event loop
        thread = threading.Thread(target=_stream_in_thread, daemon=True)
        thread.start()

        # Yield chunks as they arrive from the queue
        loop = asyncio.get_event_loop()
        while True:
            chunk = await loop.run_in_executor(None, chunk_queue.get)
            if chunk is None:
                break  # Done
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk

        logger.info("TTS streaming complete")
