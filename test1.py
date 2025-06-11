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

# --- Theme Colors (Fraoula Violet) ---
PRIMARY_COLOR = "#9400D3"
SECONDARY_COLOR = "#C779D9"
BACKGROUND_COLOR = "#1E003E"
TEXT_COLOR = "#FFFFFF"

# --- Styling ---
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {BACKGROUND_COLOR};
        color: {TEXT_COLOR};
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }}
    .stTextInput > div > div > input {{
        background-color: #2a004f;
        border: 2px solid {PRIMARY_COLOR};
        border-radius: 8px;
        color: {TEXT_COLOR};
        padding: 10px;
    }}
    .stButton > button {{
        background-color: {PRIMARY_COLOR};
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        border: none;
        cursor: pointer;
    }}
    .stButton > button:hover {{
        background-color: {SECONDARY_COLOR};
    }}
    .user-message {{
        background-color: {SECONDARY_COLOR};
        padding: 10px;
        border-radius: 12px 12px 0 12px;
        margin: 8px 0;
        text-align: right;
        max-width: 75%;
        margin-left: auto;
        color: white;
        font-size: 1rem;
    }}
    .bot-message {{
        background-color: #3b0070;
        padding: 10px;
        border-radius: 12px 12px 12px 0;
        margin: 8px 0;
        text-align: left;
        max-width: 75%;
        margin-right: auto;
        color: {TEXT_COLOR};
        font-size: 1rem;
    }}
    </style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def save_data(full_text):
    with open(DATA_STORE, "w", encoding="utf-8") as f:
        json.dump({"data": full_text}, f)

def load_data():
    if not os.path.exists(DATA_STORE):
        return ""
    with open(DATA_STORE, "r", encoding="utf-8") as f:
        return json.load(f).get("data", "")

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
        st.subheader("Upload Files")
        uploaded_file = st.file_uploader("Upload CSV, JSON, TXT, or Excel (.xlsx)", type=["csv", "json", "txt", "xlsx"])

        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()
            raw_text = ""
            df_preview = None

            try:
                if file_type == "csv":
                    try:
                        df_preview = pd.read_csv(uploaded_file, encoding="utf-8")
                    except UnicodeDecodeError:
                        df_preview = pd.read_csv(uploaded_file, encoding="ISO-8859-1")
                    raw_text = df_preview.to_string(index=False)
                elif file_type == "json":
                    data = json.load(uploaded_file)
                    raw_text = json.dumps(data, indent=2)
                    if isinstance(data, list):
                        df_preview = pd.DataFrame(data)
                    elif isinstance(data, dict):
                        df_preview = pd.json_normalize(data)
                elif file_type == "txt":
                    raw_text = uploaded_file.read().decode("utf-8")
                elif file_type == "xlsx":
                    df_preview = pd.read_excel(uploaded_file, engine='openpyxl')
                    raw_text = df_preview.to_string(index=False)

                save_data(raw_text)
                st.success("✅ File uploaded and saved to `knowledge_data.json`.")

                if df_preview is not None:
                    st.subheader("Data Preview")
                    st.dataframe(df_preview)
                else:
                    st.text_area("Preview", raw_text, height=200)

            except Exception as e:
                st.error(f"❌ Failed to read file: {e}")

# --- Chat UI ---
with tab2:
    st.title("Fraoula")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    context = load_data()

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
            if context:
                messages.append({"role": "system", "content": f"Use this knowledge:\n{context}"})
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
