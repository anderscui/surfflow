# coding=utf-8
import hashlib
import json
import sqlite3

from pathlib import Path
from typing import Any
from abc import ABC, abstractmethod


def build_embedding_cache_key(
    provider: str,
    model: str,
    text: str,
    **params: Any,
) -> str:
    payload = {
        "provider": provider,
        "model": model,
        "text": text,
        "params": params,
    }

    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class EmbeddingCache(ABC):
    @abstractmethod
    def get(self, key: str) -> list[float] | None:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, embedding: list[float]) -> None:
        raise NotImplementedError


class SqliteEmbeddingCache(EmbeddingCache):
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_database(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    cache_key TEXT PRIMARY KEY,
                    embedding TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get(self, key: str) -> list[float] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT embedding
                FROM embedding_cache
                WHERE cache_key = ?
                """,
                (key,),
            ).fetchone()

        if row is None:
            return None

        return json.loads(row[0])

    def set(self, key: str, embedding: list[float]) -> None:
        embedding_json = json.dumps(
            embedding,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO embedding_cache (
                    cache_key,
                    embedding
                )
                VALUES (?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    embedding = excluded.embedding,
                    created_at = CURRENT_TIMESTAMP
                """,
                (key, embedding_json),
            )
