from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain_classic.vectorstores import Chroma
from langchain_classic.schema import Document



embedding_model = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")


def create_embedding(data,dict_loc,collection_name):
        
        vectore_store=Chroma.from_documents(
                data,
                embedding_model,
                collection_name=collection_name,
                persist_directory=dict_loc)
        
        return vectore_store.persist()



