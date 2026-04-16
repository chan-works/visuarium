import sqlite3
import os
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_name TEXT,
            created_at   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS utterances (
            utterance_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER NOT NULL,
            utterance_index INTEGER NOT NULL,
            utterance_text  TEXT NOT NULL,
            prompt_text     TEXT NOT NULL,
            prompt_word_count INTEGER NOT NULL,
            duration_sec    REAL NOT NULL,
            spoken_at       TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
    """)
    conn.commit()
    conn.close()


def create_session() -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO sessions (created_at) VALUES (?)", (datetime.now().isoformat(),))
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id


def save_utterance(session_id: int, utterance_index: int, utterance_text: str,
                   prompt_text: str, duration_sec: float) -> int:
    prompt_word_count = len(prompt_text.split())
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO utterances
            (session_id, utterance_index, utterance_text, prompt_text,
             prompt_word_count, duration_sec, spoken_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (session_id, utterance_index, utterance_text, prompt_text,
          prompt_word_count, duration_sec, datetime.now().isoformat()))
    uid = c.lastrowid
    conn.commit()
    conn.close()
    return uid


def update_participant_name(session_id: int, name: str):
    conn = get_connection()
    conn.execute("UPDATE sessions SET participant_name=? WHERE session_id=?", (name, session_id))
    conn.commit()
    conn.close()


def get_all_sessions():
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.session_id, s.participant_name, s.created_at,
               COUNT(u.utterance_id) as utterance_count,
               COALESCE(SUM(u.duration_sec), 0) as total_duration
        FROM sessions s
        LEFT JOIN utterances u ON s.session_id = u.session_id
        GROUP BY s.session_id
        ORDER BY s.created_at DESC
    """).fetchall()
    conn.close()
    return rows


def get_utterances_by_session(session_id: int):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM utterances
        WHERE session_id=?
        ORDER BY utterance_index ASC
    """, (session_id,)).fetchall()
    conn.close()
    return rows


def get_all_utterances():
    conn = get_connection()
    rows = conn.execute("""
        SELECT u.*, s.participant_name, s.created_at as session_created_at
        FROM utterances u
        JOIN sessions s ON u.session_id = s.session_id
        ORDER BY u.session_id, u.utterance_index
    """).fetchall()
    conn.close()
    return rows
