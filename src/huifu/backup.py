from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .database import Database
from .paths import AppPaths


def create_backup(database: Database, paths: AppPaths) -> Path:
    paths.ensure()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target_dir = paths.backups / stamp
    target_dir.mkdir(parents=True, exist_ok=False)
    target_db = target_dir / "huifu.db"

    source = database.connect()
    destination = sqlite3.connect(target_db)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database": str(target_db.name),
        "integrity": Database(target_db).integrity_check(),
    }
    (target_dir / "backup.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target_dir

