from pathlib import Path

from huifu.database import Database, SCHEMA_VERSION


def test_database_migration_and_integrity(tmp_path: Path) -> None:
    database = Database(tmp_path / "huifu.db")
    database.migrate()

    assert database.integrity_check() == "ok"
    with database.session() as connection:
        version = connection.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    assert version == SCHEMA_VERSION
    assert "candidate_works" in tables
    assert "reply_drafts" in tables
    assert "publish_jobs" in tables


def test_dashboard_counts_are_zero_on_new_database(tmp_path: Path) -> None:
    database = Database(tmp_path / "huifu.db")
    database.migrate()

    assert all(value == 0 for value in database.dashboard_counts().values())


def test_sync_devices_preserves_record_and_updates_online_count(tmp_path: Path) -> None:
    database = Database(tmp_path / "huifu.db")
    database.migrate()

    database.sync_devices(
        [
            {
                "serial": "6220f9be",
                "model": "Redmi K50G",
                "android_version": "14",
                "status": "online",
            }
        ]
    )
    assert database.dashboard_counts()["devices"] == 1

    database.sync_devices([])
    assert database.dashboard_counts()["devices"] == 0
    with database.session() as connection:
        row = connection.execute(
            "SELECT serial, model, android_version, status FROM devices"
        ).fetchone()

    assert tuple(row) == ("6220f9be", "Redmi K50G", "14", "offline")
