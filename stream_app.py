import streamlit as st
import json
import os
import sys

# Add ai_webapp folder to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "ai_webapp"))

from agent import run_agent_once

# --- CRITICAL ERROR: The following line must be DELETED! user_input is not defined here. ---
# reply = run_agent_once(user_input)


USERS_FILE = "users.json"

# Ensure user file exists
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump([], f)

# -----------------------
# USER REGISTRATION LOGIC
# -----------------------
def register_user(email):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)

    if email not in users:
        users.append(email)
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)
        return True
    return False

# --- MINOR ISSUE: The following UNUSED function can be DELETED! ---
# def agent_reply(message: str):
#     # Run your agent for one turn and return response
#     return run_agent_once(message)


# -----------------------
# STREAMLIT UI
# -----------------------
st.set_page_config(page_title="AI Weather Agent", page_icon="⛅", layout="centered")

st.title("🌦 AI Weather Chat Assistant")

# -------- Email Registration --------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("Register with Email to Continue")

    email = st.text_input("Enter your email")

    if st.button("Register"):
        if email.strip() == "":
            st.error("Email cannot be empty!")
        else:
            registered = register_user(email)
            st.session_state.authenticated = True
            st.session_state.email = email
            st.success(f"Welcome {email}! You can now chat with the agent.")
    st.stop()

# -----------------------
# CHAT INTERFACE
# -----------------------
st.subheader("Chat with the AI Agent 🤖")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display old messages
for msg in st.session_state.messages:
    sender, text = msg
    if sender == "user":
        st.chat_message("user").markdown(text)
    else:
        st.chat_message("assistant").markdown(text)

# Input box
user_input = st.chat_input("Ask about weather or anything...")

if user_input:
    st.session_state.messages.append(("user", user_input))
    st.chat_message("user").markdown(user_input)

    # AGENT RESPONSE - This is the correct place for the agent call.
    reply = run_agent_once(user_input)
    st.session_state.messages.append(("assistant", reply))

    st.chat_message("assistant").markdown(reply)
# run_agent_once(user_input: str) → returns one final response # This line is a comment/note, not code.