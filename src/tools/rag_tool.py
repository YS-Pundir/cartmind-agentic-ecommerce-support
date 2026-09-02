
from src.rag.generation import rag_generate,rag_generate_with_score
from langchain_core.tools import tool



def rag(user_input: str) -> str:

    try:
        prediction =rag_generate(user_input)
    except Exception as e:
        prediction = f'Sorry, I encountered the following error: \n {e}'

    return prediction


def rag_with_score(user_input: str, return_score: bool = False):
    try:
        if return_score:
            prediction, score = rag_generate_with_score(user_input, return_score=True)
            return prediction, score
        return rag_generate(user_input)
    except Exception as e:
        error_msg = f'Sorry, I encountered the following error: \n {e}'
        return (error_msg, 0.0) if return_score else error_msg




