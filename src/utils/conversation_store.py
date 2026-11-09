
import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = ROOT_DIR / "database" / "conversations.sqlite3"


# Open a SQLite connection with the required database settings.
def get_connection() -> sqlite3.Connection:
    try:
        connection = sqlite3.connect(DATABASE_PATH, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection
    except Exception as error:
        raise RuntimeError(f"Unable to connect to the conversation database at '{DATABASE_PATH}': {error}") from error


# Create the conversation and message tables when they do not exist.
def initialize_conversation_store() -> None:
    try:
        print("[CONVERSATION STORE] Initialising SQLite storage.")
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        connection = get_connection()
        try:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    context_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id, message_id);
            """)
            connection.commit()
        finally:
            connection.close()
        print("[CONVERSATION STORE] SQLite storage initialised.")
    except Exception as error:
        raise RuntimeError(f"Unable to initialise conversation storage: {error}") from error


# Create a conversation if it does not already exist.
def create_conversation(conversation_id: str) -> None:
    try:
        print(f"[CONVERSATION STORE] Creating conversation: {conversation_id}.")
        connection = get_connection()
        try:
            connection.execute("INSERT OR IGNORE INTO conversations (conversation_id) VALUES (?)", (conversation_id,))
            connection.commit()
        finally:
            connection.close()
    except Exception as error:
        raise RuntimeError(f"Unable to create conversation '{conversation_id}': {error}") from error


# Retrieve a conversation with its most recent messages and saved context.
def get_conversation(conversation_id: str, message_limit: int = 12) -> dict[str, Any] | None:
    try:
        connection = get_connection()
        try:
            conversation = connection.execute("SELECT * FROM conversations WHERE conversation_id = ?", (conversation_id,)).fetchone()
            if conversation is None:
                return None
            messages = connection.execute("SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY message_id DESC LIMIT ?", (conversation_id, message_limit)).fetchall()
            return {"conversation_id": conversation_id, "context": json.loads(conversation["context_json"]), "messages": [dict(message) for message in reversed(messages)], "created_at": conversation["created_at"], "updated_at": conversation["updated_at"]}
        finally:
            connection.close()
    except Exception as error:
        raise RuntimeError(f"Unable to retrieve conversation '{conversation_id}': {error}") from error


# Save a user or assistant message to the conversation.
def save_message(conversation_id: str, role: str, content: str) -> None:
    try:
        if role not in {"user", "assistant"}:
            raise ValueError(f"Unsupported conversation message role: '{role}'.")
        connection = get_connection()
        try:
            connection.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)", (conversation_id, role, content))
            connection.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?", (conversation_id,))
            connection.commit()
        finally:
            connection.close()
        print(f"[CONVERSATION STORE] Saved {role} message for {conversation_id}.")
    except Exception as error:
        raise RuntimeError(f"Unable to save {role} message for conversation '{conversation_id}': {error}") from error


# Update the compact analytical context associated with a conversation.
def update_conversation_context(conversation_id: str, context: dict[str, Any]) -> None:
    try:
        context_json = json.dumps(context, default=str, separators=(",", ":"))
        connection = get_connection()
        try:
            connection.execute("UPDATE conversations SET context_json = ?, updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?", (context_json, conversation_id))
            connection.commit()
        finally:
            connection.close()
        print(f"[CONVERSATION STORE] Updated analytical context for {conversation_id}.")
    except Exception as error:
        raise RuntimeError(f"Unable to update context for conversation '{conversation_id}': {error}") from error
