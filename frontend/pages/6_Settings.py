import streamlit as st
from api_client import get, post, set_flash, show_flash

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
st.title("Settings")
st.caption("Connect a real LLM. Without a key, the studio runs on a deterministic mock generator so the demo never breaks.")

show_flash()

settings = get("/settings") or {}

if settings.get("gemini_api_key_set"):
    st.success(f"Gemini API key connected: `{settings.get('gemini_api_key_preview')}`")
else:
    st.warning("No API key configured — currently running on the mock generator.")

st.markdown("---")
st.subheader("Get a free Gemini API key (about 2 minutes, no credit card)")
st.markdown(
    """
    1. Go to **[aistudio.google.com](https://aistudio.google.com/apikey)**
    2. Sign in with any Google account
    3. Click **Create API key**
    4. Copy the key and paste it below
    """
)

with st.form("api_key_form"):
    api_key = st.text_input("Gemini API key", type="password", placeholder="AIza...")
    submitted = st.form_submit_button("Save key")
    if submitted and api_key:
        post("/settings", {"gemini_api_key": api_key})
        set_flash("Key saved. New conversations in the Playground will now use the real model.")
        st.rerun()

st.markdown("---")
st.subheader("How this is used")
st.markdown(
    """
    - When a key is set, the **Playground** sends your prompt plus the retrieved knowledge
      chunks to Gemini and generates a real, grounded answer.
    - Every response is still run through the same evaluation engine (relevance, groundedness,
      hallucination risk) regardless of whether it came from the real model or the mock.
    - If the real call ever fails (bad key, rate limit, no internet), the system automatically
      falls back to the mock generator so your demo keeps working — this is shown as
      `mock_fallback` in the conversation history, with the error message preserved for
      debugging.
    """
)
