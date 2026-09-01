from pprint import pprint
from langchain_community.vectorstores import Chroma
from src.rag.embeddings import embedding_model
from src.config import chroma_loc


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