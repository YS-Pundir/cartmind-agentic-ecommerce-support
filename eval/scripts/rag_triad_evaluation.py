"""
RAG Triad Evaluation Script — Nimbus Commerce RAG system.

Runs the existing retrieval + generation pipeline (src.rag.retrieval /
src.rag.generation) for every query in the golden test set, then scores each
(query, context, answer) triple with THREE independent LLM-as-judge calls —
context_relevance, groundedness, answer_relevance — using the exact judge
prompts/rubrics embedded in the golden test-set JSON.

Assumptions (adjust the CONFIG block below if these don't match your setup):
  - This script is run from the project root, so `src.rag.*` and `src.config`
    are importable (same layout your existing modules already assume).
  - `src.config` exposes `api_key` and `rag_model` (same Groq creds used by
    generation.py).
  - The golden test-set JSON lives at ./nimbus_rag_golden_test_set_15.json
    (change GOLDEN_SET_PATH if it's elsewhere).

Output:
  - rag_triad_evaluation_results.json  -> full structured results + averages
  - rag_triad_evaluation_results.csv   -> flat per-query score table
"""

import csv
import json
import logging
import re
import time
from pathlib import Path
from statistics import mean

from groq import Groq
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from src.config import api_key
from src.rag.retrieval import retreiver, retrieve_chunks
from src.rag.generation import rag_generate_with_score

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
# NOTE: the RAG *generation* model is whatever `rag_model` is set to inside
# src/config.py / used internally by rag_generate_with_score() — untouched
# here. The JUDGE model is deliberately kept separate/different from the
# generation model to avoid self-evaluation bias (a model tends to rate its
# own outputs more favorably than an independent model would).
JUDGE_MODEL = "openai/gpt-oss-20b"

project_root=Path(__file__).resolve().parent.parent

GOLDEN_SET_PATH = project_root/"golden"/"nimbus_rag_golden_test_set_15.json"
OUTPUT_JSON_PATH = project_root/"results"/"rag_eval_results"/"with_real_llm"/"rag_triad_evaluation_results.json"
OUTPUT_CSV_PATH = project_root/"results"/"rag_eval_results"/"with_real_llm"/"rag_triad_evaluation_results.csv"
JUDGE_TEMPERATURE = 0  # keep judges deterministic
SECONDS_BETWEEN_CALLS = 2.2  # proactive throttle: free tier = 30 req/min -> ~2s/req is safe margin

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rag_triad_eval")

client = Groq(api_key=api_key)


# --------------------------------------------------------------------------
# Helpers: golden set I/O
# --------------------------------------------------------------------------
def load_golden_set(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------
# Helpers: run the existing RAG pipeline
# --------------------------------------------------------------------------
def format_context(chunks) -> str:
    """Same shape as generation.py's context formatting, kept here so the
    judges see exactly what the generator saw."""
    parts = []
    for d in chunks:
        source = d.metadata.get("source", "unknown")
        parts.append(f"{d.page_content}\n###Source: {source}")
    return "\n\n".join(parts)


def get_context_and_answer(query: str):
    """Retrieve chunks + generate the answer using your existing pipeline."""
    chunks = retrieve_chunks(query, retreiver)
    context_text = format_context(chunks)
    answer = rag_generate_with_score(query, return_score=False)
    return context_text, answer


# --------------------------------------------------------------------------
# Helpers: LLM-as-judge calls
# --------------------------------------------------------------------------
def extract_json(raw_text: str) -> dict:
    """Strip code fences / stray prose and parse the judge's JSON reply."""
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    return json.loads(cleaned)


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def call_judge(system_prompt: str, user_content: str) -> dict:
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=JUDGE_TEMPERATURE,
    )
    raw = response.choices[0].message.content
    time.sleep(SECONDS_BETWEEN_CALLS)  # stay comfortably under free-tier 30 RPM
    try:
        return extract_json(raw)
    except (json.JSONDecodeError, AttributeError) as e:
        logger.error("Failed to parse judge JSON output: %s", raw)
        return {"score": 1, "reason": f"Judge output could not be parsed: {e}"}


def run_context_relevance_judge(judge_cfg: dict, query: str, context: str) -> dict:
    user_content = f"User query:\n{query}\n\nRetrieved context:\n{context}"
    return call_judge(judge_cfg["prompt"], user_content)


def run_groundedness_judge(judge_cfg: dict, query: str, context: str, answer: str) -> dict:
    user_content = (
        f"User query:\n{query}\n\nRetrieved context:\n{context}\n\nGenerated answer:\n{answer}"
    )
    return call_judge(judge_cfg["prompt"], user_content)


def run_answer_relevance_judge(judge_cfg: dict, query: str, answer: str) -> dict:
    user_content = f"User query:\n{query}\n\nGenerated answer:\n{answer}"
    return call_judge(judge_cfg["prompt"], user_content)


# --------------------------------------------------------------------------
# Main evaluation loop
# --------------------------------------------------------------------------
def evaluate_all(golden_set: dict) -> list:
    judges = golden_set["llm_judges"]
    results = []

    for item in golden_set["queries"]:
        qid, query, topic = item["id"], item["query"], item["topic"]
        logger.info("[%s] Running RAG pipeline for: %s", qid, query)

        try:
            context_text, answer = get_context_and_answer(query)
            time.sleep(SECONDS_BETWEEN_CALLS)  # this call also hits Groq (generation)
        except Exception as e:
            logger.error("[%s] RAG pipeline failed: %s", qid, e)
            context_text, answer = "", f"ERROR: pipeline failed - {e}"

        cr = run_context_relevance_judge(judges["context_relevance"], query, context_text)
        gr = run_groundedness_judge(judges["groundedness"], query, context_text, answer)
        ar = run_answer_relevance_judge(judges["answer_relevance"], query, answer)

        result = {
            "id": qid,
            "query": query,
            "topic": topic,
            "type": item.get("type"),
            "retrieved_context": context_text,
            "generated_answer": answer,
            "scores": {
                "context_relevance": {"score": cr.get("score"), "reason": cr.get("reason")},
                "groundedness": {"score": gr.get("score"), "reason": gr.get("reason")},
                "answer_relevance": {"score": ar.get("score"), "reason": ar.get("reason")},
            },
        }
        results.append(result)
        logger.info(
            "[%s] context_relevance=%s groundedness=%s answer_relevance=%s",
            qid, cr.get("score"), gr.get("score"), ar.get("score"),
        )

    return results


def compute_aggregates(results: list) -> dict:
    def scores_for(metric):
        return [
            r["scores"][metric]["score"]
            for r in results
            if isinstance(r["scores"][metric]["score"], (int, float))
        ]

    cr_scores = scores_for("context_relevance")
    gr_scores = scores_for("groundedness")
    ar_scores = scores_for("answer_relevance")

    avg_cr = round(mean(cr_scores), 3) if cr_scores else 0
    avg_gr = round(mean(gr_scores), 3) if gr_scores else 0
    avg_ar = round(mean(ar_scores), 3) if ar_scores else 0
    overall = round(mean([avg_cr, avg_gr, avg_ar]), 3)

    return {
        "average_context_relevance": avg_cr,
        "average_groundedness": avg_gr,
        "average_answer_relevance": avg_ar,
        "overall_average": overall,
    }


def save_results(results: list, aggregates: dict) -> None:
    output = {
        "name": "Nimbus Commerce RAG Triad Evaluation Results",
        "total_queries": len(results),
        "results": results,
        "aggregate_output": aggregates,
    }
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info("Saved JSON results to %s", OUTPUT_JSON_PATH)

    with open(OUTPUT_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "query_id",
                "query",
                "topic",
                "context_relevance_1_to_5",
                "groundedness_1_to_5",
                "answer_relevance_1_to_5",
            ]
        )
        for r in results:
            writer.writerow(
                [
                    r["id"],
                    r["query"],
                    r["topic"],
                    r["scores"]["context_relevance"]["score"],
                    r["scores"]["groundedness"]["score"],
                    r["scores"]["answer_relevance"]["score"],
                ]
            )
    logger.info("Saved CSV summary to %s", OUTPUT_CSV_PATH)


def main():
    golden_set = load_golden_set(GOLDEN_SET_PATH)
    results = evaluate_all(golden_set)
    aggregates = compute_aggregates(results)
    save_results(results, aggregates)

    print("\n=== RAG TRIAD EVALUATION SUMMARY ===")
    for r in results:
        print(
            f"[{r['id']:>2}] CR={r['scores']['context_relevance']['score']} "
            f"GR={r['scores']['groundedness']['score']} "
            f"AR={r['scores']['answer_relevance']['score']}  - {r['topic']}"
        )
    print("\nAverages:")
    for k, v in aggregates.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
