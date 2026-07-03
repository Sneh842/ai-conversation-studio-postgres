"""
Orchestrates response generation: tries a real LLM (Google Gemini) if an
API key is configured, otherwise - or if the real call fails for any
reason - falls back to the deterministic mock generator.

This graceful-degradation design is intentional: a live demo should never
hard-crash because of a missing/invalid key or a network hiccup.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from knowledge import retrieve_relevant_sources
from mock_llm import generate_mock
from settings_store import get_gemini_api_key

_executor = ThreadPoolExecutor(max_workers=4)


def _call_gemini_with_hard_timeout(prompt: str, context_chunks: list, api_key: str, timeout: int = 20) -> str:
    """Guarantees the call returns or raises within `timeout` seconds,
    regardless of what the underlying SDK's own timeout handling does."""
    future = _executor.submit(_call_gemini, prompt, context_chunks, api_key)
    try:
        return future.result(timeout=timeout)
    except FutureTimeoutError:
        raise TimeoutError(f"Gemini call did not respond within {timeout}s")

SYSTEM_INSTRUCTION = (
    "You are an enterprise assistant. Answer the user's question using ONLY "
    "the context provided below. If the context does not contain the answer, "
    "say you don't have information on this topic rather than guessing. "
    "Be concise - 2 to 4 sentences."
)


def _call_gemini(prompt: str, context_chunks: list, api_key: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    context_text = "\n\n".join(
        f"[Source: {c['title']}]\n{c['content']}" for c in context_chunks
    )
    full_prompt = f"Context:\n{context_text}\n\nQuestion: {prompt}"

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            http_options=types.HttpOptions(timeout=15_000),  # ms
        ),
    )
    return response.text.strip()


def generate_response(prompt: str, hallucination_bias: float = 0.15):
    """
    Returns dict:
      response, used_source_ids, retrieval_debug, generation_mode, error
    generation_mode is one of: "real", "mock", "mock_fallback"
    """
    retrieved = retrieve_relevant_sources(prompt, top_k=3)
    retrieval_debug = [
        {
            "source_id": src["id"],
            "source_title": src["title"],
            "match_score": round(score, 3),
            "matched_terms": terms,
        }
        for score, src, terms in retrieved
    ]
    used_ids = [src["id"] for _, src, _ in retrieved]
    context_chunks = [src for _, src, _ in retrieved]

    api_key = get_gemini_api_key()

    if not api_key:
        response_text, mock_used_ids = generate_mock(prompt, retrieved, hallucination_bias)
        return {
            "response": response_text,
            "used_source_ids": mock_used_ids,
            "retrieval_debug": retrieval_debug,
            "generation_mode": "mock",
            "error": None,
        }

    if not context_chunks:
        # No relevant knowledge found - still worth a real call so the
        # assistant can say "I don't know" in its own voice, but it's
        # useful to flag that nothing was retrieved.
        try:
            text = _call_gemini_with_hard_timeout(prompt, [], api_key)
            return {
                "response": text,
                "used_source_ids": [],
                "retrieval_debug": retrieval_debug,
                "generation_mode": "real",
                "error": None,
            }
        except Exception as e:
            response_text, mock_used_ids = generate_mock(prompt, retrieved, hallucination_bias)
            return {
                "response": response_text,
                "used_source_ids": mock_used_ids,
                "retrieval_debug": retrieval_debug,
                "generation_mode": "mock_fallback",
                "error": str(e),
            }

    try:
        text = _call_gemini_with_hard_timeout(prompt, context_chunks, api_key)
        return {
            "response": text,
            "used_source_ids": used_ids,
            "retrieval_debug": retrieval_debug,
            "generation_mode": "real",
            "error": None,
        }
    except Exception as e:
        response_text, mock_used_ids = generate_mock(prompt, retrieved, hallucination_bias)
        return {
            "response": response_text,
            "used_source_ids": mock_used_ids,
            "retrieval_debug": retrieval_debug,
            "generation_mode": "mock_fallback",
            "error": str(e),
        }
