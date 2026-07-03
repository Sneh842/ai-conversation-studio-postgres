"""
Mock LLM generator. Used automatically when no real API key is configured,
or as a fallback if the real LLM call fails (see llm_service.py).

To make the Evaluation Studio demoable even without a real key, this
deliberately injects an occasional unsupported ("hallucinated") sentence,
at a rate controlled by the assistant's hallucination_bias.
"""
import random

UNSUPPORTED_FILLERS = [
    "This has been independently verified by third-party auditors.",
    "Industry benchmarks confirm this is true in over 95% of cases.",
    "Our internal studies from 2021 support this conclusion.",
    "This is the officially recommended approach in all regions.",
]


def generate_mock(prompt: str, retrieved: list, hallucination_bias: float = 0.15):
    """
    retrieved: list of (score, source_dict, matched_terms) from knowledge.retrieve_relevant_sources
    Returns (response_text, used_source_ids)
    """
    if not retrieved:
        response = (
            "I don't have a knowledge source covering this topic, so I can't "
            "answer with confidence. Could you point me to relevant documentation?"
        )
        return response, []

    sentences = []
    used_ids = []
    for score, src, matched_terms in retrieved:
        used_ids.append(src["id"])
        src_sentences = [s.strip() for s in src["content"].split(".") if s.strip()]
        for s in src_sentences[:2]:
            sentences.append(s + ".")

    if random.random() < hallucination_bias:
        sentences.append(random.choice(UNSUPPORTED_FILLERS))

    return " ".join(sentences), used_ids
