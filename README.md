# 🎙️ Voice AI Interview Agent

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-00a393.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/Next.js-14+-black.svg" alt="Next.js">
  <img src="https://img.shields.io/badge/LLM-Groq_Llama_3.1-f55036.svg" alt="Groq">
  <img src="https://img.shields.io/badge/Voice-Vapi-purple.svg" alt="Vapi">
</p>

<p align="center">
  <strong>Production-ready Voice AI Agent for conducting technical interviews and scheduling meetings in real time.</strong>
</p>

---

## 🚀 Overview

Voice AI Interview Agent is a low-latency, production-ready AI system designed to conduct technical phone screens, answer candidate questions, and schedule interviews automatically.

The project combines a **FastAPI backend** for agent orchestration and tool execution with a **Next.js frontend** that acts as a secure Backend-for-Frontend (BFF).

Built as a technical demonstration for an AI Engineer role, the system showcases:

- Real-time voice conversations
- Tool-calling and workflow automation
- Retrieval-Augmented Generation (RAG)
- Calendar scheduling
- Production-grade security practices

---

## ✨ Features

### ⚡ Ultra-Low Latency Voice Conversations

- Powered by Groq's high-speed inference engine.
- Streams responses in real time for natural conversations.
- Optimized for minimal response delay.

### 🛠️ Intelligent Tool Calling

- Uses structured tool execution instead of relying on LLM hallucinations.
- Collects required information through slot-filling.
- Books interviews directly through Cal.com APIs.

### 🧠 Retrieval-Augmented Generation (RAG)

- Stores portfolio, project, and experience data in Pinecone.
- Uses Google Gemini embeddings for semantic search.
- Dynamically enables RAG only when relevant to reduce latency.

### 📅 Automated Interview Scheduling

- Integrates with Cal.com v2.
- Checks availability and creates real meetings automatically.
- Handles scheduling workflows through agent reasoning.

### 🔒 Production-Grade Security

- Hidden backend endpoints.
- Secret webhook routing.
- Secure API key handling through backend proxy architecture.

### 📊 Structured Observability

- Centralized logging using Loguru.
- Clear tracing of tool execution and API interactions.
- Easier debugging and monitoring.

---

## 🏗️ Tech Stack

| Layer           | Technology       |
| --------------- | ---------------- |
| Voice Platform  | Vapi + Cartesia  |
| LLM             | Groq (Llama 3.1) |
| Backend         | FastAPI          |
| Frontend        | Next.js 14       |
| Vector Database | Pinecone         |
| Embeddings      | Google Gemini    |
| Scheduling      | Cal.com v2       |
| Logging         | Loguru           |
| HTTP Client     | HTTPX            |

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
├── .gitignore
└── README.md
```

---

## ⚙️ Local Development

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/voice-ai-interview-agent.git

cd voice-ai-interview-agent
```

### 2. Backend Setup

```bash
cd backend

python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd ../frontend

npm install
```

---

## 🔑 Environment Variables

Create a `.env` file and configure the following values:

```env
# LLM & AI Services
GROQ_API_KEY=
GEMINI_API_KEY=

# Vector Database
PINECONE_API_KEY=
PINECONE_INDEX_NAME=

# Calendar Integration
CAL_API_KEY=
CAL_EVENT_TYPE_ID=

# Security
VAPI_SECRET=
```

---

## ▶️ Running the Application

### Start Backend

```bash
cd backend

uvicorn app.main:app --reload --port 8000
```

### Start Frontend

```bash
cd frontend

npm run dev
```

Application URLs:

```text
Frontend: http://localhost:3000
Backend:  http://localhost:8000
```

---

## ☁️ Deployment

This architecture is optimized for deployment on persistent servers that support long-lived streaming connections.

### Recommended Platforms

- Render
- Fly.io
- AWS EC2
- DigitalOcean

### Deployment Steps

1. Deploy the `backend` directory as a Python web service.
2. Configure all environment variables.
3. Deploy the `frontend` directory as a Next.js application.
4. Update your Vapi Custom LLM endpoint to point to the production backend URL.
5. Keep backend endpoints protected using the configured secret route.

### Performance Recommendation

Deploy infrastructure in **US-East** or **US-West** regions to minimize latency with Groq and Vapi services.

---

## 🎯 Key Engineering Highlights

- Real-time voice AI orchestration
- Async FastAPI architecture
- Streaming response generation
- Agentic tool execution
- Production-grade RAG implementation
- Calendar workflow automation
- Secure Backend-for-Frontend design
- Low-latency optimization techniques

---

## 👨‍💻 Author

**Yawar Abass**

Frontend Developer • AI Enthusiast • AI Engineer Candidate

Built to demonstrate practical applications of:

- Agentic AI Systems
- Voice Interfaces
- RAG Architectures
- Tool Calling Workflows
- Production AI Engineering

---

⭐ If you found this project interesting, consider giving it a star.
