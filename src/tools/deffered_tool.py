from datetime import datetime
import pandas as pd
from langchain.tools import tool
from src.config import deferred_case_location

deferred_cases = pd.read_csv(deferred_case_location)


def defer_to_human(record_id: str, query: str, intent: str) -> str:

    global deferred_cases
    record_id = input("Please enter your customer id : ",)
    
    case_entry = {
        "timestamp": datetime.now(),
        "record_id": record_id,
        "query": query,
        "intent": intent
    }
    deferred_cases = pd.concat([deferred_cases, pd.DataFrame([case_entry])], ignore_index=True)
    deferred_cases.to_csv(deferred_case_location, index=False)
    print("defer_to_human success")
    return "Case deferred to human agent and logged successfully!"

