import time
import re
import streamlit as st

# 🛠️ Import our modular components
import database as db
import agent

# ---- Page config ----
st.set_page_config(page_title="SeatSync AI", page_icon="✨", layout="wide")

# ---- Chat styling ----
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"]{
    background:#0b0f19;
    color:white;
}
.main{ padding-bottom:90px; }
.chat-wrap{ display:flex; flex-direction:column; gap:16px; }
.row{ display:flex; width:90%; }
.row.user{ justify-content:flex-end; }
.row.assistant{ justify-content:flex-start; }
.bubble{
    padding:14px 18px;
    border-radius:18px;
    max-width:70%;
    line-height:1.5;
    word-wrap:break-word;
    box-shadow:0 2px 10px rgba(0,0,0,.25);
    white-space: pre-wrap; 
}
.user .bubble{ background:#f3f3f3; color:#111; }
.assistant .bubble{ background:#202123; color:white; }

/* System Guide Card */
.guide-card{
    background:#161f30;
    border-left:4px solid #ffb700;
    border-radius:10px;
    padding:18px 22px;
    max-width:78%;
    line-height:1.6;
    white-space:pre-wrap;
    box-shadow:0 0 16px rgba(255,183,0,.10), 0 2px 10px rgba(0,0,0,.25);
}
.hl-action{ color:#ffb700; font-weight:600; }
.hl-info{ color:#5eead4; font-weight:600; }

/* Form Card custom styles */
[data-testid="stForm"] {
    background: #202123 !important;
    border: 1px solid #2d3139 !important;
    border-radius: 18px !important;
    padding: 24px !important;
    box-shadow: 0 4px 15px rgba(0,0,0,.3);
    max-width: 460px !important; 
}
div[data-testid="stForm"] h3 {
    color: white !important;
    font-size: 1.2rem;
    margin-bottom: 16px;
}
div[data-testid="stForm"] label {
    color: #aeafb4 !important;
}

/* 🔀 THE MAGIC FIX: Visually swap the columns! */
/* We target the exact columns containing our keyed buttons and swap their visual order */
div[data-testid="column"]:has(.st-key-confirm_booking_btn) {
    order: 3 !important; /* Forces Confirm to the far right visually */
}
div[data-testid="column"]:has(.st-key-cancel_booking_btn) {
    order: 2 !important; /* Forces Cancel to the middle-left visually */
}

/* 🔴 Premium Custom Red Block Styling for Cancel Button */
.st-key-cancel_booking_btn button {
    background-color: #e11d48 !important;
    color: white !important;
    border: 1px solid #e11d48 !important;
    transition: all 0.2s ease-in-out !important;
}
.st-key-cancel_booking_btn button:hover {
    background-color: #be123c !important;
    border-color: #be123c !important;
    box-shadow: 0 0 12px rgba(225, 29, 72, 0.4) !important;
}

/* 🟢 Clean Simple Box Styling for Confirm Button */
.st-key-confirm_booking_btn button {
    background-color: transparent !important;
    color: white !important;
    border: 1px solid #454e5f !important;
    transition: all 0.2s ease-in-out !important;
}
.st-key-confirm_booking_btn button:hover {
    border-color: #5eead4 !important;
    background-color: transparent !important;
    color: white !important;
    box-shadow: 0 0 10px rgba(94, 234, 212, 0.2) !important;
}
</style>
""", unsafe_allow_html=True)

STOP_PHRASES = [
    "never mind", "nevermind", "forget it", "nvm",
    "don't want", "dont want", "no longer want",
    "not anymore", "cancel that", "leave it"
]

def wants_to_stop(text):
    lowered = text.lower()
    return any(phrase in lowered for phrase in STOP_PHRASES)

def extract_booking_id(text):
    match = re.search(r'\d+', text)
    return match.group() if match else None

# =====================================================
# Form Input Validation Helpers
# =====================================================

def is_valid_name(name_str):
    pattern = r"^(?=.*[A-Za-z])[A-Za-z0-9\s.\-]+$"
    return bool(re.match(pattern, name_str.strip()))

def is_valid_cnic(cnic_str):
    # Just call your existing sanitize function. If it ends up being 13, it's valid.
    return len(db.sanitize_cnic(cnic_str)) == 13

def is_valid_phone(phone_str):
    pattern = r"^03\d{9}$"
    return bool(re.match(pattern, phone_str.strip()))

# =====================================================
# Booking result helpers
# =====================================================

def handle_status(booking_id):
    booking = db.find_booking(booking_id)
    if booking:
        return db.format_booking(booking)
    return f"I couldn't find any booking with number {booking_id}. Please double-check the number."

def handle_cancel(booking_id):
    if db.cancel_booking(booking_id):
        return f"Your booking #{booking_id} has been cancelled."
    return f"I couldn't find any booking with number {booking_id}. Please double-check the number."

# =====================================================
# Session state initialization
# =====================================================
if "booking_stage" not in st.session_state:
    st.session_state.booking_stage = None

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "type": "guide",
        "content": (
            "👋 Hello! I'm the Bus Stand AI Agent. Today we have 2 buses "
            f"traveling from <span class='hl-info'>{db.ROUTE}</span> at "
            "<span class='hl-info'>09:15 PM and 07:45 AM</span>.\n\n"
            "Would you like to <span class='hl-action'>book a seat</span>, "
            "<span class='hl-action'>check booking status</span>, "
            "<span class='hl-action'>cancel a booking</span>, or "
            "<span class='hl-action'>talk to support</span>? You can also ask me "
            "questions about the uploaded document."
        )
    }]

def bubble_html(role, text, cursor=False, guide=False):
    if guide:
        return f"""
        <div class="row assistant">
            <div class="guide-card">{text}</div>
        </div>
        """
    css_class = "user" if role == "user" else "assistant"
    suffix = "▌" if cursor else ""
    return f"""
    <div class="row {css_class}">
        <div class="bubble">{text}{suffix}</div>
    </div>
    """

# =====================================================
# Booking form layout logic
# =====================================================

def field_error(field_key):
    error_text = st.session_state.get("form_errors", {}).get(field_key)
    if error_text:
        st.markdown(
            f"<div style='color:#ff4d4d;font-size:0.82rem;margin:-8px 0 10px 2px;'>⚠ {error_text}</div>",
            unsafe_allow_html=True
        )

def render_history_lookup_form():
    with st.form(key="history_lookup_form"):
        st.markdown("### 🔍 Search Booking History")
        
        # Input for CNIC
        raw_cnic = st.text_input(
            "Enter your 13-digit CNIC", 
            placeholder="e.g., 3840312345671 or 38403-1234567-1",
            key="history_cnic_input"
        )
        
        submitted = st.form_submit_button("View History")

        if submitted:
            # 1. Sanitize: remove hyphens/spaces
            clean_cnic = db.sanitize_cnic(raw_cnic)
            
            # 2. Validate: Must be 13 digits and NO letters
            if len(clean_cnic) != 13 or not clean_cnic.isdigit():
                st.error("Invalid CNIC. Please enter 13 digits only (no letters).")
            else:
                # 3. Search Database
                matches = db.get_all_bookings_by_cnic(clean_cnic)
                
                if not matches:
                    st.warning("No booking history found for this CNIC.")
                else:
                    # 4. Display results
                    st.success(f"Found {len(matches)} booking(s):")
                    for b in matches:
                        st.info(db.format_booking(b))
                    
                    # Reset stage after lookup
                    if st.button("Close History"):
                        st.session_state.booking_stage = None
                        st.rerun()

def reset_booking_form_state():
    for key in ["form_name_widget", "form_cnic_widget", "form_phone_widget", "form_errors"]:
        st.session_state.pop(key, None)

def render_booking_form():
    st.write("")
    form_col, spacer_col = st.columns([2, 1])

    with form_col:
        with st.form(key="interactive_passenger_form"):
            st.markdown(f"### 🚌 {db.ROUTE} Booking Card")

            st.text_input(
                "Enter your name", placeholder="e.g., Asif Khan", key="form_name_widget"
            )
            field_error("name")
            
            st.text_input(
                "Enter CNIC", placeholder="e.g., 3840312345671 (13 digits)", key="form_cnic_widget"
            )
            field_error("cnic")

            st.text_input(
                "Enter Mobile Number", placeholder="e.g., 03217654321", key="form_phone_widget"
            )
            field_error("phone")

            # Your existing style: Use keys and session_state
            st.radio(
                "Select Departure Time",
                options=["Morning (07:45 AM)", "Evening (09:15 PM)"],
                key="form_time_widget",
                horizontal=True,
                index=None
            )
            field_error("time")

            # 🧠 SMART DOM PLACEMENT: Confirm must be coded FIRST so the browser links the 'Enter' key to it!
            spacer, confirm_col, cancel_col = st.columns([2, 1, 1])
            
            with confirm_col:
                confirm_clicked = st.form_submit_button("Confirm", use_container_width=True, key="confirm_booking_btn")
            with cancel_col:
                cancel_clicked = st.form_submit_button("Cancel", use_container_width=True, key="cancel_booking_btn")

        if cancel_clicked:
            reset_booking_form_state()
            st.session_state.booking_stage = None
            st.session_state.messages.append({
                "role": "assistant",
                "content": "No problem, I've cancelled that booking request. Let me know if you need anything else!"
            })
            st.rerun()

        if confirm_clicked:
            cleaned_name = st.session_state.form_name_widget.strip()
            # 💡 HERE IS THE MAGIC: We sanitize immediately upon submission
            raw_cnic = st.session_state.form_cnic_widget.strip()
            cleaned_cnic = db.sanitize_cnic(raw_cnic)
            cleaned_phone = st.session_state.form_phone_widget.strip()
            selected_time = st.session_state.get("form_time_widget")

            errors = {}
            if not cleaned_name:
                errors["name"] = "Please enter your name."
            elif not is_valid_name(cleaned_name):
                errors["name"] = "Invalid name!"

            # Updated validation logic
            if not raw_cnic:
                errors["cnic"] = "Please enter your CNIC."
            elif len(cleaned_cnic) != 13:
                errors["cnic"] = "Invalid CNIC. Must be 13 digits."

            if not cleaned_phone:
                errors["phone"] = "Please enter your mobile number."
            elif not is_valid_phone(cleaned_phone):
                errors["phone"] = "Invalid number. Must be 11 digits (e.g., 03...)."
            if not selected_time:
                errors["time"] = "Please select a departure time."

            if errors:
                    st.session_state.form_errors = errors
                    st.rerun()

            else:
                new_id = db.generate_booking_id()
                # Store the CLEANED CNIC
                current_bookings = db.load_bookings()
                current_bookings.append({
                    "id": new_id,
                    "name": cleaned_name,
                    "cnic": cleaned_cnic, 
                    "phone": cleaned_phone,
                    "time": selected_time,
                    "route": db.ROUTE,
                    "status": "confirmed"
                })
                db.save_bookings(current_bookings)

                # Use the formatter for the success message!
                formatted_cnic = db.format_cnic(cleaned_cnic)
                summary_text = (
                    "📋 Submitted Details:\n"
                    f"- Name: {cleaned_name}\n"
                    f"- CNIC: {formatted_cnic}\n"
                    f"- Phone: {cleaned_phone}\n"
                    f"- Time: {selected_time}"
                )

                st.session_state.messages.append({"role": "user", "content": summary_text})
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"✅ Your seat is successfully booked from {db.ROUTE}!\n\nAppointment Number: {new_id}\n\nPlease save this number to check your status or cancel later."
                })
                st.session_state.booking_stage = None
                reset_booking_form_state()
                st.rerun()

        
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

    if st.session_state.booking_stage == "awaiting_booking_info":
        render_booking_form()

question = st.chat_input("Ask about your document, or say 'I want to book a seat'...")

# =====================================================
# Core Router
# =====================================================
def route_message(question):
    stage = st.session_state.booking_stage

    if stage == "awaiting_booking_info":
        st.session_state.booking_stage = None
        reset_booking_form_state()
        stage = None

    if stage in ("awaiting_id_for_status", "awaiting_id_for_cancel"):
        booking_id = extract_booking_id(question)

        if booking_id:
            st.session_state.booking_stage = None
            if stage == "awaiting_id_for_status":
                return handle_status(booking_id)
            return handle_cancel(booking_id)

        if wants_to_stop(question):
            st.session_state.booking_stage = None
            return "No problem, I've cleared that request. Let me know if you need anything else!"

        intent = agent.classify_intent(question)

        if intent == "BOOK":
            st.session_state.booking_stage = "awaiting_booking_info"
            return "Sure! Please fill out the booking form below with your details:"

        if intent == "SUPPORT":
            st.session_state.booking_stage = None
            return "Connecting you to our support team... 📞 support@busstand.com | 0300-1234567"

        if intent == "DOCUMENT":
            doc_answer = agent.ask_document(question)
            if "I don't know based on the provided document" not in doc_answer:
                st.session_state.booking_stage = None
                return doc_answer

        return "That doesn't look like a valid appointment number. Please send just the number (e.g., 256)."

    intent = agent.classify_intent(question)

    if intent == "BOOK":
        st.session_state.booking_stage = "awaiting_booking_info"
        return "Sure! Please fill out the booking form below with your details:"

    if intent == "STATUS":
        booking_id = extract_booking_id(question)
        if booking_id:
            return handle_status(booking_id)
        st.session_state.booking_stage = "awaiting_id_for_status"
        return "Sure, please share your appointment number so I can look it up."

    # 1. Detect the intent (In message processing loop)
    if intent == "HISTORY":
        st.session_state.booking_stage = "viewing_history"
        st.rerun()
    # 2. Render the form if the stage is active
    if st.session_state.get("booking_stage") == "viewing_history":
        render_history_lookup_form()

    if intent == "CANCEL":
        booking_id = extract_booking_id(question)
        if booking_id:
            return handle_cancel(booking_id)
        st.session_state.booking_stage = "awaiting_id_for_cancel"
        return "Sure, please share your appointment number so I can cancel it."

    if intent == "SUPPORT":
        return "Connecting you to our support team... 📞 support@busstand.com | 0300-1234567"

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
        for word in answer.split():
            typed_answer += word + " "
            placeholder.markdown(bubble_html("assistant", typed_answer, cursor=True), unsafe_allow_html=True)
            time.sleep(0.02)

        placeholder.markdown(bubble_html("assistant", typed_answer), unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()