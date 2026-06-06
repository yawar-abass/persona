# 🎙️ Voice AI Interview Agent

> **Production-ready Voice AI Agent for conducting technical interviews and scheduling meetings in real time.**

---

## 🚀 Overview

The Voice AI Interview Agent is a low-latency, production-ready AI system designed to conduct technical phone screens, answer candidate questions, and schedule interviews automatically.

The project combines a **FastAPI** backend for agent orchestration and tool execution with a **Next.js** frontend that acts as a secure Backend-for-Frontend (BFF).

Built as a technical demonstration for an AI Engineer role, the system showcases:

- Real-time conversational voice agents
- Tool-calling and workflow automation
- Retrieval-Augmented Generation (RAG)
- Native calendar scheduling
- Production-grade security and state management

---

## ✨ Features

- ⚡ **Ultra-Low Latency Voice**  
  Powered by Groq's high-speed LPU inference engine. Streams responses in real time for natural, interruptible conversations.

- 🛠️ **Intelligent Tool Calling**  
  Uses structured tool execution instead of relying on LLM hallucinations. Collects required information through conversational slot-filling.

- 🧠 **Semantic RAG**  
  Stores portfolio, project, and experience data in Pinecone. Uses Google Gemini embeddings for semantic search, dynamically gated to reduce latency.

- 📅 **Automated Scheduling**  
  Integrates directly with Cal.com v2 API. Checks live availability and provisions real meetings autonomously.

- 🔒 **Production-Grade Security**  
  Hidden backend endpoints, secure webhook routing, and isolated API key handling through a proxy architecture.

- 📊 **Structured Observability**  
  Centralized logging using Loguru for clear tracing of tool execution, RAG hits, and API interactions.

---

## 🏗️ Tech Stack

| Layer               | Technology                  |
| ------------------- | --------------------------- |
| **Voice Platform**  | Vapi + Cartesia             |
| **LLM Engine**      | Groq (Llama 3.1 8B Instant) |
| **Backend**         | Python, FastAPI, `uv`       |
| **Frontend**        | React, Next.js 14           |
| **Vector Database** | Pinecone                    |
| **Embeddings**      | Google Gemini               |
| **Scheduling**      | Cal.com v2 REST API         |
| **Observability**   | Loguru, HTTPX               |

---

## 📂 Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── chat.py
│   │   ├── core/
│   │   │   ├── persona.py
│   │   │   └── security.py
│   │   ├── services/
│   │   │   ├── cal_service.py
│   │   │   └── rag_service.py
│   │   ├── config.py
│   │   └── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── api/
│   │   │   └── chat/route.ts
│   │   └── page.tsx
│   └── package.json
│
└── README.md
```

---

## ⚙️ Local Development

### 1. Clone the Repository

```bash
git clone https://github.com/yawar-abass/persona.git
cd persona
```

### 2. Backend Setup (Using `uv`)

This project uses `uv`, an extremely fast Python package installer and dependency resolver.

```bash
cd backend
uv sync

```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Environment Variables

Create a `.env` file inside the `backend` directory:

```env
# LLM & AI Services
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key

# Vector Database
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX_NAME=your_index_name

# Calendar Integration (Cal.com v2)
CAL_API_KEY=your_cal_api_key
CAL_EVENT_TYPE_ID=your_event_id

# Security
VAPI_SECRET=your_secure_webhook_route
```

---

## ▶️ Running the Application

### Start Backend

```bash
cd backend
uv run fastapi dev
```

Backend runs at:

```text
http://localhost:8000
```

### Start Frontend

```bash
cd frontend
npm run dev
```

Frontend runs at:

```text
http://localhost:3000
```

---

---

## 👨‍💻 Author

### Yawar Abass

**Full-Stack Developer • AI Enthusiast • AI Engineer Candidate**

Built to demonstrate practical applications of:

- Agentic AI Systems
- Retrieval-Augmented Generation (RAG)
- Production AI Engineering
- Voice AI Workflows
- Tool-Calling Architectures

---

## ⭐ Support

If you found this project useful or interesting, consider giving it a **star** on GitHub.

Your support helps showcase the project and motivates future improvements.
