import streamlit as st
import pandas as pd
import json
import os
import requests

# --- Config ---
st.set_page_config(page_title="Fraoula Chatbot", layout="wide")

DATA_STORE = "knowledge_data.json"
DEV_PASSWORD = "fraoula123" # Consider moving this to st.secrets as well for production

# Safely get API key from Streamlit secrets
try:
    API_KEY = st.secrets["openrouter"]["api_key"]
except KeyError:
    st.error("Error: OpenRouter API key not found in Streamlit secrets. "
             "Please add it to your `secrets.toml` file like:\n"
             "```toml\n[openrouter]\napi_key=\"sk-YOUR_API_KEY\"\n```")
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
        word-wrap: break-word;
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
        word-wrap: break-word;
    }}
    </style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def save_data(full_text):
    try:
        with open(DATA_STORE, "w", encoding="utf-8") as f:
            json.dump({"data": full_text}, f, ensure_ascii=False)
        # st.success moved to where it's contextually appropriate (after upload success)
    except Exception as e:
        st.error(f"❌ Error saving data to `{DATA_STORE}`: {e}")

def load_data():
    if not os.path.exists(DATA_STORE):
        return ""
    try:
        with open(DATA_STORE, "r", encoding="utf-8") as f:
            return json.load(f).get("data", "")
    except json.JSONDecodeError:
        st.error(f"❌ Error decoding JSON from `{DATA_STORE}`. File might be corrupted or empty.")
        return ""
    except Exception as e:
        st.error(f"❌ Error loading data from `{DATA_STORE}`: {e}")
        return ""

# --- UI Layout ---
tab1, tab2 = st.tabs(["Dev", "User"])

# --- Developer Panel ---
with tab1:
    st.header("Developer Login")
    if "dev_auth" not in st.session_state:
        st.session_state.dev_auth = False
    
    # Initialize session state for processed text and filename if not present
    if "processed_upload_text" not in st.session_state:
        st.session_state.processed_upload_text = None
    if "last_upload_filename" not in st.session_state:
        st.session_state.last_upload_filename = None

    if not st.session_state.dev_auth:
        password = st.text_input("Enter Developer Password", type="password", key="dev_password_input")
        if st.button("Login", key="dev_login_button"):
            if password == DEV_PASSWORD:
                st.session_state.dev_auth = True
                st.rerun() # Rerun to hide password input immediately
            else:
                st.error("❌ Incorrect password.")
    else:
        st.subheader("Upload Knowledge File")
        uploaded_file = st.file_uploader("Upload CSV, JSON, TXT, or Excel (.xlsx)", type=["csv", "json", "txt", "xlsx"])

        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()
            raw_text = "" # This will hold the text extracted from the file
            df_temp = None # Used for pandas processing, not for direct display in body

            try:
                # Process file based on type
                if file_type == "csv":
                    try:
                        df_temp = pd.read_csv(uploaded_file, encoding="utf-8")
                    except UnicodeDecodeError:
                        uploaded_file.seek(0) # Reset file pointer for re-reading
                        df_temp = pd.read_csv(uploaded_file, encoding="ISO-8859-1")
                    raw_text = df_temp.to_string(index=False)
                elif file_type == "json":
                    data = json.load(uploaded_file)
                    raw_text = json.dumps(data, indent=2, ensure_ascii=False)
                    # For JSON, df_temp might be created for internal processing but not directly displayed
                    if isinstance(data, list) and all(isinstance(i, dict) for i in data):
                        df_temp = pd.DataFrame(data)
                    elif isinstance(data, dict):
                        df_temp = pd.json_normalize(data)
                elif file_type == "txt":
                    raw_text = uploaded_file.read().decode("utf-8")
                elif file_type == "xlsx":
                    df_temp = pd.read_excel(uploaded_file, engine='openpyxl')
                    raw_text = df_temp.to_string(index=False)

                # Save the processed raw_text to the knowledge_data.json file
                save_data(raw_text)
                st.success(f"✅ File '{uploaded_file.name}' processed and saved to knowledge base.")

                # Store processed text and filename in session state for download button
                st.session_state.processed_upload_text = raw_text
                st.session_state.last_upload_filename = uploaded_file.name

            except Exception as e:
                st.error(f"❌ Failed to process file '{uploaded_file.name}': {e}")
                st.session_state.processed_upload_text = None # Clear on error
                st.session_state.last_upload_filename = None
        
        # Display download button if there's processed text in session state from a successful upload
        if st.session_state.processed_upload_text:
            st.download_button(
                label=f"Download Last Processed File ({st.session_state.last_upload_filename.split('.')[0]}_processed.txt)",
                data=st.session_state.processed_upload_text.encode("utf-8"), # Data must be bytes
                file_name=f"{st.session_state.last_upload_filename.split('.')[0]}_processed.txt",
                mime="text/plain",
                key="download_processed_knowledge_button" # Unique key
            )
            st.info("The download button shows the content of the *last successfully uploaded* and processed file.")
        else:
            st.info("Upload a file above to process it and enable the download option for the chunk.")


        st.subheader("Current Knowledge Base (Content used by the bot)")
        # This text area always displays the content of the DATA_STORE file
        current_knowledge_content = load_data()
        if current_knowledge_content:
            st.text_area("Full Knowledge Data:", current_knowledge_content, height=300, key="current_knowledge_display", disabled=True)
            if st.button("Clear Knowledge Base", key="clear_knowledge_button"):
                save_data("") # Clear the data file
                st.session_state.processed_upload_text = None # Clear session state for download
                st.session_state.last_upload_filename = None
                st.success("Knowledge base cleared.")
                st.rerun() # Rerun to reflect the cleared state
        else:
            st.info("The knowledge base is currently empty.")


# --- Chat UI ---
with tab2:
    st.title("Fraoula")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    context = load_data() # Load context for the chatbot

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
            # Append user message first so it appears immediately
            st.session_state.chat_history.append({"role": "user", "content": user_msg})

            messages = []
            # Construct system message based on context availability
            if context:
                system_instruction = (
                    f"You are Fraoula, a helpful AI assistant. Answer questions based *strictly* on the "
                    f"following knowledge provided. If the answer is not in the provided knowledge, "
                    f"state that you don't have enough information. Do not make up answers.\n"
                    f"Knowledge: {context}"
                )
            else:
                system_instruction = (
                    "You are Fraoula, a helpful AI assistant. Answer questions to the best of your ability. "
                    "If you don't know something, you can say so."
                )
            messages.append({"role": "system", "content": system_instruction})

            # Add previous chat history for continuity (excluding the very last user message just appended)
            # This ensures chat history is sent in order, with the *current* user message at the very end
            for msg in st.session_state.chat_history[:-1]:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})

            # Append the current user message as the final message in the sequence
            messages.append({"role": "user", "content": user_msg})

            payload = {
                "model": "meta-llama/llama-3.3-8b-instruct:free",
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7,
                "top_p": 0.9,
            }

            with st.spinner("Thinking..."):
                try:
                    res = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
                    res.raise_for_status()
                    bot_reply = res.json()["choices"][0]["message"]["content"]
                except requests.exceptions.RequestException as req_e:
                    bot_reply = f"❌ Network or API error: {req_e}. Please check your connection and API key."
                except json.JSONDecodeError:
                    bot_reply = "❌ Error: Could not decode JSON response from the API. Invalid API response."
                except IndexError:
                    bot_reply = "❌ Error: API response did not contain expected message structure (e.g., missing 'choices' or 'message' in response)."
                except Exception as e:
                    bot_reply = f"❌ An unexpected error occurred: {e}"

            st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
            st.rerun() # Rerun to display the new messages
