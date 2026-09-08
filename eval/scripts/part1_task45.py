import json
import os

from src.config import task45_result_loc
from src.config import task45_eval_loc
from src.config import chroma_loc
from src.rag.mock_llm import _generate_grounded_answer, judge_rag_triad
from src.rag.embeddings import embedding_model
from src.rag.retrieval import retrieve_chunks_with_score

from langchain_community.vectorstores import Chroma

SIMILARITY_THRESHOLD = 0.1

with open(task45_eval_loc, "r") as file:
    eval_queries = json.load(file)

evaluation_output = {
    "calibrated_threshold": SIMILARITY_THRESHOLD,
    "results": [],
}

strategies = [
    {"name": "Fixed-Size", "collection": "kb_fixed_size"},
    {"name": "Sentence-Based", "collection": "kb_sentence_based"},
]

for strategy in strategies:
    print(f"--- Evaluating Strategy: {strategy['name']} (Collection: {strategy['collection']}) ---")

    vectorestore_persisted = Chroma(
        collection_name=strategy["collection"],
        persist_directory=chroma_loc,
        embedding_function=embedding_model,
    )

    strategy_results = {
        "strategy": strategy["name"],
        "collection_name": strategy["collection"],
        "queries": [],
    }

    for item in eval_queries:
        query = item["query"]
        expected = item["expected_sources"]

        docs, top1_score = retrieve_chunks_with_score(query, k=3)

        retrieved_sources = [os.path.basename(doc.metadata["source"]) for doc in docs]

        hits = len(set(retrieved_sources) & set(expected))
        precision = hits / 3
        recall = (
            hits / len(expected)
            if len(expected) > 0
            else (1.0 if not expected and not retrieved_sources else 0.0)
        )
        max_score = top1_score if docs else 0

        status = "Grounded" if max_score >= SIMILARITY_THRESHOLD else "Fallback"

        if status == "Grounded" and docs:
            context_block = "\n".join(doc.page_content for doc in docs)
            user_msg = f"###Context\n{context_block}\n\n###Question\n{query}"
            response = _generate_grounded_answer(user_msg)
        else:
            context_block = ""
            response = (
                "I don't know — I don't have enough information in the "
                "knowledge base to answer that."
            )

        triad_scores = judge_rag_triad(query=query, context=context_block, answer=response)

        strategy_results["queries"].append(
            {
                "query": query,
                "precision_at_3": round(precision, 4),
                "recall_at_3": round(recall, 4),
                "max_similarity": round(max_score, 4),
                "mock_llm_response": response,
                "Status": status,
                "rag_triad_scores": triad_scores,
            }
        )

    evaluation_output["results"].append(strategy_results)

with open(task45_result_loc, "w") as f:
    json.dump(evaluation_output, f, indent=4)

print(f"\nEvaluation results successfully saved to {task45_result_loc}")