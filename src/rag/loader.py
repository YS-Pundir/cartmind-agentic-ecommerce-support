from src.config import kd_loc

from pathlib import Path
from typing import TypedDict
from langchain_community.document_loaders import PyPDFDirectoryLoader


class Document(TypedDict):
    text: str
    source: str


def load_markdown_documents(directory: str | Path) -> list[Document]:
    """
    Load all Markdown documents from the knowledge-base directory.

    Each Markdown file becomes one parent document.
    """

    directory = Path(directory)

    if not directory.exists():
        raise FileNotFoundError(
            f"Knowledge-base directory not found: {directory}"
        )


    text = PyPDFDirectoryLoader(kd_loc)

    documents=text.load()

 

    if not documents:
        raise ValueError(
            f"No Markdown documents found in {directory}"
        )

    print("document loaded !!")

    return documents

