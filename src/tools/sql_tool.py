import sqlite3
from src.config import db_loc
def check_order_status(record_id: str) -> dict:
    """Looks up an order's status and computes an escalation score.

    Args:
        record_id (str): The ID of the order to check.

    Returns:
        dict: A dictionary containing the order's status, value, and escalation score.
              Returns an error message if the order is not found.
    """
    conn = sqlite3.connect(db_loc)
    
    cursor = conn.cursor()

    cursor.execute("SELECT category,status, order_value_inr, days_since_created, delayed_shipment FROM orders WHERE record_id = ?", (record_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        category,status, order_value_inr, days_since_created, delayed_shipment = result

        # Calculate escalation score
        # Formula: escalation_score = (days_since_created / 30) * 0.7 + (1 if delayed_shipment else 0) * 0.3
        # Normalized days_since_created (assuming max 30 days for simplicity in normalization)
        normalized_days = min(days_since_created / 30, 1.0)

        escalation_score = (normalized_days * 0.7) + (1 if delayed_shipment else 0) * 0.3

        return {
            "record_id": record_id,
            "category":category,
            "status": status,
            "order_value_inr": order_value_inr,
            "days_since_created": days_since_created,
            "delayed_shipment": bool(delayed_shipment),
            "escalation_score": round(escalation_score, 4)
        }
    else:
        return {"error": f"Order with record_id {record_id} not found."}

# Example of usage (for demonstration, normally this would be called by the agent)
# if __name__ == "__main__":
#     # You can test with a record_id from the `df_check` output
#     print(check_order_status("ORD-0000"))
#     print(check_order_status("ORD-0001"))
#     print(check_order_status("ORD-9999")) # Non-existent order
