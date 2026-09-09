from __future__ import annotations
import mlflow
from src.config import mlflow_tracking_uri

_initialized = False


def setup_tracing() -> None:
    global _initialized
    if _initialized:
        return

    mlflow.set_tracking_uri(mlflow_tracking_uri)   # sqlite:///.../mlflow.db, no server needed
    mlflow.set_experiment("cartmind-agent")

    mlflow.langchain.autolog()
    mlflow.groq.autolog()
    mlflow.openai.autolog()

    _initialized = True