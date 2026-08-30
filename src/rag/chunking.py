from src.rag.loader import load_markdown_documents
from src.config import kd_loc
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter,NLTKTextSplitter
from langchain_community.document_loaders import TextLoader



def fixed_chunking(documents):
    

    text_splitter=RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    encoding_name='cl100k_base',
    chunk_size=512,
    chunk_overlap=16
)
    fixed_chunks=text_splitter.split_documents(documents)

    return fixed_chunks

def sentence_based_chunking(documents):
  """Strategy 2: Sentence-based chunking using NLTKTextSplitter to respect linguistic boundaries."""
  sentence_splitter = NLTKTextSplitter(
     chunk_size=512,
     chunk_overlap=64)
  sentence_chunks = sentence_splitter.split_documents(documents)
  return sentence_chunks



