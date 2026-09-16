from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    database: Path
    backups: Path
    logs: Path
    images: Path
    audio: Path
    diagnostics: Path
    config: Path

    @classmethod
    def discover(cls) -> "AppPaths":
        override = os.environ.get("HUIFU_DATA_DIR")
        if override:
            root = Path(override).expanduser().resolve()
        elif os.name == "nt":
            local = os.environ.get("LOCALAPPDATA")
            root = Path(local or Path.home() / "AppData" / "Local") / "HuifuAI"
        else:
            root = Path.home() / ".local" / "share" / "HuifuAI"

        return cls(
            root=root,
            database=root / "huifu.db",
            backups=root / "backups",
            logs=root / "logs",
            images=root / "media" / "images",
            audio=root / "media" / "audio",
            diagnostics=root / "diagnostics",
            config=root / "config",
        )

    def ensure(self) -> None:
        for path in (
            self.root,
            self.backups,
            self.logs,
            self.images,
            self.audio,
            self.diagnostics,
            self.config,
        ):
            path.mkdir(parents=True, exist_ok=True)

