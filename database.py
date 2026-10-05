import json
import os
import random
import re

ROUTE = "Skardu to Murree"
BOOKINGS_FILE = "bookings.json"


def sanitize_cnic(cnic_str):
    """Strips everything except digits. Returns clean 13-digit string."""
    return re.sub(r'\D', '', cnic_str)

def format_cnic(cnic_str):
    """Turns 13-digit clean string into display format: 00000-0000000-0"""
    clean = sanitize_cnic(cnic_str)
    if len(clean) != 13:
        return clean # Return original if invalid
    return f"{clean[:5]}-{clean[5:12]}-{clean[12]}"

def load_bookings():
    if not os.path.exists(BOOKINGS_FILE):
        return []
    with open(BOOKINGS_FILE, "r") as f:
        return json.load(f)


def save_bookings(bookings):
    with open(BOOKINGS_FILE, "w") as f:
        json.dump(bookings, f, indent=2)


def generate_booking_id():
    """Returns an ID no existing booking uses. Starts at 3 digits, grows if they run out."""
    taken = {b["id"] for b in load_bookings()}
    low, high = 100, 999
    while True:
        free = [str(n) for n in range(low, high + 1) if str(n) not in taken]
        if free:
            return random.choice(free)
        low, high = high + 1, high * 10 + 9


def find_booking(booking_id):
    for b in load_bookings():
        if b["id"] == str(booking_id).strip():
            return b
    return None

def get_all_bookings_by_cnic(clean_cnic):
    """Returns a list of all bookings matching the provided 13-digit CNIC."""
    all_bookings = load_bookings()
    # Filter list: keep only records that match the CNIC
    return [b for b in all_bookings if b['cnic'] == clean_cnic]

def cancel_booking(booking_id):
    """Marks a booking as cancelled. Returns True if found, False otherwise."""
    bookings = load_bookings()
    found = False
    for b in bookings:
        if b["id"] == str(booking_id).strip():
            b["status"] = "cancelled"
            found = True
            break
    if found:
        save_bookings(bookings)
    return found

def format_booking(booking):
    """Shared formatter for displaying existing records."""
    pretty_cnic = format_cnic(booking['cnic'])
    
    # 🕒 Pull the time from the booking, default to 'Not specified' for older entries
    booking_time = booking.get('time', 'Not specified')
    
    return (
        "Here are your booking details:\n\n"
        f"- Name: {booking['name']}\n"
        f"- CNIC: {pretty_cnic}\n"
        f"- Time: {booking_time}\n"
        f"- Phone: {booking['phone']}\n"
        f"- Route: {booking['route']}\n"
        f"- Status: {booking['status']}"
    )