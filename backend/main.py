from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import json

from database import db, init_db, rows_to_list, row_to_dict
from models import KnowledgeSourceCreate, AssistantCreate, ChatRequest, FeedbackCreate, GovernanceReviewUpdate
from llm_service import generate_response
from evaluation import evaluate_response
from document_extraction import extract_text, chunk_text
from settings_store import get_settings, set_setting, get_gemini_api_key

app = FastAPI(title="AI Conversation Studio API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ------------------------------------------------------------------ Settings
@app.get("/settings")
def read_settings():
    settings = get_settings()
    key = settings.get("gemini_api_key", "")
    return {
        "gemini_api_key_set": bool(key or get_gemini_api_key()),
        "gemini_api_key_preview": (key[:4] + "..." + key[-4:]) if key else "",
    }


@app.post("/settings")
def update_settings(payload: dict):
    if "gemini_api_key" in payload:
        set_setting("gemini_api_key", payload["gemini_api_key"])
    return {"saved": True}


# ---------------------------------------------------------------- Assistants
@app.post("/assistants")
def create_assistant(payload: AssistantCreate):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO assistants (name, persona, hallucination_bias) VALUES (?, ?, ?)",
            (payload.name, payload.persona, payload.hallucination_bias),
        )
        return {"id": cur.lastrowid, **payload.dict()}


@app.get("/assistants")
def list_assistants():
    with db() as conn:
        return rows_to_list(conn.execute("SELECT * FROM assistants").fetchall())


# ------------------------------------------------------------- Knowledge base
@app.post("/knowledge")
def create_source(payload: KnowledgeSourceCreate):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO knowledge_sources (title, category, content) VALUES (?, ?, ?)",
            (payload.title, payload.category, payload.content),
        )
        return {"id": cur.lastrowid, **payload.dict()}


@app.post("/knowledge/upload")
async def upload_source(file: UploadFile = File(...), category: str = Form("Uploaded")):
    file_bytes = await file.read()
    text = extract_text(file.filename, file_bytes)
    if not text.strip():
        raise HTTPException(400, "Could not extract any text from this file.")

    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(400, "File was read but produced no usable chunks.")

    created = []
    with db() as conn:
        for i, chunk in enumerate(chunks):
            title = f"{file.filename} (part {i + 1}/{len(chunks)})"
            cur = conn.execute(
                "INSERT INTO knowledge_sources (title, category, content) VALUES (?, ?, ?)",
                (title, category, chunk),
            )
            created.append(cur.lastrowid)

    return {"filename": file.filename, "chunks_created": len(created), "ids": created}


@app.get("/knowledge")
def list_sources():
    with db() as conn:
        return rows_to_list(conn.execute("SELECT * FROM knowledge_sources ORDER BY id DESC").fetchall())


@app.delete("/knowledge/{source_id}")
def delete_source(source_id: int):
    with db() as conn:
        conn.execute("DELETE FROM knowledge_sources WHERE id = ?", (source_id,))
    return {"deleted": source_id}


# ---------------------------------------------------------------- Chat / test
@app.post("/chat")
def chat(payload: ChatRequest):
    with db() as conn:
        assistant = row_to_dict(
            conn.execute("SELECT * FROM assistants WHERE id = ?", (payload.assistant_id,)).fetchone()
        )
    if not assistant:
        raise HTTPException(404, "Assistant not found")

    result = generate_response(payload.prompt, hallucination_bias=assistant["hallucination_bias"])
    response_text = result["response"]
    used_ids = result["used_source_ids"]

    with db() as conn:
        used_sources = rows_to_list(
            conn.execute(
                f"SELECT * FROM knowledge_sources WHERE id IN ({','.join('?' * len(used_ids)) or 'NULL'})",
                used_ids,
            ).fetchall()
        ) if used_ids else []

        cur = conn.execute(
            """INSERT INTO conversations
               (assistant_id, prompt, response, used_source_ids, generation_mode, generation_error)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                payload.assistant_id, payload.prompt, response_text,
                json.dumps(used_ids), result["generation_mode"], result["error"],
            ),
        )
        conversation_id = cur.lastrowid

    eval_result = evaluate_response(payload.prompt, response_text, used_sources)

    with db() as conn:
        conn.execute(
            """INSERT INTO evaluations
               (conversation_id, relevance_score, groundedness_score, hallucination_risk,
                overall_score, explanation, flagged)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                conversation_id,
                eval_result["relevance_score"],
                eval_result["groundedness_score"],
                eval_result["hallucination_risk"],
                eval_result["overall_score"],
                eval_result["explanation"],
                int(eval_result["flagged"]),
            ),
        )
        if eval_result["flagged"]:
            conn.execute(
                "INSERT INTO governance_reviews (conversation_id, status) VALUES (?, 'pending')",
                (conversation_id,),
            )

    return {
        "conversation_id": conversation_id,
        "response": response_text,
        "used_sources": [{"id": s["id"], "title": s["title"]} for s in used_sources],
        "retrieval_debug": result["retrieval_debug"],
        "generation_mode": result["generation_mode"],
        "generation_error": result["error"],
        "evaluation": eval_result,
    }


@app.get("/conversations")
def list_conversations():
    with db() as conn:
        rows = conn.execute(
            """SELECT c.*, e.relevance_score, e.groundedness_score, e.hallucination_risk,
                      e.overall_score, e.explanation, e.flagged
               FROM conversations c
               LEFT JOIN evaluations e ON e.conversation_id = c.id
               ORDER BY c.id DESC"""
        ).fetchall()
        return rows_to_list(rows)


# -------------------------------------------------------------------- Feedback
@app.post("/feedback")
def submit_feedback(payload: FeedbackCreate):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO feedback (conversation_id, rating, comment) VALUES (?, ?, ?)",
            (payload.conversation_id, payload.rating, payload.comment),
        )
        return {"id": cur.lastrowid, **payload.dict()}


@app.get("/feedback")
def list_feedback():
    with db() as conn:
        return rows_to_list(conn.execute("SELECT * FROM feedback ORDER BY id DESC").fetchall())


# ------------------------------------------------------------------ Governance
@app.get("/governance")
def list_governance_items():
    with db() as conn:
        rows = conn.execute(
            """SELECT g.*, c.prompt, c.response, e.hallucination_risk, e.explanation
               FROM governance_reviews g
               JOIN conversations c ON c.id = g.conversation_id
               LEFT JOIN evaluations e ON e.conversation_id = c.id
               ORDER BY g.id DESC"""
        ).fetchall()
        return rows_to_list(rows)


@app.put("/governance/{review_id}")
def update_governance_item(review_id: int, payload: GovernanceReviewUpdate):
    with db() as conn:
        conn.execute(
            "UPDATE governance_reviews SET status = ?, reviewer_note = ?, reviewed_at = datetime('now') WHERE id = ?",
            (payload.status, payload.reviewer_note, review_id),
        )
    return {"updated": review_id, "status": payload.status}


# ------------------------------------------------------------------- Analytics
@app.get("/analytics")
def analytics():
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM conversations").fetchone()["c"]
        avg_scores = conn.execute(
            """SELECT AVG(relevance_score) rel, AVG(groundedness_score) grd,
                      AVG(hallucination_risk) hal, AVG(overall_score) ov
               FROM evaluations"""
        ).fetchone()
        flagged_count = conn.execute("SELECT COUNT(*) c FROM evaluations WHERE flagged = 1").fetchone()["c"]
        feedback_counts = rows_to_list(
            conn.execute("SELECT rating, COUNT(*) count FROM feedback GROUP BY rating").fetchall()
        )
        by_assistant = rows_to_list(
            conn.execute(
                """SELECT a.name, COUNT(c.id) total, AVG(e.hallucination_risk) avg_hallucination
                   FROM conversations c
                   JOIN assistants a ON a.id = c.assistant_id
                   LEFT JOIN evaluations e ON e.conversation_id = c.id
                   GROUP BY a.id"""
            ).fetchall()
        )
        recent_trend = rows_to_list(
            conn.execute(
                """SELECT c.id, c.created_at, e.overall_score, e.hallucination_risk
                   FROM conversations c LEFT JOIN evaluations e ON e.conversation_id = c.id
                   ORDER BY c.id DESC LIMIT 20"""
            ).fetchall()
        )
        by_generation_mode = rows_to_list(
            conn.execute(
                "SELECT generation_mode, COUNT(*) count FROM conversations GROUP BY generation_mode"
            ).fetchall()
        )

    return {
        "total_conversations": total,
        "avg_relevance": round(avg_scores["rel"] or 0, 2),
        "avg_groundedness": round(avg_scores["grd"] or 0, 2),
        "avg_hallucination_risk": round(avg_scores["hal"] or 0, 2),
        "avg_overall_score": round(avg_scores["ov"] or 0, 2),
        "flagged_count": flagged_count,
        "feedback_counts": feedback_counts,
        "by_assistant": by_assistant,
        "recent_trend": list(reversed(recent_trend)),
        "by_generation_mode": by_generation_mode,
    }


@app.get("/")
def root():
    return {"status": "ok", "service": "AI Conversation Studio API"}
