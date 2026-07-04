# coding=utf-8
import sqlite3
from pathlib import Path

from archaeo.io.files import expand_user_path


def connect_db(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(expand_user_path(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    # TODO: load from deploy db scripts.
    conn.executescript("""""")
