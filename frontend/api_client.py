import requests
import streamlit as st

BASE_URL = "http://localhost:8000"


def _handle(resp):
    if resp.status_code >= 400:
        st.error(f"API error {resp.status_code}: {resp.text}")
        return None
    return resp.json()


def get(path):
    return _handle(requests.get(f"{BASE_URL}{path}"))


def post(path, payload):
    return _handle(requests.post(f"{BASE_URL}{path}", json=payload))


def put(path, payload):
    return _handle(requests.put(f"{BASE_URL}{path}", json=payload))


def delete(path):
    return _handle(requests.delete(f"{BASE_URL}{path}"))


def upload_file(path, uploaded_file, category="Uploaded"):
    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
    data = {"category": category}
    return _handle(requests.post(f"{BASE_URL}{path}", files=files, data=data))


def set_flash(message, kind="success"):
    """Queue a message to be shown after the next rerun (e.g. right before st.rerun())."""
    st.session_state["_flash"] = (kind, message)


def show_flash():
    """Call near the top of a page to display and clear any queued flash message."""
    if "_flash" in st.session_state:
        kind, message = st.session_state.pop("_flash")
        getattr(st, kind)(message)
