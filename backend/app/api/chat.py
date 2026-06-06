import json
from fastapi import APIRouter, Request, HTTPException
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
    safe_query = ""
    for i in range(len(clean_messages) - 1, -1, -1):
        if clean_messages[i].get("role") == "user":
            user_query = clean_messages[i].get("content", "")
            safe_query = clean_and_validate_input(user_query)
            if safe_query != user_query:
                clean_messages[i]["content"] = safe_query
            break

    # 3. PRODUCTION FIX: Sliding Window Context
    MAX_HISTORY = 10
    if len(clean_messages) > MAX_HISTORY:
        clean_messages = clean_messages[-MAX_HISTORY:]
        while clean_messages and clean_messages[0].get("role") == "tool":
            clean_messages.pop(0)
        while clean_messages and "tool_calls" in clean_messages[0]:
            clean_messages.pop(0)

    # 4. Latency Guard (Keyword RAG)
    rag_context = ""
    keywords = ["project", "experience", "iit", "collabnotes", "tech", "stack", "architecture", "kotlin", "android", "ai", "ml", "research", "education", "background", "skills"]
    if any(word in safe_query.lower() for word in keywords) and len(safe_query.split()) > 2:
        logger.debug(f"🔍 Running RAG for: {safe_query}")
        rag_context = rag_service.retrieve_context(safe_query)

    # 5. Build Context
    current_system_prompt = SYSTEM_PROMPT
    if rag_context:
        current_system_prompt += f"\n\n### Grounded Context:\n{rag_context}"
        
    ist_tz = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist_tz).strftime("%A, %B %d, %Y at %I:%M %p IST")
    current_system_prompt += f"\n\n[Current Temporal Context: Right now is {current_time}. Calculate all exact UTC timestamps for tools based on IST.]"

    final_messages = [{"role": "system", "content": current_system_prompt}]
    final_messages.extend(clean_messages) 

    # 6. THE UNIFIED STREAMING GENERATOR
    async def unified_streaming_generator():
        try:
            stream_response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=final_messages,
                tools=[BOOKING_TOOL],
                tool_choice="auto",
                temperature=0.2,
                stream=True
            )

            tool_calls_accumulators = {}
            is_tool_call = False
            has_yielded_filler = False

            # Iterate through the chunks as they arrive in milliseconds
            for chunk in stream_response:
                delta = chunk.choices[0].delta

                # --- PATH A: GROQ IS CALLING A TOOL ---
                if delta.tool_calls:
                    is_tool_call = True
                    
                    # IMMEDIATELY yield the filler phrase to satisfy Vapi's timeout
                    if not has_yielded_filler:
                        yield f"data: {json.dumps({'id': 'filler', 'choices': [{'delta': {'content': 'Got it. Let me check the calendar right now...'}}]})}\n\n"
                        has_yielded_filler = True

                    for tc in delta.tool_calls:
                        index = tc.index
                        if index not in tool_calls_accumulators:
                            tool_calls_accumulators[index] = {
                                "id": tc.id,
                                "name": tc.function.name if tc.function else "book_calendar_interview",
                                "arguments": ""
                            }
                        if tc.function and tc.function.arguments:
                            tool_calls_accumulators[index]["arguments"] += tc.function.arguments
                    continue 

                # --- PATH B: GROQ IS JUST TALKING (Instant Stream) ---
                if delta.content and not is_tool_call:
                    yield f"data: {json.dumps({'id': chunk.id, 'choices': [{'delta': {'content': delta.content}}]})}\n\n"

            # --- EXECUTE THE TOOL (Only triggers if Path A happened) ---
            if is_tool_call:
                # Reconstruct the tool call object
                formatted_tool_calls = []
                for tc in tool_calls_accumulators.values():
                    formatted_tool_calls.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]}
                    })

                final_messages.append({"role": "assistant", "tool_calls": formatted_tool_calls})

                # Execute with The Bouncer
                for tc in formatted_tool_calls:
                    if tc["function"]["name"] == "book_calendar_interview":
                        try:
                            arguments = json.loads(tc["function"]["arguments"])
                        except Exception:
                            arguments = {}

                        email = arguments.get("email", "")
                        name = arguments.get("name", "")
                        start_time = arguments.get("start_time", "")

                        if not email or not name or not start_time:
                            logger.warning("⚠️ LLM tried to book without all data.")
                            booking_result = {"success": False, "message": "SYSTEM ERROR: You cannot book yet. Politely ask the user for their missing info."}
                        else:
                            booking_result = await cal_service.book_interview(name=name, email=email, start_time=start_time)

                        final_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": "book_calendar_interview",
                            "content": json.dumps(booking_result)
                        })

                # Stream the final post-tool result
                tool_result_stream = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=final_messages,
                    temperature=0.3,
                    stream=True
                )
                for chunk in tool_result_stream:
                    if chunk.choices[0].delta.content is not None:
                        yield f"data: {json.dumps({'id': chunk.id, 'choices': [{'delta': {'content': chunk.choices[0].delta.content}}]})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"🚨 Stream Error: {e}")
            yield f"data: {json.dumps({'id': 'err', 'choices': [{'delta': {'content': 'My apologies, I had a brief connection issue. Could you repeat that?'}}]})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(unified_streaming_generator(), media_type="text/event-stream")