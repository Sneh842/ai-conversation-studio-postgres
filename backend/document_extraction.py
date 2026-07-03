"""
Extracts text from uploaded files and splits it into reasonably-sized
chunks so each becomes its own retrievable knowledge source row.
"""
import io
from pypdf import PdfReader


def extract_text(filename: str, file_bytes: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    # plain text / markdown fallback
    return file_bytes.decode("utf-8", errors="ignore")


def chunk_text(text: str, max_words: int = 150):
    """Simple word-count chunking with paragraph awareness. Good enough
    for a hackathon RAG demo; a production system would use a smarter
    splitter (e.g. recursive character/semantic chunking)."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        words = para.split()
        if current_len + len(words) > max_words and current:
            chunks.append(" ".join(current))
            current, current_len = [], 0
        current.extend(words)
        current_len += len(words)

    if current:
        chunks.append(" ".join(current))

    return [c for c in chunks if len(c.split()) > 10]  # drop tiny fragments
