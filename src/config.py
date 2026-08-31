from pathlib import Path

project_root=Path(__file__).resolve().parent.parent

#sql db location
db_loc=project_root/"data"/"database"/"orders.db"

# Vectore database location
chroma_loc=str(project_root/"storage"/"vector_databases")


# knowledge documents location
kd_loc=project_root/"data"/"policy_docs"/"nimbus_kb_split_by_topic"

