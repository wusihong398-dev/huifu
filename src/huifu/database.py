from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_VERSION = 1


MIGRATION_001 = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    android_version TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'offline',
    last_seen_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS platform_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    nickname TEXT NOT NULL DEFAULT '',
    remark TEXT NOT NULL DEFAULT '',
    device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL,
    login_status TEXT NOT NULL DEFAULT 'unknown',
    daily_limit INTEGER NOT NULL DEFAULT 0 CHECK (daily_limit >= 0),
    paused INTEGER NOT NULL DEFAULT 0 CHECK (paused IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    base_url TEXT NOT NULL,
    model TEXT NOT NULL,
    secret_blob BLOB,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    last_test_status TEXT NOT NULL DEFAULT 'untested',
    last_test_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS business_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    business_description TEXT NOT NULL DEFAULT '',
    target_audience TEXT NOT NULL DEFAULT '',
    reply_goal TEXT NOT NULL DEFAULT '',
    persona TEXT NOT NULL DEFAULT '',
    forbidden_content TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS target_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_profile_id INTEGER NOT NULL REFERENCES business_profiles(id) ON DELETE CASCADE,
    profile_type TEXT NOT NULL CHECK (profile_type IN ('work', 'comment')),
    name TEXT NOT NULL,
    target_description TEXT NOT NULL DEFAULT '',
    include_rules TEXT NOT NULL DEFAULT '',
    exclude_rules TEXT NOT NULL DEFAULT '',
    relevance_threshold INTEGER NOT NULL DEFAULT 80 CHECK (relevance_threshold BETWEEN 0 AND 100),
    risk_threshold INTEGER NOT NULL DEFAULT 30 CHECK (risk_threshold BETWEEN 0 AND 100),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profile_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_profile_id INTEGER NOT NULL REFERENCES target_profiles(id) ON DELETE CASCADE,
    example_type TEXT NOT NULL CHECK (example_type IN ('positive', 'negative', 'correction')),
    content TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS keyword_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id INTEGER REFERENCES keyword_folders(id) ON DELETE SET NULL,
    keyword TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unused',
    last_searched_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(folder_id, keyword)
);

CREATE TABLE IF NOT EXISTS search_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    platform TEXT NOT NULL,
    account_id INTEGER REFERENCES platform_accounts(id) ON DELETE SET NULL,
    target_profile_id INTEGER REFERENCES target_profiles(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    review_mode TEXT NOT NULL DEFAULT 'ai_then_human',
    reply_formats TEXT NOT NULL DEFAULT '[\"text\"]',
    progress_current INTEGER NOT NULL DEFAULT 0,
    progress_total INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidate_works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES search_tasks(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    platform_work_id TEXT NOT NULL,
    url TEXT NOT NULL DEFAULT '',
    author_name TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    transcript TEXT NOT NULL DEFAULT '',
    ocr_text TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'candidate',
    relevance_score INTEGER,
    need_score INTEGER,
    reply_value_score INTEGER,
    risk_score INTEGER,
    analysis_reason TEXT NOT NULL DEFAULT '',
    captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform, platform_work_id, task_id)
);

CREATE TABLE IF NOT EXISTS collected_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL REFERENCES candidate_works(id) ON DELETE CASCADE,
    platform_comment_id TEXT NOT NULL,
    parent_comment_id TEXT,
    author_name TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    published_at TEXT,
    status TEXT NOT NULL DEFAULT 'candidate',
    relevance_score INTEGER,
    need_score INTEGER,
    reply_value_score INTEGER,
    risk_score INTEGER,
    analysis_reason TEXT NOT NULL DEFAULT '',
    UNIQUE(work_id, platform_comment_id)
);

CREATE TABLE IF NOT EXISTS reply_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL REFERENCES candidate_works(id) ON DELETE CASCADE,
    comment_id INTEGER REFERENCES collected_comments(id) ON DELETE SET NULL,
    account_id INTEGER REFERENCES platform_accounts(id) ON DELETE SET NULL,
    format TEXT NOT NULL CHECK (format IN ('text', 'image', 'audio', 'text_image')),
    text_content TEXT NOT NULL DEFAULT '',
    media_path TEXT NOT NULL DEFAULT '',
    fallback_text TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'draft',
    relevance_score INTEGER,
    risk_score INTEGER,
    review_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS publish_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id INTEGER NOT NULL REFERENCES reply_drafts(id) ON DELETE CASCADE,
    device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL,
    state TEXT NOT NULL DEFAULT 'queued',
    stage TEXT NOT NULL DEFAULT 'waiting_device',
    result TEXT NOT NULL DEFAULT '',
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS publish_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES publish_jobs(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    diagnostic_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT '',
    entity_id TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_candidate_works_status ON candidate_works(status);
CREATE INDEX IF NOT EXISTS idx_comments_status ON collected_comments(status);
CREATE INDEX IF NOT EXISTS idx_reply_drafts_status ON reply_drafts(status);
CREATE INDEX IF NOT EXISTS idx_publish_jobs_state ON publish_jobs(state);
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        with self.session() as connection:
            connection.executescript(MIGRATION_001)
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
                (SCHEMA_VERSION,),
            )

    def integrity_check(self) -> str:
        with self.session() as connection:
            row = connection.execute("PRAGMA integrity_check").fetchone()
            return str(row[0])

    def dashboard_counts(self) -> dict[str, int]:
        queries = {
            "devices": "SELECT COUNT(*) FROM devices WHERE status = 'online'",
            "accounts": "SELECT COUNT(*) FROM platform_accounts WHERE login_status = 'logged_in' AND paused = 0",
            "candidates": "SELECT COUNT(*) FROM candidate_works",
            "targets": "SELECT COUNT(*) FROM candidate_works WHERE status = 'approved'",
            "drafts": "SELECT COUNT(*) FROM reply_drafts WHERE status IN ('draft', 'awaiting_review')",
            "queued": "SELECT COUNT(*) FROM publish_jobs WHERE state = 'queued'",
            "succeeded": "SELECT COUNT(*) FROM publish_jobs WHERE state = 'succeeded'",
            "failed": "SELECT COUNT(*) FROM publish_jobs WHERE state IN ('failed', 'uncertain')",
        }
        with self.session() as connection:
            return {
                key: int(connection.execute(sql).fetchone()[0])
                for key, sql in queries.items()
            }

