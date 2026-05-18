# CallGraph AI 🎙️

CallGraph AI is an advanced, real-time voice-driven AI agent designed for ultra-low latency conversational interactions. It processes streaming audio, understands context, executes tools via an agentic workflow, and replies with a highly realistic synthesized voice—all within milliseconds.

---

## 🏗️ Architecture & Technology Stack

The system is built on a streaming WebSocket architecture to ensure zero blocking and minimum time-to-first-byte (TTFB). Below is a deep dive into the core components driving the backend:

### 1. Real-Time Communication (FastAPI & WebSockets)
- **FastAPI**: Serves as the robust, asynchronous backend framework.
- **WebSockets**: We maintain a persistent bidirectional connection between the client and server. Audio chunks are sent continuously as the user speaks, and AI responses are streamed back chunk-by-chunk.

### 2. Speech-to-Text / STT (Deepgram)
- **Service**: Deepgram Live API.
- **Model**: `nova-2`.
- **Why**: Deepgram is currently the fastest STT provider on the market. It processes audio streams on the fly with endpointing (silence detection) optimized down to 150ms. This allows the backend to know exactly when the user stops speaking without waiting for a manual trigger.

### 3. Agentic Brain (LangGraph & OpenAI)
- **Framework**: LangGraph.
- **LLM**: OpenAI `gpt-4o-mini`.
- **How it works**: Instead of simple chat completions, the intelligence is modeled as a ReAct (Reason + Act) agent. 
  - **Dynamic Context**: The agent's identity, behavior rules, and domain knowledge are dynamically injected via YAML configurations (`identity.yaml`, `context.yaml`).
  - **Tools**: The agent can autonomously decide to use tools (like web search, calculator, or datetime fetcher) before formulating its response. 
  - **Optimization**: The model is tuned with a low temperature (`0.3`) and a strict max token limit (`150`) to ensure fast, concise, conversational replies suitable for voice.

### 4. Text-to-Speech / TTS (OpenAI)
- **Service**: OpenAI TTS API.
- **Model / Voice**: `tts-1` / `nova` (a warm, highly realistic female voice).
- **Streaming Implementation**: Audio generation does not wait for the entire text response. Using background threading and Python's `asyncio` queues, the TTS engine generates raw MP3 byte chunks and immediately streams them over the WebSocket. This means the client starts hearing the AI speak *while* the rest of the sentence is still being generated.

### 5. Frontend (Preview)
- Currently, the frontend is a lightweight **Vanilla JavaScript** implementation using the browser's `MediaRecorder API` to capture microphone input and `AudioObjectURL` to play the incoming streams.
- **Future Roadmap**: The frontend is slated for a full rewrite using **React.js** for a more robust, component-driven user interface and better state management.

---

## 📂 Backend Structure

```text
backend/
├── app/
│   ├── agent/         # LangGraph ReAct agent logic and prompt building
│   ├── api/           # FastAPI routers (WebSocket endpoints)
│   ├── services/      # External integrations (Deepgram STT, OpenAI TTS)
│   └── tools/         # Tools the AI agent can invoke (calculator, search, etc.)
├── config/            # YAML files defining the agent's identity and knowledge
├── .env               # API Keys (OpenAI, Deepgram)
├── test_keys.py       # Utility script to validate API keys
└── main.py            # Application entry point
```

---

## 🚀 Getting Started

If you are a developer looking to spin up the environment quickly:

1. **Environment Setup**:
   Ensure your API keys are added to `backend/.env`. You can validate your setup by running:
   ```bash
   cd backend
   python test_keys.py
   ```

2. **Run the Server**:
   Start the FastAPI application. (The static vanilla JS frontend is served automatically).
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Interact**:
   Open `http://localhost:8000` in your browser, allow microphone access, and hold the button to talk to the AI.
