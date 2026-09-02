from pprint import pprint
from langchain_community.vectorstores import Chroma
from src.rag.embeddings import embedding_model
from src.config import chroma_loc
import numpy as np

collection_name="kb_fixed_size"  # choosen from task 5!!!

vectorestore_persisted=Chroma(
    collection_name=collection_name,
    persist_directory=chroma_loc,
    embedding_function=embedding_model
)

retreiver=vectorestore_persisted.as_retriever(
    search_type="similarity",
    search_kwargs={"k":5}
)

def retrieve_chunks(user_query, retriever):
    docs = retriever.invoke(user_query)
    return docs


def retrieve_chunks_with_score(user_query, k: int = 5):
    docs_with_distance = vectorestore_persisted.similarity_search_with_score(user_query, k=k)
    if not docs_with_distance:
        return [], 0.0
    query_vec = np.array(embedding_model.embed_query(user_query))
    docs = [doc for doc, _ in docs_with_distance]
    # compute cosine similarity directly against each doc's embedding
    doc_vecs = np.array(embedding_model.embed_documents([d.page_content for d in docs]))
    sims = (doc_vecs @ query_vec) / (np.linalg.norm(doc_vecs, axis=1) * np.linalg.norm(query_vec) + 1e-10)
    top1_score = float(sims[0])
    return docs, top1_score