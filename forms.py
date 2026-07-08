import streamlit as st
import database as db
import re

# =====================================================
# Form Input Validation Helpers
# =====================================================
def is_valid_name(name_str):
    pattern = r"^(?=.*[A-Za-z])[A-Za-z0-9\s.\-]+$"
    return bool(re.match(pattern, name_str.strip()))

def is_valid_phone(phone_str):
    pattern = r"^03\d{9}$"
    return bool(re.match(pattern, phone_str.strip()))

def field_error(field_key):
    error_text = st.session_state.get("form_errors", {}).get(field_key)
    if error_text:
        st.markdown(
            f"<div style='color:#ff4d4d;font-size:0.82rem;margin:-8px 0 10px 2px;'>⚠ {error_text}</div>",
            unsafe_allow_html=True
        )

def reset_booking_form_state():
    for key in ["form_name_widget", "form_cnic_widget", "form_phone_widget", "form_time_widget", "form_errors"]:
        st.session_state.pop(key, None)

# =====================================================
# The UI Forms
# =====================================================
def render_history_lookup_form():
    with st.form(key="history_lookup_form"):
        st.markdown("### 🔍 Search Booking History")
        
        raw_cnic = st.text_input(
            "Enter your 13-digit CNIC", 
            placeholder="e.g., 3840312345671 or 38403-1234567-1",
            key="history_cnic_input"
        )
        
        # In Streamlit forms, you must use form_submit_button
        search_clicked = st.form_submit_button("View History")
        close_clicked = st.form_submit_button("Close Window")

        if close_clicked:
            st.session_state.booking_stage = None
            st.rerun()

        if search_clicked:
            clean_cnic = db.sanitize_cnic(raw_cnic)
            
            if len(clean_cnic) != 13 or not clean_cnic.isdigit():
                st.error("Invalid CNIC. Please enter 13 digits only (no letters).")
            else:
                matches = db.get_all_bookings_by_cnic(clean_cnic)
                
                if not matches:
                    st.warning("No booking history found for this CNIC.")
                else:
                    st.success(f"Found {len(matches)} booking(s):")
                    for b in matches:
                        st.info(db.format_booking(b))

def render_booking_form():
    st.write("")
    form_col, spacer_col = st.columns([2, 1])

    with form_col:
        with st.form(key="interactive_passenger_form"):
            st.markdown(f"### 🚌 {db.ROUTE} Booking Card")

            st.text_input("Enter your name", placeholder="e.g., Asif Khan", key="form_name_widget")
            field_error("name")
            
            st.text_input("Enter CNIC", placeholder="e.g., 3840312345671 (13 digits)", key="form_cnic_widget")
            field_error("cnic")

            st.text_input("Enter Mobile Number", placeholder="e.g., 03217654321", key="form_phone_widget")
            field_error("phone")

            st.radio(
                "Select Departure Time",
                options=["Morning (07:45 AM)", "Evening (09:15 PM)"],
                key="form_time_widget",
                horizontal=True,
                index=None
            )
            field_error("time")

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
            raw_cnic = st.session_state.form_cnic_widget.strip()
            cleaned_cnic = db.sanitize_cnic(raw_cnic)
            cleaned_phone = st.session_state.form_phone_widget.strip()
            selected_time = st.session_state.get("form_time_widget")

            errors = {}
            if not cleaned_name:
                errors["name"] = "Please enter your name."
            elif not is_valid_name(cleaned_name):
                errors["name"] = "Invalid name!"

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