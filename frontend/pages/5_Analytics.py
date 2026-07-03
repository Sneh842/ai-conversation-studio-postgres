import streamlit as st
import pandas as pd
import plotly.express as px
from api_client import get

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
st.title("Analytics")
st.caption("Quality trends across all assistants and conversations.")

analytics = get("/analytics") or {}

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total conversations", analytics.get("total_conversations", 0))
c2.metric("Avg relevance", analytics.get("avg_relevance", 0))
c3.metric("Avg groundedness", analytics.get("avg_groundedness", 0))
c4.metric("Avg hallucination risk", analytics.get("avg_hallucination_risk", 0))

st.markdown("---")

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Score trend (most recent 20 conversations)")
    trend = analytics.get("recent_trend", [])
    if trend:
        df = pd.DataFrame(trend)
        fig = px.line(df, x="id", y=["overall_score", "hallucination_risk"],
                       labels={"id": "Conversation ID", "value": "Score", "variable": "Metric"},
                       markers=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data yet.")

with col_right:
    st.subheader("Hallucination risk by assistant")
    by_assistant = analytics.get("by_assistant", [])
    if by_assistant:
        df2 = pd.DataFrame(by_assistant)
        fig2 = px.bar(df2, x="name", y="avg_hallucination", color="name",
                       labels={"name": "Assistant", "avg_hallucination": "Avg hallucination risk"})
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No data yet.")

st.markdown("---")
st.subheader("Feedback breakdown")
fb = analytics.get("feedback_counts", [])
if fb:
    df3 = pd.DataFrame(fb)
    fig3 = px.pie(df3, names="rating", values="count")
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No feedback submitted yet.")
