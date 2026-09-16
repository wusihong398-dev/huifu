from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def _self_test() -> int:
    """Run a non-GUI startup check for packaged Windows builds."""
    from huifu.database import Database

    with tempfile.TemporaryDirectory(prefix="huifu-self-test-") as directory:
        database = Database(Path(directory) / "huifu.db")
        database.migrate()
        if database.integrity_check() != "ok":
            return 1
        counts = database.dashboard_counts()
        if any(counts.values()):
            return 1
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()

    # Keep this absolute import so the frozen entry point always has a package.
    from huifu.app import main as application_main

    return application_main()


if __name__ == "__main__":
    raise SystemExit(main())

