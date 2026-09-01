
from src.rag.generation import rag_generate
from langchain_core.tools import tool



def rag(user_input: str) -> str:

    try:
        prediction =rag_generate(user_input)
    except Exception as e:
        prediction = f'Sorry, I encountered the following error: \n {e}'

    return prediction




