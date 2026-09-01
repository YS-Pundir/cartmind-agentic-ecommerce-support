from langchain_core.tools import tool
import pandas as pd 
import re
from datetime import datetime
from src.config import feedback_log_location

feedback_log = pd.read_csv(feedback_log_location)


def register_feedback(intent: str, record_id: int, feedback: str) -> str:

    global feedback_log
    record_id = input("Please enter your customer id : ",)

    feedback_entry = {
        "timestamp": datetime.now(),
        "intent": intent,
        "record_id": record_id,
        "feedback": feedback
    }

    feedback_log = pd.concat([feedback_log, pd.DataFrame([feedback_entry])], ignore_index=True)

    feedback_log.to_csv(feedback_log_location)
    return "Feedback registered successfully!"

