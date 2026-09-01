import logging
from src.config import rag_log_location

logging.basicConfig(
    level=logging.INFO,
    filename=rag_log_location,
    filemode="a",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"

)