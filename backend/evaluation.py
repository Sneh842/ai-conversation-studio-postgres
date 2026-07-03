"""
Evaluation engine.

Rule-based (not another LLM call) so every score is deterministic,
reproducible, free to run, and fully explainable - we can show exactly
which sentence triggered which score. Groundedness now uses TF-IDF cosine
similarity rather than raw token overlap, which is far more robust on
real free-text LLM output (paraphrasing, reordering, extra words).
"""
from knowledge import tokenize, tfidf_similarity

GROUNDEDNESS_THRESHOLD = 0.15  # cosine similarity below this = ungrounded sentence


def _sentence_grounded(sentence: str, source_texts: list) -> bool:
    if not tokenize(sentence):
        return True  # nothing substantive to check, don't penalize
    for src_text in source_texts:
        if tfidf_similarity(sentence, src_text) >= GROUNDEDNESS_THRESHOLD:
            return True
    return False


def evaluate_response(prompt: str, response: str, used_sources: list):
    """
    used_sources: list of dicts with at least 'content' and 'title'
    Returns dict with scores (0-1) and a human-readable explanation.
    """
    source_texts = [s["content"] for s in used_sources]

    # --- Relevance: response should be topically similar to the prompt ---
    relevance = tfidf_similarity(prompt, response)
    relevance = min(relevance * 2.0, 1.0)  # scale up - overlap is naturally partial

    # --- Groundedness: fraction of sentences traceable to a source ---
    sentences = [s.strip() for s in response.split(".") if s.strip()]
    if not sentences:
        groundedness = 0.0
        ungrounded = []
    else:
        grounded_flags = [_sentence_grounded(s, source_texts) for s in sentences]
        groundedness = sum(grounded_flags) / len(sentences)
        ungrounded = [s for s, g in zip(sentences, grounded_flags) if not g]

    hallucination_risk = round(1 - groundedness, 2)
    overall = round((relevance * 0.3 + groundedness * 0.7), 2)

    flagged = hallucination_risk >= 0.3 or not used_sources

    explanation_lines = []
    if not used_sources:
        explanation_lines.append("No knowledge source was retrieved for this prompt.")
    else:
        src_titles = ", ".join(s["title"] for s in used_sources)
        explanation_lines.append(f"Retrieved sources: {src_titles}.")
    if ungrounded:
        explanation_lines.append(
            f"{len(ungrounded)} sentence(s) not traceable to any source (TF-IDF similarity below {GROUNDEDNESS_THRESHOLD}): "
            + " | ".join(f'"{s}."' for s in ungrounded)
        )
    else:
        explanation_lines.append("All sentences are traceable to retrieved sources.")

    return {
        "relevance_score": round(relevance, 2),
        "groundedness_score": round(groundedness, 2),
        "hallucination_risk": hallucination_risk,
        "overall_score": overall,
        "flagged": flagged,
        "explanation": " ".join(explanation_lines),
    }
