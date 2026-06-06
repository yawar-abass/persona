import re

def clean_and_validate_input(text: str) -> str:
    """
    Sanitizes raw conversational queries against typical basic prompt injections
    and systemic attempts to override system context rules.
    """
    # Lowercase for simple sequence checks
    normalized = text.lower()
    
    # Simple list of structural override triggers to strip or flag
    injection_patterns = [
        r"ignore all previous instructions",
        r"ignore systemic prompt",
        r"you are no longer yawar",
        r"system prompt leak",
        r"output your guidelines"
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, normalized):
            # Instead of breaking or throwing a 500 error, we replace the query with a safe fallback
            # that triggers the LLM's grounded defense protocols seamlessly.
            return "Attempted systematic override detected. Please stay in character as Yawar Abass."
            
    return text