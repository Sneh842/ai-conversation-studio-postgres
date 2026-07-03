import streamlit as st
import pandas as pd
from api_client import get

st.set_page_config(page_title="Evaluation History", page_icon="📋", layout="wide")
st.title("Evaluation History")
st.caption("Every conversation, with its automated evaluation scores.")

conversations = get("/conversations") or []

if not conversations:
    st.info("No conversations yet. Go to the Playground to test a prompt.")
else:
    df = pd.DataFrame(conversations)
    df_display = df[[
        "id", "prompt", "response", "relevance_score", "groundedness_score",
        "hallucination_risk", "overall_score", "flagged", "created_at"
    ]].rename(columns={
        "id": "ID", "prompt": "Prompt", "response": "Response",
        "relevance_score": "Relevance", "groundedness_score": "Groundedness",
        "hallucination_risk": "Hallucination risk", "overall_score": "Overall",
        "flagged": "Flagged", "created_at": "Time"
    })
    df_display["Flagged"] = df_display["Flagged"].map({1: "⚠ Yes", 0: "No"})

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Inspect a conversation")
    selected_id = st.selectbox("Conversation ID", df["id"].tolist())
    row = df[df["id"] == selected_id].iloc[0]
    st.write("**Prompt:**", row["prompt"])
    st.write("**Response:**", row["response"])
    st.write("**Explanation:**", row["explanation"])
