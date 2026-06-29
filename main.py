import os
import json
import re
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage
from config import SYSTEM_PROMPT
from lead_scorer import score_prospect, get_tag

load_dotenv()

app = FastAPI()

# Allow CORS for React frontend (Vite default is 5173, but we allow all for local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for chat histories (In production, use Redis or a database)
sessions = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str
    api_key: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    stage: str
    lead_captured: bool
    lead_data: Optional[dict] = None

def get_session_memory(session_id: str):
    if session_id not in sessions:
        sessions[session_id] = ConversationBufferMemory(return_messages=True)
    return sessions[session_id]

def extract_stage(text: str):
    match = re.search(r'\[STAGE:(identify|engage|convert)\]', text, re.IGNORECASE)
    if match:
        stage = match.group(1).lower()
        return stage, text.replace(match.group(0), "").strip()
    return "identify", text

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    api_key = request.api_key or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required")

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.7
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    memory = get_session_memory(request.session_id)
    memory.chat_memory.add_user_message(request.message)

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + memory.chat_memory.messages

    try:
        response = llm.invoke(messages)
        full_response = response.content
        
        stage, clean_response = extract_stage(full_response)
        
        lead_captured = False
        lead_data = None
        
        if "LEAD_CAPTURED" in clean_response:
            parts = clean_response.split("LEAD_CAPTURED")
            clean_response = parts[0].strip()
            json_str = parts[1].strip()
            
            try:
                json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if json_match:
                    lead_data = json.loads(json_match.group(0))
                    lead_data['score'] = score_prospect(lead_data)
                    lead_data['tag'] = get_tag(lead_data['score'])
                    lead_captured = True
            except Exception:
                pass # Fallback if JSON fails to parse
                
        memory.chat_memory.add_ai_message(full_response)
        
        return ChatResponse(
            reply=clean_response,
            stage=stage,
            lead_captured=lead_captured,
            lead_data=lead_data
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
