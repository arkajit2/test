import streamlit as st
import pandas as pd
import json
import os
import requests

# --- Config ---
st.set_page_config(page_title="Fraoula Chatbot", layout="wide")

DATA_STORE = "knowledge_data.json"
DEV_PASSWORD = "fraoula123"

API_KEY = st.secrets["openrouter"]["api_key"]
API_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# --- Styling ---
st.markdown("""
    <style>
    .stApp {
        background-color: #1E003E;
        color: #FFFFFF;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stTextInput > div > div > input {
        background-color: #2a004f;
        border: 2px solid #9400D3;
        border-radius: 8px;
        color: #FFFFFF;
        padding: 10px;
    }
    .stButton > button {
        background-color: #9400D3;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        border: none;
        cursor: pointer;
    }
    .stButton > button:hover {
        background-color: #C779D9;
    }
    .user-message {
        background-color: #C779D9;
        padding: 10px;
        border-radius: 12px 12px 0 12px;
        margin: 8px 0;
        text-align: right;
        max-width: 75%;
        margin-left: auto;
        color: white;
        font-size: 1rem;
    }
    .bot-message {
        background-color: #3b0070;
        padding: 10px;
        border-radius: 12px 12px 12px 0;
        margin: 8px 0;
        text-align: left;
        max-width: 75%;
        margin-right: auto;
        color: #FFFFFF;
        font-size: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def save_data(new_text, filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    else:
        existing_data = {"data": []}

    if new_text not in existing_data["data"]:
        existing_data["data"].append(new_text)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2)

def load_data(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f).get("data", [])

# --- UI Layout ---
tab1, tab2 = st.tabs(["Dev", "User"])

# --- Developer Panel ---
with tab1:
    st.header("Developer Login")
    if "dev_auth" not in st.session_state:
        st.session_state.dev_auth = False

    if not st.session_state.dev_auth:
        password = st.text_input("Enter Developer Password", type="password")
        if st.button("Login"):
            if password == DEV_PASSWORD:
                st.session_state.dev_auth = True
                st.success("Access granted")
            else:
                st.error("❌ Incorrect password.")
    else:
        st.subheader("Upload Knowledge Base Files")
        uploaded_file = st.file_uploader("Upload CSV, JSON, TXT, or Excel (.xlsx)", type=["csv", "json", "txt", "xlsx"])

        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()
            raw_text = ""
            df_preview = None

            try:
                if file_type == "csv":
                    df_preview = pd.read_csv(uploaded_file)
                    raw_text = df_preview.to_string(index=False)
                elif file_type == "json":
                    json_data = json.load(uploaded_file)
                    raw_text = json.dumps(json_data, indent=2)
                    df_preview = pd.json_normalize(json_data) if isinstance(json_data, dict) else pd.DataFrame(json_data)
                elif file_type == "txt":
                    raw_text = uploaded_file.read().decode("utf-8")
                elif file_type == "xlsx":
                    df_preview = pd.read_excel(uploaded_file)
                    raw_text = df_preview.to_string(index=False)

                save_data(raw_text, DATA_STORE)
                st.success("✅ Data added to knowledge base.")

                if df_preview is not None:
                    st.subheader("Preview of Uploaded Data")
                    st.dataframe(df_preview)
                else:
                    st.text_area("Preview of Uploaded Text", raw_text, height=200)

            except Exception as e:
                st.error(f"❌ Failed to read file: {e}")

        if os.path.exists(DATA_STORE):
            with open(DATA_STORE, "rb") as f:
                st.download_button(
                    label="📥 Download Full Knowledge Base",
                    data=f,
                    file_name="knowledge_data.json",
                    mime="application/json"
                )

# --- Chat UI ---
with tab2:
    st.title("Fraoula")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    context_list = load_data(DATA_STORE)
    combined_context = "\n\n---\n\n".join(context_list)

    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            css_class = "user-message" if msg["role"] == "user" else "bot-message"
            st.markdown(f'<div class="{css_class}">{msg["content"]}</div>', unsafe_allow_html=True)

    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([8, 2])
        with col1:
            user_input = st.text_input("You:", placeholder="Ask anything...")
        with col2:
            send_btn = st.form_submit_button("Send")

        if send_btn and user_input.strip():
            user_msg = user_input.strip()
            st.session_state.chat_history.append({"role": "user", "content": user_msg})

            messages = []
            if combined_context:
                messages.append({"role": "system", "content": f"Use this knowledge:\n{combined_context}"})
            messages += [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]

            payload = {
                "model": "meta-llama/llama-3.3-8b-instruct:free",
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.7
            }

            with st.spinner("Thinking..."):
                try:
                    res = requests.post(API_URL, headers=HEADERS, json=payload)
                    res.raise_for_status()
                    bot_reply = res.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    bot_reply = f"❌ Error: {e}"

            st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
            st.rerun()
