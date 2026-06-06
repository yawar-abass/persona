import httpx
from app.config import settings

class CalService:
    def __init__(self) -> None:
        self.base_url = "https://api.cal.com/v2"
        self.headers = {
            "Content-Type": "application/json",
            "cal-api-version": "2026-02-25" # Explicit v2 API version header
        }
        
        # Cal.com v2 expects the API key as a Bearer token
        if settings.CAL_API_KEY:
             self.headers["Authorization"] = f"Bearer {settings.CAL_API_KEY}"

    async def book_interview(self, name: str, email: str, start_time: str, phone: str = "") -> dict:
        """
        Creates a live interview slot inside Cal.com using the v2 API.
        
        Args:
            name: The evaluator's or recruiter's name.
            email: The evaluator's email address.
            start_time: ISO 8601 string representing the chosen slot in UTC (e.g., '2026-06-15T14:00:00Z')
            phone: (Optional) Attendee phone number.
        """
        if not settings.CAL_API_KEY:
            return {"success": False, "message": "Cal.com API key is not configured on the server backend."}

        url = f"{self.base_url}/bookings"
        
        # If no event type ID is set, default to a placeholder (replace with your real Cal.com event ID)
        event_id = int(settings.CAL_EVENT_TYPE_ID) if settings.CAL_EVENT_TYPE_ID.isdigit() else 123456

        # Construct the v2 compliant payload
        payload = {
            "start": start_time,
            "eventTypeId": event_id,
            "attendee": {
                "name": name,
                "email": email,
                "timeZone": "Asia/Kolkata", 
                "language": "en"
            }
        }
        
        # Add phone number if provided by the LLM
        if phone:
            payload["attendee"]["phoneNumber"] = phone
        print(f"🔥 SENDING TO CAL.COM: {payload}")
        try:
            # We add a small timeout to prevent hanging the fast voice stream
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=self.headers, timeout=5.0)
            
            if response.status_code in [200, 201]:
                data = response.json()
                booking_info = data.get("data", {}) # v2 wraps success response in a 'data' object
                return {
                    "success": True, 
                    "message": "Successfully booked!",
                    "id": booking_info.get("id"),
                    "uid": booking_info.get("uid"),
                    "status": booking_info.get("status")
                }
            else:
                print(f"Cal.com v2 Error Response: {response.text}")
                return {"success": False, "message": f"Cal.com returned status {response.status_code}: {response.text}"}
                
       # Updated exception handling for httpx
        except httpx.TimeoutException:
            return {"success": False, "message": "Calendar network timeout. Please try scheduling again."}
        except httpx.RequestError as e:
            print(f"Network error connecting to Cal.com: {e}")
            return {"success": False, "message": f"Network error: {str(e)}"}
        except Exception as e:
            print(f"Unexpected error in booking workflow: {e}")
            return {"success": False, "message": str(e)}
    
    async def check_availability(self, date: str) -> dict:
        """
        Checks Cal.com for available time slots on a specific date.
        Args:
            date: YYYY-MM-DD string (e.g., '2026-06-15')
        """
        if not settings.CAL_API_KEY:
            return {"success": False, "message": "API key missing."}

        # Cal.com v2 slots endpoint
        url = f"{self.base_url}/slots"
        event_id = int(settings.CAL_EVENT_TYPE_ID) if settings.CAL_EVENT_TYPE_ID.isdigit() else 123456

        # Look for slots from the start of the requested day to the end
        params = {
            "eventTypeId": event_id,
            "startTime": f"{date}T00:00:00Z",
            "endTime": f"{date}T23:59:59Z",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                slots = data.get("data", {}).get("slots", [])
                
                if not slots:
                    return {"success": True, "available_slots": [], "message": "No slots available on this date."}
                
                # Extract just the raw times to keep the LLM context clean
                available_times = [slot.get("time") for slot in slots]
                return {"success": True, "available_slots": available_times}
            else:
                return {"success": False, "message": "Could not fetch calendar availability."}
                
        except Exception as e:
            return {"success": False, "message": str(e)}
# Export single functional service instance
cal_service = CalService()