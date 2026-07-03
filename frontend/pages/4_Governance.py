import streamlit as st
from api_client import get, put, set_flash, show_flash

st.set_page_config(page_title="Governance", page_icon="🛡", layout="wide")
st.title("Governance")
st.caption("Conversations auto-flagged for high hallucination risk or missing knowledge grounding, pending human review.")

show_flash()

items = get("/governance") or []
pending = [i for i in items if i["status"] == "pending"]
reviewed = [i for i in items if i["status"] != "pending"]

st.write(f"**{len(pending)} pending review**, {len(reviewed)} reviewed")

for item in pending:
    with st.container(border=True):
        st.markdown(f"**Conversation #{item['conversation_id']}**  \nHallucination risk: `{item['hallucination_risk']}`")
        st.write("**Prompt:**", item["prompt"])
        st.write("**Response:**", item["response"])
        st.write("**Why flagged:**", item["explanation"])

        col1, col2, col3 = st.columns([1, 1, 3])
        note = col3.text_input("Reviewer note", key=f"note_{item['id']}")
        if col1.button("Approve", key=f"approve_{item['id']}"):
            put(f"/governance/{item['id']}", {"status": "approved", "reviewer_note": note})
            set_flash(f"Conversation #{item['conversation_id']} approved.")
            st.rerun()
        if col2.button("Reject", key=f"reject_{item['id']}"):
            put(f"/governance/{item['id']}", {"status": "rejected", "reviewer_note": note})
            set_flash(f"Conversation #{item['conversation_id']} rejected.")
            st.rerun()

if reviewed:
    st.markdown("---")
    st.subheader("Reviewed")
    for item in reviewed:
        status_icon = "✅" if item["status"] == "approved" else "❌"
        with st.expander(f"{status_icon} Conversation #{item['conversation_id']} — {item['status']}"):
            st.write("**Prompt:**", item["prompt"])
            st.write("**Response:**", item["response"])
            st.write("**Reviewer note:**", item.get("reviewer_note") or "—")
