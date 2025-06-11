import streamlit as st
import pandas as pd
import json
import os
import requests

# --- Config ---
st.set_page_config(page_title="Fraoula Chatbot", layout="wide")

DATA_STORE = "knowledge_data.json"
DEV_PASSWORD = "fraoula123"

# Safely get API key from Streamlit secrets
try:
    API_KEY = st.secrets["openrouter"]["api_key"]
except KeyError:
    st.error("Error: OpenRouter API key not found in Streamlit secrets. Please add it to your `secrets.toml` file.")
    st.stop() # Stop the app if API key is not found

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
        word-wrap: break-word; /* Added for long words/URLs */
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
        word-wrap: break-word; /* Added for long words/URLs */
    }}
    </style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def save_data(full_text):
    try:
        with open(DATA_STORE, "w", encoding="utf-8") as f:
            json.dump({"data": full_text}, f, ensure_ascii=False) # ensure_ascii=False for proper Unicode saving
        st.success(f"✅ Data successfully saved to `{DATA_STORE}`.")
    except Exception as e:
        st.error(f"❌ Error saving data: {e}")

def load_data():
    if not os.path.exists(DATA_STORE):
        return ""
    try:
        with open(DATA_STORE, "r", encoding="utf-8") as f:
            return json.load(f).get("data", "")
    except json.JSONDecodeError:
        st.error(f"❌ Error decoding JSON from `{DATA_STORE}`. File might be corrupted.")
        return ""
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return ""

# --- UI Layout ---
tab1, tab2 = st.tabs(["Dev", "User"])

# --- Developer Panel ---
with tab1:
    st.header("Developer Login")
    if "dev_auth" not in st.session_state:
        st.session_state.dev_auth = False

    if not st.session_state.dev_auth:
        password = st.text_input("Enter Developer Password", type="password", key="dev_password_input")
        if st.button("Login", key="dev_login_button"):
            if password == DEV_PASSWORD:
                st.session_state.dev_auth = True
                st.rerun() # Rerun to hide password input immediately
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
                        uploaded_file.seek(0) # Reset file pointer for re-reading
                        df_preview = pd.read_csv(uploaded_file, encoding="ISO-8859-1")
                    raw_text = df_preview.to_string(index=False)
                elif file_type == "json":
                    data = json.load(uploaded_file)
                    raw_text = json.dumps(data, indent=2, ensure_ascii=False)
                    if isinstance(data, list):
                        df_preview = pd.DataFrame(data)
                    elif isinstance(data, dict):
                        df_preview = pd.json_normalize(data)
                elif file_type == "txt":
                    raw_text = uploaded_file.read().decode("utf-8")
                elif file_type == "xlsx":
                    df_preview = pd.read_excel(uploaded_file, engine='openpyxl')
                    raw_text = df_preview.to_string(index=False)

                save_data(raw_text) # Call save_data here

                if df_preview is not None and not df_preview.empty: # Check if DataFrame is not empty
                    st.subheader("Data Preview")
                    st.dataframe(df_preview)
                elif raw_text: # Display raw text if no DataFrame preview
                    st.text_area("Preview of uploaded content:", raw_text, height=200)

            except Exception as e:
                st.error(f"❌ Failed to process file: {e}")
        
        st.subheader("Current Knowledge Base")
        current_knowledge = load_data()
        if current_knowledge:
            st.text_area("Existing Knowledge Data", current_knowledge, height=300, key="current_knowledge_display", disabled=True)
            if st.button("Clear Knowledge Base", key="clear_knowledge_button"):
                save_data("") # Clear the data
                st.success("Knowledge base cleared.")
                st.rerun()
        else:
            st.info("No knowledge data uploaded yet.")

# --- Chat UI ---
with tab2:
    st.title("Fraoula")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    context = load_data()

    # Display chat history within a scrollable container
    chat_messages_placeholder = st.container()
    
    with chat_messages_placeholder:
        for msg in st.session_state.chat_history:
            css_class = "user-message" if msg["role"] == "user" else "bot-message"
            st.markdown(f'<div class="{css_class}">{msg["content"]}</div>', unsafe_allow_html=True)

    # Input form for new messages
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([8, 2])
        with col1:
            user_input = st.text_input("You:", placeholder="Ask anything...", key="user_chat_input")
        with col2:
            send_btn = st.form_submit_button("Send")

        if send_btn and user_input.strip():
            user_msg = user_input.strip()
            st.session_state.chat_history.append({"role": "user", "content": user_msg})

            messages = []
            if context:
                # Provide clear instructions for using the context
                messages.append({"role": "system", "content": f"You are Fraoula, a helpful AI assistant. Answer questions based *strictly* on the following knowledge provided. If the answer is not in the provided knowledge, state that you don't have enough information. Do not make up answers.\nKnowledge: {context}"})
            else:
                messages.append({"role": "system", "content": "You are Fraoula, a helpful AI assistant. Answer questions to the best of your ability. If you don't know something, you can say so."})
            
            # Add previous chat history for continuity
            for msg in st.session_state.chat_history:
                if msg["role"] == "user" or msg["role"] == "assistant":
                    messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Ensure the last message is always the current user input
            # This handles cases where chat_history might be longer than desirable for the model
            # For longer histories, consider a summary or truncation strategy
            if messages[-1]["content"] != user_msg: # Prevent double-adding the user's message if already appended above
                 messages.append({"role": "user", "content": user_msg})


            payload = {
                "model": "meta-llama/llama-3.3-8b-instruct:free", # Using the specified model
                "messages": messages,
                "max_tokens": 500, # Increased max_tokens for potentially longer responses
                "temperature": 0.7,
                "top_p": 0.9, # Added top_p for more diverse responses
            }

            with st.spinner("Thinking..."):
                try:
                    res = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60) # Added timeout
                    res.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                    bot_reply = res.json()["choices"][0]["message"]["content"]
                except requests.exceptions.RequestException as req_e:
                    bot_reply = f"❌ Network or API error: {req_e}. Please check your connection and API key."
                except json.JSONDecodeError:
                    bot_reply = "❌ Error: Could not decode JSON response from the API. Invalid API response."
                except IndexError:
                    bot_reply = "❌ Error: API response did not contain expected message structure."
                except Exception as e:
                    bot_reply = f"❌ An unexpected error occurred: {e}"

            st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
            st.rerun()
