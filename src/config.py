from pathlib import Path
import json 
import os
from dotenv import load_dotenv
load_dotenv()
api_key=os.getenv("api_key")

project_root=Path(__file__).resolve().parent.parent

#sql db location
db_loc=project_root/"data"/"database"/"orders.db"

# Vectore database location
chroma_loc=str(project_root/"storage"/"vector_databases")


# knowledge documents location
kd_loc=project_root/"data"/"policy_docs"/"nimbus_kb_split_by_topic"


#config of the rag tool for the generation of grounded answers

rag_config_path=project_root/"config"/"rag_tool.json"

def settings(config_path:Path):
    with open(config_path, "r") as f:
        data=json.load(f)
    return data

def get_prompt(prompt_path:Path):
    with open(prompt_path, "r") as f:
        data=f.read()
    return data

rag_data=settings(rag_config_path)
rag_model=rag_data["rag_tool"]["v1"]["config"]["model"]
rag_prompt_path=rag_data["rag_tool"]["v1"]["prompt_path"]
rag_prompt=get_prompt(rag_prompt_path)
rag_temperature=rag_data["rag_tool"]["v1"]["config"]["temperature"]
rag_log_location=project_root/"logs"/"api_retries"/"rag_llm_retries.log"
