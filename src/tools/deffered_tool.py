from datetime import datetime
import pandas as pd
from langchain.tools import tool
from src.config import deferred_case_location
from src.guardrails.pii import mask_pii
deferred_cases = pd.read_csv(deferred_case_location)


def defer_to_human( query: str, intent: str) -> str:

    global deferred_cases
    record_id = input("Please enter your customer id : ",)
    while True:
        try:
            phone_input = input("Please enter your phone no (10 digits): ")
        
            # 1. Check if the input contains only digits and is exactly 10 characters long
            if not phone_input.isdigit() or len(phone_input) != 10:
                print("Invalid input! Phone number must be exactly 10 digits and contain numbers only. Try again.\n")
                continue
            
            # 2. Convert to int datatype as requested
            phone_no = int(phone_input)
            masked_no=mask_pii(str(phone_no))
        
            print(f"Successfully accepted phone number: {masked_no}")
            break
        
        except ValueError:
            print("Invalid datatype! Please enter numbers only.\n")

    case_entry = {
        "timestamp": datetime.now(),
        "record_id": record_id,
        "query": query,
        "intent": intent,
        "contact number":phone_no
    }
    deferred_cases = pd.concat([deferred_cases, pd.DataFrame([case_entry])], ignore_index=True)
    deferred_cases.to_csv(deferred_case_location, index=False)
    print("defer_to_human success")
    return "Case deferred to human agent and logged successfully!"

