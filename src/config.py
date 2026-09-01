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
rag_log_location=project_root/"logs"/"api_retries"/"llm_retries.log"
task45_eval_loc=project_root/"eval"/"golden"/"part1_task45.json"
task45_result_loc=project_root/"eval"/"results"/"part1_task45.json"


resp_gen_config=project_root/"config"/"response_generator.json"
resp_gen_schema_path=project_root/"schema"/"agent_response.json"
response_data=settings(resp_gen_config)
resp_gen_promt_path=response_data["response_generater"]["v1"]["prompt_path"]
resp_gen_prompt=get_prompt(resp_gen_promt_path)
resp_gen_schema=settings(resp_gen_schema_path)
resp_gen_model=response_data["response_generater"]["v1"]["config"]["model"]
resp_gen_temp=response_data["response_generater"]["v1"]["config"]["temperature"]
resp_gen_max_token=response_data["response_generater"]["v1"]["config"]["max_tockens"]
feedback_log_location=project_root/"storage"/"feedbacks"/"feedback_storage.csv"#
deferred_case_location=project_root/"storage"/"deferred_cases"/"cases.csv"

