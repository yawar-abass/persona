Markdown

# 🎙️ Yawar Abass - Voice AI Interview Agent

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)
![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)
![Groq](https://img.shields.io/badge/LLM-Groq_Llama_3.1-f55036.svg)
![Vapi](https://img.shields.io/badge/Voice-Vapi-purple.svg)

A low-latency, production-ready Voice AI Agent built to conduct technical phone screens and seamlessly schedule calendar interviews. Developed as an interactive portfolio and technical demonstration for the **AI Engineer** role at **Scaler**.

This monorepo contains a **FastAPI** backend for ultra-fast agentic reasoning and tool execution, paired with a **Next.js** frontend serving as a secure Backend-For-Frontend (BFF).

## ✨ Key Features

- **⚡ Ultra-Low Latency Voice Streaming:** Achieves human-like conversational speed by utilizing Groq's LPU inference (`llama-3.1-8b-instant`) and asynchronous chunk-streaming directly to Vapi.
- **🛠️ Native Tool Execution (Slot Filling):** Implements a robust state-machine for calendar booking. The agent securely extracts user data and interfaces directly with the **Cal.com v2 API** via `httpx` to book live meetings without hallucination.
- **🧠 Keyword-Gated RAG:** Integrates Pinecone and Google GenAI embeddings to retrieve context about my background (IIT Delhi research, CollabNotes architecture). The RAG pipeline is conditionally bypassed for casual queries to save ~500ms of latency.
- **🛡️ Production-Grade Security:** Utilizes a dynamic Secret Path routing strategy to armor the webhook endpoint against unauthorized access, while keeping frontend API keys entirely hidden.
- **📊 Structured Logging:** Implements `loguru` for beautiful, chronological terminal traces of the AI's "thought process" and network flow.

## 🏗️ Architecture Stack

| Component               | Technology            | Purpose                                                     |
| :---------------------- | :-------------------- | :---------------------------------------------------------- |
| **Voice Orchestration** | Vapi + Cartesia       | WebRTC audio streaming, ASR, and ultra-fast TTS.            |
| **Core Brain (LLM)**    | Groq (`llama-3.1-8b`) | High-speed inference and JSON tool-calling capabilities.    |
| **Backend API**         | FastAPI (Python)      | Async event loop, tool execution, and context management.   |
| **Vector Database**     | Pinecone              | Storing and retrieving detailed project/experience context. |
| **Embeddings**          | Google GenAI          | `gemini-embedding-001` for high-dimensional vectorization.  |
| **External APIs**       | Cal.com v2            | Executing real-world calendar bookings.                     |
| **Frontend/BFF**        | Next.js 14            | Client UI and secure proxy routing to the Python backend.   |

## 📂 Monorepo Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── chat.py           # Core SSE streaming and routing logic
│   │   ├── core/
│   │   │   ├── persona.py        # System prompt, guardrails, and state-machine
│   │   │   └── security.py       # Input sanitization
│   │   ├── services/
│   │   │   ├── cal_service.py    # Async Cal.com integration
│   │   │   └── rag_service.py    # Pinecone/Gemini context retrieval
│   │   ├── config.py             # Pydantic environment validation
│   │   └── main.py               # FastAPI application entrypoint
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── api/
│   │   │   └── chat/route.ts     # Next.js BFF secure proxy
│   │   └── page.tsx              # Web interface
│   └── package.json
├── .gitignore
└── README.md
🚀 Local Development Setup
1. Clone the Repository
Bash
git clone [https://github.com/yourusername/yawar-voice-agent.git](https://github.com/yourusername/yawar-voice-agent.git)
cd yawar-voice-agent
2. Backend Setup (FastAPI)
Bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
3. Frontend Setup (Next.js)
Bash
cd ../frontend
npm install
4. Environment Variables
Create a .env file in the root directory (or respective subdirectories) based on the template below:

Code snippet
# --- LLM & AI Services ---
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key

# --- Vector Database ---
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=your_index_name

# --- Integrations ---
CAL_API_KEY=your_cal_com_v2_key
CAL_EVENT_TYPE_ID=your_event_id

# --- Security ---
VAPI_SECRET=your_super_secure_webhook_path
5. Running the Application
Start the Python Backend:

Bash
cd backend
uvicorn app.main:app --reload --port 8000
Start the Next.js Frontend:

Bash
cd frontend
npm run dev
☁️ Deployment
This architecture is designed to be deployed on persistent servers (e.g., Render, Fly.io, or AWS EC2) to support long-lived Server-Sent Events (SSE).

Deploy the backend directory as a Python Web Service.

Ensure the deployment region is US-East or US-West to minimize network latency with Groq and Vapi data centers.

Update the Vapi dashboard Custom LLM URL to match the production backend URL + your VAPI_SECRET path.

Built by Yawar Abass | Candidate for AI Engineer @ Scaler
```
