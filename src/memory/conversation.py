from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from src.config import conversations_file_loc

class ConversationMemory:
    """
    Simple JSON-backed persistent conversation memory.

    Each conversation is identified by a conversation_id.
    """

    def __init__(self, file_path: str = conversations_file_loc):
        self.file_path = conversations_file_loc
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.file_path.exists():
            self.file_path.write_text("{}", encoding="utf-8")

    def _load(self) -> dict[str, Any]:
        try:
            content = self.file_path.read_text(encoding="utf-8")

            if not content.strip():
                return {}

            return json.loads(content)

        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        temp_file = self.file_path.with_suffix(".tmp")

        temp_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        temp_file.replace(self.file_path)

    def get_history(self, conversation_id: str) -> list[dict[str, str]]:
        """
        Return the conversation history for a conversation.
        """
        data = self._load()

        conversation = data.get(conversation_id, {})

        return conversation.get("messages", [])

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
    ) -> None:
        """
        Persist one message to a conversation.
        """
        data = self._load()

        if conversation_id not in data:
            data[conversation_id] = {
                "messages": []
            }

        data[conversation_id]["messages"].append(
            {
                "role": role,
                "content": content,
            }
        )

        self._save(data)

    def add_exchange(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """
        Persist a user/assistant exchange.
        """
        data = self._load()

        if conversation_id not in data:
            data[conversation_id] = {
                "messages": []
            }

        data[conversation_id]["messages"].extend(
            [
                {
                    "role": "user",
                    "content": user_message,
                },
                {
                    "role": "assistant",
                    "content": assistant_message,
                },
            ]
        )

        self._save(data)

    def clear(self, conversation_id: str) -> None:
        """
        Delete one conversation.
        """
        data = self._load()

        if conversation_id in data:
            del data[conversation_id]

        self._save(data)

    def exists(self, conversation_id: str) -> bool:
        """
        Check whether a conversation has persisted history.
        """
        data = self._load()

        return (
            conversation_id in data
            and len(data[conversation_id].get("messages", [])) > 0
        )

    def conversation_count(self) -> int:
        """
        Return the number of persisted conversations.
        """
        return len(self._load())