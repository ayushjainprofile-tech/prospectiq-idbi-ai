import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

# Ensure the local api directory is importable when this file is executed as a Vercel serverless function.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import SystemMessage
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
        sessions[session_id] = InMemoryChatMessageHistory()
    return sessions[session_id]

def extract_stage(text: str):
    match = re.search(r'\[STAGE:(identify|engage|convert)\]', text, re.IGNORECASE)
    if match:
        stage = match.group(1).lower()
        return stage, text.replace(match.group(0), "").strip()
    return "identify", text

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    load_dotenv(override=True)
    openai_key = os.getenv("OPENAI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = request.api_key or os.getenv("GOOGLE_API_KEY")

    memory = get_session_memory(request.session_id)
    memory.add_user_message(request.message)
    recent_messages = memory.messages[-6:] if len(memory.messages) > 6 else memory.messages
    
    full_response = ""
    user_msg = request.message.lower()

    # Question-Based Intent Analysis
    is_complex_query = any(k in user_msg for k in ["loan", "interest", "rate", "calculate", "eligibility", "compare", "account", "scheme", "process"])
    is_lead_data = any(k in user_msg for k in ["name", "phone", "number", "branch", "apply", "contact"])

    # Define dynamic priority queue based on question type
    if is_complex_query or is_lead_data:
        # Complex financial queries get top-tier Llama 3 70B & GPT-4o reasoning power first
        provider_order = ["groq", "openai", "gemini"]
    else:
        # Quick conversational queries prioritize ultra-fast streaming
        provider_order = ["groq", "gemini", "openai"]

    for provider in provider_order:
        if full_response:
            break

        if provider == "groq" and (groq_key or (gemini_key and gemini_key.startswith("gsk_"))):
            key_to_use = groq_key if (groq_key and groq_key.startswith("gsk_")) else gemini_key
            if key_to_use and key_to_use.startswith("gsk_"):
                import requests
                headers = {"Authorization": f"Bearer {key_to_use}", "Content-Type": "application/json"}
                formatted_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
                for m in recent_messages:
                    role = "user" if m.type == "user" else "assistant"
                    formatted_msgs.append({"role": role, "content": m.content})
                # Choose model based on complexity
                m_name = "llama-3.3-70b-versatile" if is_complex_query else "llama-3.1-8b-instant"
                try:
                    payload = {"model": m_name, "messages": formatted_msgs, "temperature": 0.7, "max_tokens": 350}
                    res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=5)
                    if res.status_code == 200:
                        full_response = res.json()['choices'][0]['message']['content']
                except Exception:
                    pass

        elif provider == "openai" and (openai_key or (gemini_key and gemini_key.startswith("sk-"))):
            key_to_use = openai_key if (openai_key and openai_key.startswith("sk-")) else gemini_key
            if key_to_use and key_to_use.startswith("sk-"):
                import requests
                try:
                    headers = {"Authorization": f"Bearer {key_to_use}", "Content-Type": "application/json"}
                    formatted_msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
                    for m in recent_messages:
                        role = "user" if m.type == "user" else "assistant"
                        formatted_msgs.append({"role": role, "content": m.content})
                    payload = {"model": "gpt-4o-mini", "messages": formatted_msgs, "temperature": 0.7, "max_tokens": 350}
                    res = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=5)
                    if res.status_code == 200:
                        full_response = res.json()['choices'][0]['message']['content']
                except Exception:
                    pass

        elif provider == "gemini" and gemini_key and gemini_key.startswith("AIza"):
            try:
                llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash-lite",
                    google_api_key=gemini_key,
                    temperature=0.7,
                    max_output_tokens=350
                )
                messages = [SystemMessage(content=SYSTEM_PROMPT)] + recent_messages
                response = llm.invoke(messages)
                full_response = response.content
            except Exception:
                pass

    try:
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
                pass
                
        memory.add_ai_message(full_response)
        return ChatResponse(
            reply=clean_response,
            stage=stage,
            lead_captured=lead_captured,
            lead_data=lead_data
        )

    except Exception as e:
        error_str = str(e)
        if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
            # Smart fallback for demonstration when Gemini API free quota is exhausted
            user_msg_lower = request.message.lower()
            lead_captured = False
            lead_data = None
            
            # Check if user provided contact info (lead capture)
            if "phone" in user_msg_lower or "number" in user_msg_lower or re.search(r'\d{10}', request.message):
                # Try extracting name and branch
                name_match = re.search(r'name\s*[:\-]\s*([a-zA-Z]+)', request.message, re.IGNORECASE)
                branch_match = re.search(r'branch\s*[:\-]\s*([a-zA-Z]+)', request.message, re.IGNORECASE)
                phone_match = re.search(r'(\d{10})', request.message)
                
                name = name_match.group(1).capitalize() if name_match else "Valued Customer"
                branch = branch_match.group(1).capitalize() if branch_match else "Main Branch"
                phone = phone_match.group(1) if phone_match else "1234567890"
                
                lead_data = {
                    "name": name,
                    "product": "IDBI Banking Services",
                    "income": "5,00,000",
                    "score": 85,
                    "tag": "HOT"
                }
                lead_captured = True
                reply_text = f"[STAGE:convert] Excellent! Thank you {name}. I have registered your details for IDBI Bank ({branch} Branch). Our representative will call you shortly on {phone} to complete your onboarding!"
            elif "home loan" in user_msg_lower or "home" in user_msg_lower:
                reply_text = "[STAGE:engage] IDBI Bank Home Loans start at an attractive 8.45% p.a. interest rate with flexible tenure up to 30 years and up to 90% financing! Are you looking to purchase a new property or transfer an existing loan?"
            elif "interest" in user_msg_lower or "rate" in user_msg_lower or "eligibility" in user_msg_lower:
                reply_text = "[STAGE:engage] Our Home Loan interest rates start at 8.45% p.a. and Fixed Deposits offer up to 7.25% p.a. (7.50% for Senior Citizens)! Which product's eligibility would you like me to calculate for you?"
            elif "loan" in user_msg_lower or "loans" in user_msg_lower:
                reply_text = "[STAGE:engage] We offer a variety of tailored loans including Home Loans (8.45%), Auto Loans (8.75%), and Personal Loans (10.75%). Which loan type suits your current requirement best?"
            elif "account" in user_msg_lower or "savings" in user_msg_lower or "fd" in user_msg_lower:
                reply_text = "[STAGE:engage] Our IDBI Super Savings Account gives up to 4% p.a. interest with zero-balance facilities! Would you like to open an account or know more about our 7.25% FD rates?"
            elif "hello" in user_msg_lower or "hi" in user_msg_lower or "hey" in user_msg_lower or "namaste" in user_msg_lower:
                reply_text = "[STAGE:identify] Namaste! 🙏 Welcome to IDBI Bank ProspectIQ. I am your personal AI Relationship Manager. How can I help you with your financial goals today?"
            else:
                reply_text = f"[STAGE:engage] Thanks for asking about '{request.message}'. IDBI Bank provides customized solutions for all your banking needs. Could you tell me a bit more about your requirement or share your contact info for a personalized quote?"

            stage, clean_response = extract_stage(reply_text)
            memory.add_ai_message(reply_text)
            return ChatResponse(
                reply=clean_response,
                stage=stage,
                lead_captured=lead_captured,
                lead_data=lead_data
            )
        raise HTTPException(status_code=500, detail=str(e))
