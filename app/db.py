from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .settings import settings


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}:{derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest = stored.split(":", 1)
    return hmac.compare_digest(hash_password(password, bytes.fromhex(salt_hex)).split(":", 1)[1], digest)


@contextmanager
def connection():
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(settings.database_path)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


def init_db() -> None:
    settings.voice_path.mkdir(parents=True, exist_ok=True)
    settings.obsidian_path.mkdir(parents=True, exist_ok=True)
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'owner', created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS progress (
                user_id INTEGER NOT NULL, language TEXT NOT NULL, level TEXT NOT NULL,
                lessons INTEGER NOT NULL DEFAULT 0, minutes INTEGER NOT NULL DEFAULT 0,
                xp INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (user_id, language)
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                language TEXT NOT NULL, topic TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                language TEXT NOT NULL, category TEXT NOT NULL, example TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 1, next_review_at TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL, topic TEXT NOT NULL,
                title TEXT NOT NULL, url TEXT NOT NULL, accent TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'candidate', created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS voice_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                language TEXT NOT NULL, filename TEXT NOT NULL, content_type TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS skill_progress (
                user_id INTEGER NOT NULL, language TEXT NOT NULL, skill TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0, samples INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL, PRIMARY KEY (user_id, language, skill)
            );
            CREATE TABLE IF NOT EXISTS lesson_completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                lesson_id TEXT NOT NULL, language TEXT NOT NULL, minutes INTEGER NOT NULL,
                created_at TEXT NOT NULL, UNIQUE(user_id, lesson_id)
            );
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                language TEXT NOT NULL, lesson_id TEXT NOT NULL,
                confidence INTEGER NOT NULL, learned TEXT NOT NULL,
                difficult TEXT NOT NULL, created_at TEXT NOT NULL
            );
            """
        )
        user = db.execute("SELECT id FROM users WHERE email=?", (settings.owner_email,)).fetchone()
        if not user:
            db.execute(
                "INSERT INTO users(email,password_hash,role,created_at) VALUES(?,?,?,?)",
                (settings.owner_email, hash_password(settings.owner_password), "owner", utcnow()),
            )
            user_id = db.execute("SELECT id FROM users WHERE email=?", (settings.owner_email,)).fetchone()["id"]
        else:
            user_id = user["id"]
        for language in ("English", "Spanish"):
            db.execute(
                "INSERT OR IGNORE INTO progress(user_id,language,level) VALUES(?,?,?)",
                (user_id, language, "A0"),
            )
            for skill in ("speaking", "listening", "reading", "writing", "vocabulary", "pronunciation"):
                db.execute(
                    "INSERT OR IGNORE INTO skill_progress(user_id,language,skill,updated_at) VALUES(?,?,?,?)",
                    (user_id, language, skill, utcnow()),
                )
        if not db.execute("SELECT 1 FROM videos LIMIT 1").fetchone():
            db.executemany(
                "INSERT INTO videos(language,topic,title,url,accent,status,created_at) VALUES(?,?,?,?,?,?,?)",
                [
                    ("English", "th-sound", "TH sound: положение языка", "https://www.youtube.com/results?search_query=american+english+th+sound+articulation", "American", "approved", utcnow()),
                    ("Spanish", "vowels", "Испанские гласные", "https://www.youtube.com/results?search_query=latin+american+spanish+vowels+pronunciation", "Latin American", "approved", utcnow()),
                ],
            )
