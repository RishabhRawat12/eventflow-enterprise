from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import json
import google.generativeai as genai
from services.redis_state import redis_service

router = APIRouter(prefix="/api/v1")

# --- Pydantic Schemas for Structured Output (as per user directive) ---

class ProtocolStep(BaseModel):
    zone_id: str
    action: str

class StaffResponse(BaseModel):
    severity: str = Field(description="CRITICAL, WARNING, or INFO")
    target_zones: List[str]
    dispersal_protocol: List[ProtocolStep]
    broadcast_message: str

class ItineraryStep(BaseModel):
    time: str
    action: str
    zone_id: str

class AttendeeResponse(BaseModel):
    answer: str
    itinerary: List[ItineraryStep]
    suggested_route: List[str]

class ConciergeRequest(BaseModel):
    prompt: str
    role: str = "attendee" # "staff" or "attendee"

# --- Gemini Service Initialization ---

def get_gemini_model(role: str):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key missing.")
    
    genai.configure(api_key=api_key)
    
    # Select schema based on role
    schema = StaffResponse if role == "staff" else AttendeeResponse
    
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": schema
        }
    )

@router.post("/concierge")
async def ai_concierge(request: ConciergeRequest):
    """
    Zero-trust Gemini proxy with live Redis context injection via system_instruction.
    """
    try:
        # 1. Pull Live State from Redis (Context Injection)
        keys = await redis_service.client.keys("venue:stadium:zone:*")
        venue_context = []
        for key in keys:
            data = await redis_service.client.hgetall(key)
            venue_context.append({
                "id": key.split(":")[-1],
                **data
            })
            
        context_json = json.dumps(venue_context)
        
        # 2. Model Initialization with System Instructions
        system_instruction = (
            f"You are the EventFlow AI Concierge for Wankhede Stadium. "
            f"Active Role: {request.role}. "
            f"Live Venue State: {context_json}. "
            "STRICT RULES: Use ONLY the provided live data. "
            "If a zone is 'CRITICAL', you MUST prioritize safety dispersal protocols. "
            "Response must be valid JSON matching the requested schema."
        )
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Gemini API Key missing.")
        
        genai.configure(api_key=api_key)
        
        # Select schema based on role
        schema = StaffResponse if request.role == "staff" else AttendeeResponse
        
        # 3. Model Execution (User prompt is isolated)
        if api_key == "mock-key":
            print("[AI] Running in MOCK mode. Returning simulated response.")
            if request.role == "staff":
                return {
                    "severity": "INFO",
                    "target_zones": ["NorthGate"],
                    "dispersal_protocol": [{"zone_id": "0", "action": "Increase monitoring"}],
                    "broadcast_message": "SIMULATED: All zones nominal. Maintaining flow."
                }
            else:
                return {
                    "answer": "SIMULATED: I see you are looking for info about the stadium. Based on the live data, everything looks clear!",
                    "itinerary": [{"time": "12:00", "action": "Visit MainArena", "zone_id": "2"}],
                    "suggested_route": ["0", "2"]
                }

        # Initialize model with system instruction (Corrected per expert advice)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_instruction,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": schema
            }
        )
        
        response = await model.generate_content_async(request.prompt)
        return json.loads(response.text)
        
    except Exception as e:
        # Stack trace handled by global exception middleware
        raise HTTPException(status_code=500, detail=f"Gemini inference failed: {str(e)}")
