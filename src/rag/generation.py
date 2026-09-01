from datetime import datetime
from src.config import ( api_key,
                        rag_prompt,
                        rag_temperature,
                        rag_model,
                        rag_log_location
                        )

from src.rag.retrieval import( retrieve_chunks
                              ,retreiver)

from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain_classic.vectorstores import Chroma

from groq import Groq
client=Groq(api_key=api_key)

# For Api Rate limiting
import logging
from tenacity import (
     retry,  # Decorator that wraps a function with retry logic
    stop_after_attempt,  # Stop after N total attempts
    wait_exponential,  # Wait 1s, 2s, 4s, 8s between retries
    before_sleep_log, 

)

logger = logging.getLogger("rag_generation")


attempt_counter={"n":0}



qna_user_message_template = """
###Context
Here are some documents and their source that may be relevant to the question mentioned below.
{context}

###Question
{question}
"""


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1,min=1,max=10),
    before_sleep=before_sleep_log(logger,logging.WARNING)
)
def rag_generate(user_input: str) -> str:

   

    relevant_document_chunks =retrieve_chunks(user_input,retreiver)
    context_list = [d.page_content + "\n ###Source: " + d.metadata['source'] + "\n\n " for d in relevant_document_chunks]

    context_for_query = ". ".join(context_list)
    # print("context: ", context_for_query)  # Use this to understand what context is provided BTS and to debug.
    prompt = [
        {'role':'system', 'content': rag_prompt},
        {'role': 'user', 'content': qna_user_message_template.format(
            context=context_for_query,
            question=user_input
            )
        }
    ]

    try:
        logger.info("RAG API CALL")
        response = client.chat.completions.create(
        model=rag_model,
        messages=prompt,
        temperature=rag_temperature
        )

        prediction = response.choices[0].message.content
        logger.info("RAG API SUCCESS")
    except Exception as e:
        logger.error(f"RAG API FAILED: {e}")
        raise

    return prediction
