"""
eval/scripts/rag_triad_evaluation_mock.py

RAG Triad Evaluation Script — Nimbus Commerce RAG system — MOCK_LLM mode.

Uses your EXISTING retrieval pipeline (src.rag.retrieval: retreiver /
retrieve_chunks) exactly as-is — no new retriever, no TF-IDF, nothing
swapped out on the retrieval side.

The only thing swapped is the LLM: generation goes through
src.llm_client.get_llm_client() (-> src.rag.mock_llm.MockGroqClient when
MOCK_LLM=true, per your llm_client.py / mock_llm.py), and judging goes
through src.rag.mock_llm.judge_rag_triad(), both zero-network,
zero-API-key, fully deterministic.

Run with:
    MOCK_LLM=true python -m eval.scripts.rag_triad_evaluation_mock

Output:
  - eval/results/rag_triad_evaluation_results_mock.json
  - eval/results/rag_triad_evaluation_results_mock.csv
"""

import csv
import json
import logging
import os
from pathlib import Path
from statistics import mean

os.environ.setdefault("MOCK_LLM", "true")

from src.llm_client import get_llm_client
from src.rag.mock_llm import judge_rag_triad
from src.rag.retrieval import retreiver, retrieve_chunks  # <-- your existing retriever, untouched

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
project_root = Path(__file__).resolve().parent.parent

GOLDEN_SET_PATH = project_root / "golden" / "nimbus_rag_golden_test_set_15.json"
OUTPUT_JSON_PATH = project_root / "results" /"rag_eval_results"/"with_mock_llm"/ "rag_triad_evaluation_results_mock.json"
OUTPUT_CSV_PATH = project_root / "results" /"rag_eval_results"/"with_mock_llm"/"rag_triad_evaluation_results_mock.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rag_triad_eval_mock")

client = get_llm_client()  # MockGroqClient under MOCK_LLM=true


# --------------------------------------------------------------------------
# Helpers: golden set I/O
# --------------------------------------------------------------------------
def load_golden_set(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------
# Helpers: run the pipeline (your retriever + MockGroqClient generation)
# --------------------------------------------------------------------------
def format_context(docs) -> str:
    """Same shape as generation.py's context formatting, so the judge sees
    exactly what the generator saw."""
    parts = []
    for d in docs:
        source = d.metadata.get("source", "unknown")
        parts.append(f"{d.page_content}\n###Source: {source}")
    return "\n\n".join(parts)


QNA_USER_MESSAGE_TEMPLATE = """
###Context
Here are some documents and their source that may be relevant to the question mentioned below.
{context}

###Question
{question}
"""


def get_context_and_answer(query: str):
    """Retrieve via your existing retreiver/retrieve_chunks, generate via
    MockGroqClient using the same prompt shape as generation.py."""
    docs = retrieve_chunks(query, retreiver)
    context_text = format_context(docs)

    prompt = [
        {"role": "system", "content": "Answer using only the provided context. If the context does not contain the answer, say you don't know."},
        {"role": "user", "content": QNA_USER_MESSAGE_TEMPLATE.format(context=context_text, question=query)},
    ]
    response = client.chat.completions.create(model="mock", messages=prompt, temperature=0.0)
    answer = response.choices[0].message.content
    return context_text, answer


# --------------------------------------------------------------------------
# Helpers: LLM-as-judge (deterministic, MOCK_LLM)
# --------------------------------------------------------------------------
def score_to_stars(score_0_1: float) -> int:
    """Map a [0,1] deterministic judge score onto the golden set's 1-5 rubric
    scale, so results read consistently with the embedded judge prompts."""
    if score_0_1 >= 0.60:
        return 5
    if score_0_1 >= 0.40:
        return 4
    if score_0_1 >= 0.20:
        return 3
    if score_0_1 > 0.0:
        return 2
    return 1


def run_judges(query: str, context: str, answer: str) -> dict:
    """Runs the same rubric embedded in llm_judges (context_relevance,
    groundedness, answer_relevance) via the deterministic MOCK_LLM judge."""
    raw = judge_rag_triad(query=query, context=context, answer=answer)
    out = {}
    for metric in ("context_relevance", "groundedness", "answer_relevance"):
        raw_score = raw[metric]
        out[metric] = {
            "score_0_1": round(raw_score, 4),
            "score_1_5": score_to_stars(raw_score),
        }
    return out


# --------------------------------------------------------------------------
# Main evaluation loop
# --------------------------------------------------------------------------
def evaluate_all(golden_set: dict) -> list:
    results = []

    for item in golden_set["queries"]:
        qid, query, topic, qtype = item["id"], item["query"], item["topic"], item.get("type")
        logger.info("[%s] Running mock RAG pipeline for: %s", qid, query)

        try:
            context_text, answer = get_context_and_answer(query)
        except Exception as e:
            logger.error("[%s] RAG pipeline failed: %s", qid, e)
            context_text, answer = "", f"ERROR: pipeline failed - {e}"

        scores = run_judges(query, context_text, answer)

        result = {
            "id": qid,
            "query": query,
            "topic": topic,
            "type": qtype,
            "retrieved_context": context_text,
            "generated_answer": answer,
            "scores": scores,
        }
        results.append(result)
        logger.info(
            "[%s] context_relevance=%.2f groundedness=%.2f answer_relevance=%.2f  (%s)",
            qid,
            scores["context_relevance"]["score_0_1"],
            scores["groundedness"]["score_0_1"],
            scores["answer_relevance"]["score_0_1"],
            topic,
        )

    return results


def compute_aggregates(results: list) -> dict:
    def scores_for(metric):
        return [r["scores"][metric]["score_0_1"] for r in results]

    cr_scores = scores_for("context_relevance")
    gr_scores = scores_for("groundedness")
    ar_scores = scores_for("answer_relevance")

    avg_cr = round(mean(cr_scores), 4) if cr_scores else 0
    avg_gr = round(mean(gr_scores), 4) if gr_scores else 0
    avg_ar = round(mean(ar_scores), 4) if ar_scores else 0
    overall = round(mean([avg_cr, avg_gr, avg_ar]), 4)

    return {
        "average_context_relevance": avg_cr,
        "average_groundedness": avg_gr,
        "average_answer_relevance": avg_ar,
        "overall_average": overall,
        "n_queries": len(results),
    }


def save_results(results: list, aggregates: dict) -> None:
    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "name": "Nimbus Commerce RAG Triad Evaluation Results (MOCK_LLM)",
        "mode": "MOCK_LLM",
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
                "query_id", "query", "topic", "type",
                "context_relevance_0_1", "groundedness_0_1", "answer_relevance_0_1",
                "context_relevance_1_5", "groundedness_1_5", "answer_relevance_1_5",
            ]
        )
        for r in results:
            s = r["scores"]
            writer.writerow([
                r["id"], r["query"], r["topic"], r["type"],
                s["context_relevance"]["score_0_1"], s["groundedness"]["score_0_1"], s["answer_relevance"]["score_0_1"],
                s["context_relevance"]["score_1_5"], s["groundedness"]["score_1_5"], s["answer_relevance"]["score_1_5"],
            ])
    logger.info("Saved CSV summary to %s", OUTPUT_CSV_PATH)


def main():
    golden_set = load_golden_set(GOLDEN_SET_PATH)
    results = evaluate_all(golden_set)
    aggregates = compute_aggregates(results)
    save_results(results, aggregates)

    print("\n=== RAG TRIAD EVALUATION SUMMARY (MOCK_LLM) ===")
    for r in results:
        s = r["scores"]
        print(
            f"[{r['id']:>2}] CR={s['context_relevance']['score_0_1']:.2f} "
            f"GR={s['groundedness']['score_0_1']:.2f} "
            f"AR={s['answer_relevance']['score_0_1']:.2f}  - {r['topic']} ({r['type']})"
        )
    print("\nAverages across all 15 queries:")
    for k, v in aggregates.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()