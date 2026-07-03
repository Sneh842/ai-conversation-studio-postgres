import streamlit as st
from api_client import get, post, delete, upload_file, set_flash, show_flash

st.set_page_config(page_title="Knowledge Base", page_icon="📚", layout="wide")
st.title("Knowledge Base")
st.caption("Real documents and manual entries that assistants retrieve from when answering prompts.")

show_flash()

with st.expander("Upload a real document (PDF or .txt)", expanded=True):
    category = st.text_input("Category for this document", value="Uploaded", key="upload_category")
    uploaded = st.file_uploader("Choose a file", type=["pdf", "txt", "md"])
    if uploaded is not None and st.button("Process and add to knowledge base"):
        with st.spinner("Extracting and chunking text..."):
            result = upload_file("/knowledge/upload", uploaded, category=category or "Uploaded")
        if result:
            set_flash(f"Added {result['chunks_created']} chunk(s) from {result['filename']}.")
            st.rerun()

with st.expander("Or add a source manually", expanded=False):
    with st.form("new_source"):
        title = st.text_input("Title")
        category2 = st.text_input("Category", placeholder="e.g. Policy, Technical, Sales")
        content = st.text_area("Content", height=150)
        if st.form_submit_button("Add source"):
            if title and content:
                post("/knowledge", {"title": title, "category": category2 or "General", "content": content})
                set_flash(f"Added knowledge source '{title}'.")
                st.rerun()
            else:
                st.warning("Title and content are required.")

st.markdown("---")

sources = get("/knowledge") or []
st.write(f"**{len(sources)} knowledge source(s)**")

for s in sources:
    with st.container(border=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"**{s['title']}**  \n`{s['category']}`")
            st.write(s["content"])
        with col2:
            if st.button("Delete", key=f"del_{s['id']}"):
                delete(f"/knowledge/{s['id']}")
                set_flash(f"Deleted '{s['title']}'.")
                st.rerun()
