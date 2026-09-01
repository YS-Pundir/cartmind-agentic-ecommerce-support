from src.agent.graph import app
from langchain_core.messages import HumanMessage


import src.logging_config


# Define the initial state payload
initial_state = {
    "record_id": "",
    "input": "How long does a COD refund take?",
    "chat_history": [HumanMessage(content="Can you check the status of my order?")],
    "tool_output": "", # Initialize as empty string
    "intent": ""       # Will be populated by your intent classification node
}

# Invoke the graph
result = app.invoke(initial_state)

# Access the final state output
print(result["intent"])
print(result["tool_output"])