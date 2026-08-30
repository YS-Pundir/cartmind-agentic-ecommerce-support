from src.rag.loader import load_markdown_documents
from src.rag.chunking import fixed_chunking,sentence_based_chunking
from src.rag.embeddings import create_embedding
from src.config import kd_loc
from src.config import chroma_loc

docs=load_markdown_documents(kd_loc)
fixed_data=fixed_chunking(docs)
sentence_data=sentence_based_chunking(docs)

def build_storages():

    create_embedding(fixed_data,chroma_loc,"kb_fixed_size")
    print("Fix-sized collection created !!")

    create_embedding(sentence_data,chroma_loc,"kb_sentence_based")
    print("sentence-based collection created !!")


