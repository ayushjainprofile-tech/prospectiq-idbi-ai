import streamlit as st
import json
import os
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from config import SYSTEM_PROMPT, QUICK_REPLIES
from lead_scorer import score_prospect, get_tag, get_product_label

# --- Page Configuration ---
st.set_page_config(
    page_title="ProspectIQ | IDBI Bank",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    /* Premium Styling */
    .stApp {
        background-color: #0A2E2A;
        color: #FFFFFF;
    }
    
    /* Header Gradient */
    .piq-header {
        background: linear-gradient(135deg, #0A2E2A 0%, #0D5C4B 100%);
        padding: 20px 30px;
        border-radius: 16px;
        margin-bottom: 30px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .piq-title {
        color: #FFFFFF;
        font-family: 'Sora', sans-serif;
        font-weight: 800;
        margin: 0;
        font-size: 28px;
    }
    
    .piq-title span {
        color: #F5A623;
    }
    
    .piq-subtitle {
        color: rgba(255, 255, 255, 0.7);
        font-size: 14px;
        margin: 5px 0 0 0;
    }
    
    /* Chat bubbles */
    .stChatMessage {
        background: transparent !important;
    }
    
    div[data-testid="stChatMessage"] {
        padding: 10px 15px;
        border-radius: 12px;
        margin-bottom: 10px;
    }
    
    /* Lead Card */
    .lead-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-left: 4px solid #F5A623;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        backdrop-filter: blur(10px);
    }
    
    .lead-title {
        color: #F5A623;
        margin-top: 0;
        font-size: 18px;
        font-weight: bold;
    }
    
    .score-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 12px;
    }
    
    .badge-HOT { background: #E53E3E; color: white; }
    .badge-WARM { background: #DD6B20; color: white; }
    .badge-NEW { background: #3182CE; color: white; }
    
    /* Quick Replies */
    .quick-replies-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 20px;
    }
    
    /* Stage Pill */
    .stage-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-top: 10px;
    }
    .stage-identify { background: rgba(255,255,255,0.1); color: white; }
    .stage-engage { background: #FEF3D7; color: #B8941F; }
    .stage-convert { background: #E8F4F2; color: #0D5C4B; }
    
</style>
""", unsafe_allow_html=True)

# --- Initialization ---
load_dotenv()

def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Add initial greeting
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "Namaste! 🙏 I'm ProspectIQ, IDBI Bank's AI assistant. How can I help you with your banking needs today?",
            "is_lead": False
        })
    if "memory" not in st.session_state:
        st.session_state.memory = ConversationBufferMemory(return_messages=True)
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.getenv("GOOGLE_API_KEY", "")
    if "stage" not in st.session_state:
        st.session_state.stage = "identify"
    if "leads" not in st.session_state:
        st.session_state.leads = []

init_session()

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    api_key_input = st.text_input("Gemini API Key", value=st.session_state.api_key, type="password")
    if api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input
    
    st.markdown("---")
    
    model_choice = st.selectbox(
        "AI Model",
        ["gemini-1.5-flash", "gemini-1.5-pro"]
    )
    
    st.markdown("---")
    
    st.markdown("### Funnel Stage")
    
    stage_classes = {
        "identify": "stage-identify",
        "engage": "stage-engage",
        "convert": "stage-convert"
    }
    
    current_class = stage_classes.get(st.session_state.stage, "stage-identify")
    
    st.markdown(f'<div class="stage-pill {current_class}">{st.session_state.stage.upper()}</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("Reset Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.memory = ConversationBufferMemory(return_messages=True)
        st.session_state.stage = "identify"
        st.rerun()

# --- Main App ---
st.markdown("""
<div class="piq-header">
    <h1 class="piq-title">Prospect<span>IQ</span></h1>
    <p class="piq-subtitle">IDBI Bank — AI Customer Acquisition Assistant</p>
</div>
""", unsafe_allow_html=True)

# Helper function to extract stage
def extract_stage(text):
    match = re.search(r'\[STAGE:(identify|engage|convert)\]', text, re.IGNORECASE)
    if match:
        stage = match.group(1).lower()
        return stage, text.replace(match.group(0), "").strip()
    return None, text

# Check API Key
if not st.session_state.api_key:
    st.warning("⚠️ Please enter your Gemini API Key in the sidebar to start chatting.")
    st.stop()

try:
    llm = ChatGoogleGenerativeAI(
        model=model_choice,
        google_api_key=st.session_state.api_key,
        temperature=0.7
    )
except Exception as e:
    st.error(f"Error initializing AI: {str(e)}")
    st.stop()

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("is_lead"):
            lead = msg["lead_data"]
            st.markdown(f"""
            <div class="lead-card">
                <h3 class="lead-title">🎯 Lead Captured</h3>
                <p><strong>Name:</strong> {lead.get('name', 'N/A')}</p>
                <p><strong>Product:</strong> {get_product_label(lead.get('product', ''))}</p>
                <p><strong>Income:</strong> ₹{lead.get('income', '0')}</p>
                <div style="margin-top: 15px;">
                    <span class="score-badge badge-{lead.get('tag', 'NEW')}">{lead.get('tag', 'NEW')} PRIORITY</span>
                    <span style="margin-left: 10px; font-weight: bold; color: #57D48D;">Score: {lead.get('score', 0)}/99</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if msg.get("content"):
                 st.markdown(msg["content"])
        else:
            st.markdown(msg["content"])

# Quick Replies logic
def handle_quick_reply(reply):
    st.session_state.quick_reply_clicked = reply

if "quick_reply_clicked" in st.session_state and st.session_state.quick_reply_clicked:
    prompt = st.session_state.quick_reply_clicked
    st.session_state.quick_reply_clicked = None
else:
    prompt = st.chat_input("Ask about IDBI Bank products...")

if len(st.session_state.messages) == 1:
    st.markdown("<div class='quick-replies-container'>", unsafe_allow_html=True)
    cols = st.columns(len(QUICK_REPLIES[:4])) # Show first 4
    for i, reply in enumerate(QUICK_REPLIES[:4]):
        with cols[i]:
            if st.button(reply, key=f"qr_{i}"):
                prompt = reply
    st.markdown("</div>", unsafe_allow_html=True)

if prompt:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt, "is_lead": False})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    st.session_state.memory.chat_memory.add_user_message(prompt)

    # Prepare messages for LangChain
    history = st.session_state.memory.chat_memory.messages
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + history

    # Call AI
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # Try streaming first
            for chunk in llm.stream(messages):
                full_response += chunk.content
                # Hide the [STAGE] tags during streaming if possible, but simpler to just stream all and clean after
                clean_streaming = re.sub(r'\[STAGE:(identify|engage|convert)\]', '', full_response, flags=re.IGNORECASE)
                response_placeholder.markdown(clean_streaming + "▌")
            
            # Post-process response
            stage, clean_response = extract_stage(full_response)
            if stage:
                st.session_state.stage = stage
                
            # Check for lead capture
            if "LEAD_CAPTURED" in clean_response:
                parts = clean_response.split("LEAD_CAPTURED")
                chat_text = parts[0].strip()
                json_str = parts[1].strip()
                
                try:
                    # Find JSON block
                    json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
                    if json_match:
                        lead_data = json.loads(json_match.group(0))
                        lead_data['score'] = score_prospect(lead_data)
                        lead_data['tag'] = get_tag(lead_data['score'])
                        
                        st.session_state.leads.append(lead_data)
                        
                        response_placeholder.markdown(chat_text)
                        
                        st.markdown(f"""
                        <div class="lead-card">
                            <h3 class="lead-title">🎯 Lead Captured</h3>
                            <p><strong>Name:</strong> {lead_data.get('name', 'N/A')}</p>
                            <p><strong>Product:</strong> {get_product_label(lead_data.get('product', ''))}</p>
                            <p><strong>Income:</strong> ₹{lead_data.get('income', '0')}</p>
                            <div style="margin-top: 15px;">
                                <span class="score-badge badge-{lead_data.get('tag', 'NEW')}">{lead_data.get('tag', 'NEW')} PRIORITY</span>
                                <span style="margin-left: 10px; font-weight: bold; color: #57D48D;">Score: {lead_data.get('score', 0)}/99</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": chat_text,
                            "is_lead": True,
                            "lead_data": lead_data
                        })
                        st.session_state.memory.chat_memory.add_ai_message(full_response)
                        st.rerun() # Refresh to update sidebar stage
                        
                except Exception as e:
                    clean_response = clean_response.replace("LEAD_CAPTURED", "")
                    response_placeholder.markdown(clean_response)
                    st.session_state.messages.append({"role": "assistant", "content": clean_response, "is_lead": False})
                    st.session_state.memory.chat_memory.add_ai_message(full_response)
                    
            else:
                response_placeholder.markdown(clean_response)
                st.session_state.messages.append({"role": "assistant", "content": clean_response, "is_lead": False})
                st.session_state.memory.chat_memory.add_ai_message(full_response)
                
            st.rerun() # Refresh to update sidebar stage
                
        except Exception as e:
            st.error(f"Error communicating with AI: {str(e)}")
