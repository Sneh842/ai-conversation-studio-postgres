"""
Retrieval layer using TF-IDF + cosine similarity.

This is a genuine, production-recognized lightweight retrieval technique
(not a toy keyword match). It requires no internet connection and no model
download, which matters for a live hackathon demo on unreliable wifi.

Swap point: to upgrade to dense embeddings (sentence-transformers / a
vector DB), replace `_build_index()` and `retrieve_relevant_sources()`
below and keep the same return signature - nothing else needs to change.
"""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from database import db, rows_to_list

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "on",
    "for", "and", "or", "how", "what", "why", "does", "do", "can", "i",
    "we", "you", "it", "this", "that", "with", "be", "as", "at", "by",
}


def tokenize(text: str):
    """Used by the evaluation engine for sentence-level grounding checks."""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def _build_index(sources):
    corpus = [s["content"] + " " + s["title"] for s in sources]
    vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
    matrix = vectorizer.fit_transform(corpus)
    return vectorizer, matrix


def retrieve_relevant_sources(prompt: str, top_k: int = 3, min_score: float = 0.18):
    """
    Return top_k knowledge sources ranked by TF-IDF cosine similarity to the prompt.
    Returns list of (score, source_dict, matched_terms).
    """
    with db() as conn:
        sources = rows_to_list(conn.execute("SELECT * FROM knowledge_sources").fetchall())

    if not sources or not prompt.strip():
        return []

    vectorizer, matrix = _build_index(sources)
    prompt_vec = vectorizer.transform([prompt])
    scores = cosine_similarity(prompt_vec, matrix).flatten()

    feature_names = vectorizer.get_feature_names_out()
    prompt_terms = set(feature_names[i] for i in prompt_vec.nonzero()[1])

    ranked = sorted(zip(scores, sources), key=lambda x: x[0], reverse=True)

    results = []
    for score, src in ranked[:top_k]:
        if score < min_score:
            continue
        src_tokens = set(tokenize(src["content"] + " " + src["title"]))
        matched_terms = sorted(prompt_terms & src_tokens)
        results.append((float(score), src, matched_terms))

    return results


def tfidf_similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity between two arbitrary texts - used by the
    evaluation engine to score groundedness of a generated sentence
    against retrieved source content."""
    if not text_a.strip() or not text_b.strip():
        return 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform([text_a, text_b])
        return float(cosine_similarity(matrix[0], matrix[1])[0][0])
    except ValueError:
        return 0.0
