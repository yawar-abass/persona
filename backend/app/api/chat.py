import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from groq import Groq
from app.config import settings
from app.core.persona import SYSTEM_PROMPT
from app.core.security import clean_and_validate_input
from app.services.rag_service import rag_service
from app.services.cal_service import cal_service
from datetime import datetime, timedelta
import pytz
from loguru import logger
import re


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
                 "description": "The valid email address of the attendee. CRITICAL FOR VOICE: You must aggressively clean phonetic spellings before outputting. Remove all spaces between spelled letters. Convert 'underscore' to '_', 'dash' to '-', 'at' to '@', and 'dot' to '.'. Example: 'j o h n underscore d o e at g mail dot com' -> 'john_doe@gmail.com'."
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


CHECK_AVAILABILITY_TOOL = {
    "type": "function",
    "function": {
        "name": "check_calendar_availability",
        "description": "Checks the user's real calendar for open, available time slots on a specific date. Use this BEFORE attempting to book a meeting so you can propose real times to the caller.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "The exact date to check for open slots in YYYY-MM-DD format (e.g., '2026-06-15'). Ensure the year is 2026."
                }
            },
            "required": ["date"]
        }
    }
}


SECRET_ROUTE = settings.VAPI_SECRET

def sanitize_and_validate_email(spoken_email: str) -> dict:
    """Cleans up voice transcription errors, stutters, and spelled-out numbers for emails."""
    if not spoken_email:
        return {"is_valid": False, "clean_email": ""}
        
    clean_email = spoken_email.lower().strip()
    
    # 1. Expand common voice-to-text spelled elements (Added underscore/dash)
    replacements = {
        " at rate ": "@",
        " at ": "@",
        " [at] ": "@",
        "(at)": "@",
        " dot ": ".",
        " [dot] ": ".",
        "(dot)": ".",
        " underscore ": "_",
        " dash ": "-",
        " hyphen ": "-",
        " double u ": "w",
        " at sign ": "@"
    }
    for old, new in replacements.items():
        clean_email = clean_email.replace(old, new)
        
    # 2. Convert spelled-out numbers to digits
    number_words = {
        "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", 
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9"
    }
    for word, digit in number_words.items():
        clean_email = re.sub(rf'\b{word}\b', digit, clean_email)
        
    # 3. Strip ALL spaces (Fixes "y e w a r @ g mail . com")
    clean_email = clean_email.replace(" ", "")
    
    # 4. Clean up Transcriber Stuttering & duplicate domains
    clean_email = re.sub(r'@+', '@', clean_email)  # Collapse multiple @@@ into one @
    clean_email = re.sub(r'\.+', '.', clean_email)  # Collapse multiple ... into one .
    clean_email = clean_email.replace("gmailgmail", "gmail")
    clean_email = clean_email.replace("yahooyahoo", "yahoo")
    clean_email = clean_email.replace("outlookoutlook", "outlook")
    
    # 5. Fix common fragmented domains caused by STT spacing
    domain_fixes = {
        "@gmai.": "@gmail.",
        "@g.mail.": "@gmail.",
        "@yaho.": "@yahoo.",
    }
    for bad_domain, good_domain in domain_fixes.items():
        clean_email = clean_email.replace(bad_domain, good_domain)
        
    # 6. Strip trailing periods (often added by STT at the end of a sentence)
    clean_email = clean_email.rstrip('.')
    
    # 7. Final Regex validation
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    is_valid = bool(re.match(email_regex, clean_email))
    
    if not is_valid:
        logger.warning(f"Email sanitation failed. Raw: '{spoken_email}' -> Cleaned: '{clean_email}'")
        
    return {"is_valid": is_valid, "clean_email": clean_email}

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
        # Slice from the end to keep the most recent messages
        cutoff_index = len(clean_messages) - MAX_HISTORY
        sliced_messages = clean_messages[cutoff_index:]
        
        # it has lost its parent "assistant" trigger. It is orphaned. Remove it.
        while sliced_messages and sliced_messages[0].get("role") == "tool":
            sliced_messages.pop(0)
            
        # that tried to call a tool, but we just deleted the tool response, remove the trigger too.
        while sliced_messages and (sliced_messages[0].get("role") == "assistant" and "tool_calls" in sliced_messages[0]):
            sliced_messages.pop(0)
            
        clean_messages = sliced_messages

    # 4. Latency Guard (Keyword RAG)
    rag_context = ""

    normalized_query = safe_query.lower().strip()

    import string
    clean_normalized = normalized_query.translate(str.maketrans('', '', string.punctuation))

    filler_phrases = {"hello", "hi", "hey", "yes", "no", "yeah", "nope", "okay", "ok", "thanks", "thank you", "cool", "got it", "awesome", "sure", "right"}

    is_personal_info = any(indicator in normalized_query for indicator in ["@", "dot com", "gmail", "yahoo", "my name is", "i am", "email"])

    if clean_normalized and clean_normalized not in filler_phrases and not is_personal_info:
        logger.debug(f"🔍 Running Semantic RAG for: {safe_query}")
        # Bumping top_k to 4 to ensure we catch deep README details
        rag_context = rag_service.retrieve_context(safe_query, top_k=4)

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
                        try:
                            # Yield ONLY standard text content so Vapi can speak it. 
                            # Do NOT yield fake tool_calls, it crashes the Vapi parser.
                            yield f"data: {json.dumps({'id': 'filler', 'choices': [{'delta': {'content': 'Give me just a second to pull that up...'}}]})}\n\n"
                        except Exception:
                            break # Handle user interruption gracefully
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

                        raw_email = arguments.get("email", "")
                        raw_name = arguments.get("name", "").strip()
                        raw_start_time = arguments.get("start_time", "").strip()

                        email_data = sanitize_and_validate_email(raw_email)
                        current_dt = datetime.now(ist_tz)
                        start_time = ""

                        # --- BULLETPROOF DATE PARSING ---
                        if "tomorrow" in raw_start_time.lower():
                            target_dt = current_dt + timedelta(days=1)
                            start_time = target_dt.replace(hour=10, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
                        elif "today" in raw_start_time.lower():
                            start_time = current_dt.replace(hour=17, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
                        else:
                            # Use Regex to extract exactly YYYY-MM-DDTHH:MM:SS, ignoring any trailing garbage
                            iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
                            match = re.search(iso_pattern, raw_start_time)
                            
                            if match:
                                # Force the 'Z' on the cleanly extracted string
                                start_time = f"{match.group(0)}Z"
                            else:
                                # If the LLM passed something completely unreadable (e.g., "10 AM"), 
                                # leave start_time empty so the validation block catches it.
                                logger.error(f"❌ Unparseable ISO string from LLM: {raw_start_time}")
                                start_time = ""


                        validation_errors = []
                        if not raw_name or len(raw_name) < 2:
                            validation_errors.append("a valid full name")
                        if not email_data["is_valid"]:
                            validation_errors.append("a valid email address")
                        if not start_time:
                            validation_errors.append("a specific time for the meeting")

                        if validation_errors:
                            logger.warning(f"⚠️ Validation Failed: {validation_errors}. Raw Email: {raw_email}")
                            issues_str = " and ".join(validation_errors)
                            
                            if not email_data["is_valid"] and email_data["clean_email"]:
                                error_prompt = f"SYSTEM ERROR: The email I heard was '{email_data['clean_email']}', but it seems to be missing something. Could you spell it out for me one more time?"
                            else:
                                error_prompt = f"SYSTEM ERROR: You cannot book yet. The provided data is invalid. Politely ask the user to clarify: {issues_str}."
                            
                            booking_result = {"success": False, "message": error_prompt}
                        else:
                            booking_result = await cal_service.book_interview(
                                name=raw_name, 
                                email=email_data["clean_email"], 
                                start_time=start_time
                            )

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