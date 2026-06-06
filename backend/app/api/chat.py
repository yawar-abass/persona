import json
from fastapi import APIRouter, Request,Header, HTTPException
from fastapi.responses import StreamingResponse
from groq import Groq
from app.config import settings
from app.core.persona import SYSTEM_PROMPT
from app.core.security import clean_and_validate_input
from app.services.rag_service import rag_service
from app.services.cal_service import cal_service
from datetime import datetime
import pytz
from loguru import logger


router = APIRouter()
groq_client = Groq(api_key=settings.GROQ_API_KEY)

# Define the production tool schema for Groq function calling
BOOKING_TOOL = {
    "type": "function",
    "function": {
        "name": "book_calendar_interview",
        "description": "Natively books an interview or meeting slot on Cal.com. Call this ONLY when the user explicitly provides their name, email, and preferred date/time to finalize a booking.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The full name of the recruiter, interviewer, or evaluator."
                },
                "email": {
                    "type": "string",
                    "description": "The valid email address of the attendee where the calendar invite will be sent."
                },
                "start_time": {
                    "type": "string",
                    "description": "The exact ISO 8601 UTC date-time string for the slot (e.g., '2026-06-15T10:00:00Z'). Ensure the year matches 2026."
                }
            },
            "required": ["name", "email", "start_time"]
        }
    }
}
SECRET_ROUTE = settings.VAPI_SECRET

@router.post(f"/{SECRET_ROUTE}/chat/completions")
async def chat_completions(request: Request):
  
    payload = await request.json()
    raw_messages = payload.get("messages", [])
    # 1. Sanitize incoming messages
    clean_messages = []
    for msg in raw_messages:
        clean_msg = {"role": msg.get("role"), "content": msg.get("content", "")}
        if "tool_calls" in msg: clean_msg["tool_calls"] = msg["tool_calls"]
        if "tool_call_id" in msg: clean_msg["tool_call_id"] = msg["tool_call_id"]
        if "name" in msg: clean_msg["name"] = msg["name"]
        clean_messages.append(clean_msg)

    # 2. Extract and validate the latest user message SAFELY
    user_query = ""
    for i in range(len(clean_messages) - 1, -1, -1):
        if clean_messages[i].get("role") == "user":
            user_query = clean_messages[i].get("content", "")
            safe_query = clean_and_validate_input(user_query)
            if safe_query != user_query:
                clean_messages[i]["content"] = safe_query # Safely update the exact user message
            break

    # 3. PRODUCTION FIX #1: Sliding Window Context
    MAX_HISTORY = 10
    if len(clean_messages) > MAX_HISTORY:
        clean_messages = clean_messages[-MAX_HISTORY:]
        
        # Protect against orphaned tool responses
        while clean_messages and clean_messages[0].get("role") == "tool":
            clean_messages.pop(0)
            
        # Protect against orphaned assistant tool_calls
        while clean_messages and "tool_calls" in clean_messages[0]:
            clean_messages.pop(0)

   # 4. Latency Guard: Only run RAG if they are asking about technical skills or background
    rag_context = ""
    keywords = ["project", "experience", "iit", "collabnotes", "tech", "stack", "architecture", "kotlin", "android", "ai", "ml", "research","education","background","skills"]
    if any(word in safe_query.lower() for word in keywords) and len(safe_query.split()) > 2:
        logger.debug(f"🔍 Running context retrieval for query: {safe_query}")
        rag_context = rag_service.retrieve_context(safe_query)
    # 5. Build current conversation context
    current_system_prompt = SYSTEM_PROMPT
    if rag_context:
        current_system_prompt += f"\n\n### Grounded Context (Source Data):\n{rag_context}"
        
    ist_tz = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist_tz).strftime("%A, %B %d, %Y at %I:%M %p IST")
    current_system_prompt += f"\n\n[Current Temporal Context: Right now is {current_time}. Calculate all exact UTC ISO 8601 timestamps for calendar tools based on IST.]"

    # 6. Assemble the Final Safe Array
    final_messages = [{"role": "system", "content": current_system_prompt}]
    final_messages.extend(clean_messages) # Use the safe array, DO NOT slice [-6:] here!
    try:
    # 7. Query Groq for initial tool-call check
        initial_response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=final_messages,
            tools=[BOOKING_TOOL],
            tool_choice="auto",
            temperature=0.1
        )
    except Exception as e:
        # Prevent server crash and smoothly inform the user
        def error_stream():
            yield f'data: {json.dumps({"choices": [{"delta": {"content": "Ah, apologies, my neural link is experiencing a bit of latency right now. Could you repeat that?"}}]})}\n\n'
            yield 'data: [DONE]\n\n'
        return StreamingResponse(error_stream(), media_type="text/event-stream")
    
    response_message = initial_response.choices[0].message
    tool_calls = response_message.tool_calls

    # 5. If the model determines a tool call is required, execute it natively
    if tool_calls:
        assistant_tool_message = {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": tool.id,
                    "type": "function",
                    "function": {
                        "name": tool.function.name,
                        "arguments": tool.function.arguments
                    }
                } for tool in tool_calls
            ]
        }
        final_messages.append(assistant_tool_message)
        for tool_call in tool_calls:
            if tool_call.function.name == "book_calendar_interview":
                # Natively extract the parameters determined by the model
                arguments = json.loads(tool_call.function.arguments)
                
                # Execute the real external Cal.com V2 endpoint
                booking_result = await cal_service.book_interview(
                    name=arguments.get("name"),
                    email=arguments.get("email"),
                    start_time=arguments.get("start_time")
                )
                
                # Feed the real-world operational result back into the system message chain
                # final_messages.append(response_message)
                final_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": "book_calendar_interview",
                    "content": json.dumps(booking_result)
                })
                
                # Request a final response from Groq based strictly on the execution output
                final_response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=final_messages,
                    temperature=0.3,
                    stream=True
                )
                
                # Simple generator to wrap the final text as an OpenAI-compatible stream
                def stream_text_response(text: str):
                    data = json.dumps({
                        "id": "chatcmpl-tool",
                        "choices": [{"delta": {"content": text}}]
                    })
                    yield f"data: {data}\n\n"
                    yield "data: [DONE]\n\n"
                    
                return StreamingResponse(
                    stream_text_response(final_response.choices[0].message.content), 
                    media_type="text/event-stream"
                )

    # 6. If no tool was called, fallback to streaming the standard conversational response instantly
    def generate_stream():
        try:
            stream_response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=final_messages,
                stream=True,
                temperature=0.4,
                max_tokens=300
            )
            for chunk in stream_response:
                if chunk.choices[0].delta.content is not None:
                    data = json.dumps({
                        "id": chunk.id,
                        "choices": [{"delta": {"content": chunk.choices[0].delta.content}}]
                    })
                    yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")