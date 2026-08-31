import json
import os
import pandas as pd

from src.config import task45_result_loc
from src.config import task45_eval_loc
from src.config import chroma_loc
from src.rag.mock_llm import MockLLM
from src.rag.embeddings import embedding_model

from langchain_community.vectorstores import Chroma

mock_llm = MockLLM()

with open(task45_eval_loc,"r") as file:
    eval_queries=json.load(file)




def evaluate_retrieval(query, ground_truth_sources, vector_db, k=3):
    # Using similarity_search_with_relevance_scores which returns (doc, score)
    # The warning indicates scores are sometimes outside [0,1] depending on the embedding space distance
    results = vector_db.similarity_search_with_relevance_scores(query, k=k)
    retrieved_sources = [doc.metadata['source'] for doc, score in results]
    hits = len(set(retrieved_sources) & set(ground_truth_sources))
    precision = hits / k
    recall = hits / len(ground_truth_sources) if len(ground_truth_sources) > 0 else 0
    max_score = results[0][1] if results else 0
    return precision, recall, max_score



evaluation_output = {
    "calibrated_threshold": mock_llm.similarity_threshold,
    "results": []
}

strategies = [
    {"name": "Fixed-Size", "collection": "kb_fixed_size"},
    {"name": "Sentence-Based", "collection": "kb_sentence_based"}
]


# Evaluation loop using your pattern: initializing Chroma with a specific collection_name
for strategy in strategies:
    print(f"--- Evaluating Strategy: {strategy['name']} (Collection: {strategy['collection']}) ---")
    
    # Initialize the vectorstore for the specific collection
    vectorestore_persisted = Chroma(
        collection_name=strategy['collection'],
        persist_directory=chroma_loc,
        embedding_function=embedding_model # Using the 'embeddings' object defined in cell 81f34a33
    )
    
    strategy_results = {
        "strategy": strategy['name'],
        "collection_name": strategy['collection'],
        "queries": []
    }
    
    for item in eval_queries:
        query = item['query']
        expected = item['expected_sources']
        
        results_with_scores = vectorestore_persisted.similarity_search_with_relevance_scores(query, k=3)
        
        # FIX: Extract only the filename from the source path to match 'expected_sources'
        retrieved_sources = [os.path.basename(doc.metadata['source']) for doc, score in results_with_scores]
        
        hits = len(set(retrieved_sources) & set(expected))
        precision = hits / 3
        recall = hits / len(expected) if len(expected) > 0 else (1.0 if not expected and not retrieved_sources else 0.0)
        max_score = results_with_scores[0][1] if results_with_scores else 0
        
        if results_with_scores:
            doc, top_score = results_with_scores[0]
            response = mock_llm.generate_content(query, retrieved_context=[doc.page_content], retrieval_score=top_score)
        else:
            response = mock_llm.generate_content(query)

        status = 'Grounded' if max_score >= mock_llm.similarity_threshold else 'Fallback'
        strategy_results["queries"].append({
            "query": query,
            "precision_at_3": round(precision, 4),
            "recall_at_3": round(recall, 4),
            "max_similarity": round(max_score, 4),
            "mock_llm_response": response,
            "Status":status
            
        })
        


    evaluation_output["results"].append(strategy_results)

#Save results

with open(task45_result_loc, 'w') as f:
    json.dump(evaluation_output, f, indent=4)

print(f"\nEvaluation results successfully saved to {task45_result_loc}")