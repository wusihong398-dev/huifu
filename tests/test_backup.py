from pathlib import Path

from huifu.backup import create_backup
from huifu.database import Database
from huifu.paths import AppPaths


def _paths(root: Path) -> AppPaths:
    return AppPaths(
        root=root,
        database=root / "huifu.db",
        backups=root / "backups",
        logs=root / "logs",
        images=root / "media" / "images",
        audio=root / "media" / "audio",
        diagnostics=root / "diagnostics",
        config=root / "config",
    )


def test_backup_creates_valid_database(tmp_path: Path) -> None:
    paths = _paths(tmp_path / "data")
    paths.ensure()
    database = Database(paths.database)
    database.migrate()

    target = create_backup(database, paths)

    assert (target / "huifu.db").exists()
    assert (target / "backup.json").exists()
    assert Database(target / "huifu.db").integrity_check() == "ok"

