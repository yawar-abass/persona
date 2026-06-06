from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router

app = FastAPI(
    title="Scaler AI Persona Brain",
    description="Unified backend for Voice Agent and Next.js Chat Interface",
    version="1.0.0"
)

# Crucial for allowing your Next.js frontend to hit this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint (Useful for Koyeb/Render to know the app is alive)
@app.get("/")
async def root():
    return {"status": "online", "message": "Yawar Abass AI Persona is active."}

# Mount the unified chat router
app.include_router(chat_router, prefix="/api", tags=["chat"])

# if __name__ == "__main__":
#     import uvicorn
#     # Start the server on port 8000
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)