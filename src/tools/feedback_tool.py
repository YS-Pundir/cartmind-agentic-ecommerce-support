from langchain_core.tools import tool
import pandas as pd 
import re
from datetime import datetime
from src.config import feedback_log_location

feedback_log = pd.read_csv(feedback_log_location)



def register_feedback(intent: str, feedback: str,record_id) -> str:

    global feedback_log

    if record_id:
        print(f"\n--- recording feedback for {record_id} ---")
        feedback_entry = {
            "timestamp": datetime.now(),
            "intent": intent,
            "record_id": record_id,
            "feedback": feedback
        }

        feedback_log = pd.concat([feedback_log, pd.DataFrame([feedback_entry])], ignore_index=True)

        feedback_log.to_csv(feedback_log_location,index=False)
        return "Feedback registered successfully!"

    else:
        return "Could not extract a valid order ID from your query. Please provide it in the format ORDXXXX."
