import streamlit as st
from api_client import get

st.set_page_config(page_title="AI Conversation Studio", page_icon="🧭", layout="wide")

st.title("AI Conversation Studio")
st.caption("Knowledge management, testing, evaluation, feedback, governance and analytics for enterprise AI assistants.")

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

analytics = get("/analytics") or {}

col1.metric("Total conversations", analytics.get("total_conversations", 0))
col2.metric("Avg overall score", analytics.get("avg_overall_score", 0))
col3.metric("Avg hallucination risk", analytics.get("avg_hallucination_risk", 0))
col4.metric("Flagged for review", analytics.get("flagged_count", 0))

st.markdown("---")

st.subheader("How to use this studio")
st.markdown(
    """
    1. **Knowledge Base** — add or review the knowledge sources assistants can draw on.
    2. **Playground** — send a test prompt to an assistant and see the response, what it retrieved, and its evaluation.
    3. **Evaluation History** — browse every past conversation with its relevance, groundedness, and hallucination-risk scores.
    4. **Governance** — review conversations that were auto-flagged as high hallucination risk.
    5. **Analytics** — track quality trends across assistants over time.

    Use the sidebar to navigate between pages.
    """
)

st.info(
    "This is a working prototype built for a 24-hour hackathon. The LLM layer is mocked "
    "and the knowledge base is simulated, per the challenge constraints — see the Solution "
    "Document for assumptions and what a production version would add."
)
