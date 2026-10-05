import time
import re
import html
import streamlit as st

# 🛠️ Import our modular components
import database as db
import agent
import forms  # <-- NEW: Our separated forms logic!

# ---- Page config ----
st.set_page_config(page_title="SeatSync AI", page_icon="✨", layout="wide")

# ---- Chat styling ----
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"]{ background:#0b0f19; color:white; }
.main{ padding-bottom:90px; }
.chat-wrap{ display:flex; flex-direction:column; gap:16px; }
.row{ display:flex; width:90%; }
.row.user{ justify-content:flex-end; }
.row.assistant{ justify-content:flex-start; }
.bubble{
    padding:14px 18px; border-radius:18px; max-width:70%;
    line-height:1.5; word-wrap:break-word;
    box-shadow:0 2px 10px rgba(0,0,0,.25); white-space: pre-wrap; 
}
.user .bubble{ background:#f3f3f3; color:#111; }
.assistant .bubble{ background:#202123; color:white; }
.guide-card{
    background:#161f30; border-left:4px solid #ffb700; border-radius:10px;
    padding:18px 22px; max-width:78%; line-height:1.6; white-space:pre-wrap;
    box-shadow:0 0 16px rgba(255,183,0,.10), 0 2px 10px rgba(0,0,0,.25);
}
.hl-action{ color:#ffb700; font-weight:600; }
.hl-info{ color:#5eead4; font-weight:600; }

/* Form Card custom styles */
[data-testid="stForm"] {
    background: #202123 !important; border: 1px solid #2d3139 !important;
    border-radius: 18px !important; padding: 24px !important; max-width: 460px !important; 
}
div[data-testid="stForm"] h3 { color: white !important; font-size: 1.2rem; margin-bottom: 16px; }
div[data-testid="stForm"] label { color: #aeafb4 !important; }
div[data-testid="column"]:has(.st-key-confirm_booking_btn) { order: 3 !important; }
div[data-testid="column"]:has(.st-key-cancel_booking_btn) { order: 2 !important; }

/* Buttons */
.st-key-cancel_booking_btn button { background-color: #e11d48 !important; color: white !important; border: 1px solid #e11d48 !important; }
.st-key-confirm_booking_btn button { background-color: transparent !important; color: white !important; border: 1px solid #454e5f !important; }
</style>
""", unsafe_allow_html=True)

STOP_PHRASES = ["never mind", "nevermind", "forget it", "nvm", "don't want", "dont want", "cancel that", "leave it"]

def wants_to_stop(text):
    return any(phrase in text.lower() for phrase in STOP_PHRASES)

def extract_booking_id(text):
    match = re.search(r'\d+', text)
    return match.group() if match else None

def handle_status(booking_id):
    booking = db.find_booking(booking_id)
    if booking: return db.format_booking(booking)
    return f"I couldn't find any booking with number {booking_id}. Please double-check the number."

def handle_cancel(booking_id):
    if db.cancel_booking(booking_id): return f"Your booking #{booking_id} has been cancelled."
    return f"I couldn't find any booking with number {booking_id}. Please double-check the number."

# =====================================================
# Session state initialization
# =====================================================
if "booking_stage" not in st.session_state:
    st.session_state.booking_stage = None

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant", "type": "guide",
        "content": (
            "👋 Hello! I'm the Bus Stand AI Agent. Today we have 2 buses "
            f"traveling from <span class='hl-info'>{db.ROUTE}</span> at <span class='hl-info'>09:15 PM and 07:45 AM</span>.\n\n"
            "Would you like to <span class='hl-action'>book a seat</span>, <span class='hl-action'>check booking history</span>, "
            "<span class='hl-action'>cancel a booking</span>, or <span class='hl-action'>talk to support</span>?"
        )
    }]

def bubble_html(role, text, cursor=False, guide=False):
    if guide:
        return f'<div class="row assistant"><div class="guide-card">{text}</div></div>'
    # Only the guide card carries our own HTML; everything else is typed text
    text = html.escape(text)
    css_class = "user" if role == "user" else "assistant"
    suffix = "▌" if cursor else ""
    return f'<div class="row {css_class}"><div class="bubble">{text}{suffix}</div></div>'

# =====================================================
# Chat UI Containers
# =====================================================
container = st.container()

with container:
    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        is_guide = message.get("type") == "guide"
        st.markdown(bubble_html(message["role"], message["content"], guide=is_guide), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # 💡 MAGIC HAPPENS HERE: Forms render safely inside the main layout loop!
    if st.session_state.booking_stage == "awaiting_booking_info":
        forms.render_booking_form()
    elif st.session_state.booking_stage == "viewing_history":
        forms.render_history_lookup_form()

question = st.chat_input("Ask about your document, or say 'I want to book a seat'...")

# =====================================================
# Core Router
# =====================================================
def route_message(question):
    stage = st.session_state.booking_stage

    # THE FIX: Close ANY open forms if the user types a new message!
    if stage in ["awaiting_booking_info", "viewing_history"]:
        st.session_state.booking_stage = None
        if stage == "awaiting_booking_info":
            forms.reset_booking_form_state()
        stage = None

    if stage in ("awaiting_id_for_status", "awaiting_id_for_cancel"):
        booking_id = extract_booking_id(question)
        if booking_id:
            st.session_state.booking_stage = None
            if stage == "awaiting_id_for_status": return handle_status(booking_id)
            return handle_cancel(booking_id)
        if wants_to_stop(question):
            st.session_state.booking_stage = None
            return "No problem, I've cleared that request. Let me know if you need anything else!"
        return "That doesn't look like a valid appointment number. Please send just the number (e.g., 256)."

    # 🧠 FOREFRONT INTENT CHECK
    intent = agent.classify_intent(question)

    if intent == "BOOK":
        st.session_state.booking_stage = "awaiting_booking_info"
        return "Sure! Please fill out the booking form below with your details:"
        
    if intent == "HISTORY":
        st.session_state.booking_stage = "viewing_history"
        return "I can help with that. Please enter your 13-digit CNIC in the form below to search your history."

    if intent == "STATUS":
        booking_id = extract_booking_id(question)
        if booking_id: return handle_status(booking_id)
        st.session_state.booking_stage = "awaiting_id_for_status"
        return "Sure, please share your appointment number so I can look it up."

    if intent == "CANCEL":
        booking_id = extract_booking_id(question)
        if booking_id: return handle_cancel(booking_id)
        st.session_state.booking_stage = "awaiting_id_for_cancel"
        return "Sure, please share your appointment number so I can cancel it."

    if intent == "SUPPORT":
        return "Connecting you to our support team... 📞 support@busstand.com | 0300-1234567"

    # Fallback to ID check just in case, then document lookup
    booking_id = extract_booking_id(question)
    if booking_id and db.find_booking(booking_id):
        return handle_status(booking_id)

    return agent.ask_document(question)

# =====================================================
# Process submissions and stream answers
# =====================================================
if question:
    st.session_state.messages.append({"role": "user", "content": question})

    with container:
        st.markdown(bubble_html("user", question), unsafe_allow_html=True)
        placeholder = st.empty()
        placeholder.markdown(bubble_html("assistant", "🔍 Thinking..."), unsafe_allow_html=True)

        answer = route_message(question)

        typed_answer = ""
        # Keep each word's trailing whitespace so line breaks survive the typing effect
        for word in re.findall(r'\S+\s*', answer):
            typed_answer += word
            placeholder.markdown(bubble_html("assistant", typed_answer, cursor=True), unsafe_allow_html=True)
            time.sleep(0.02)

        placeholder.markdown(bubble_html("assistant", answer), unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()