from __future__ import annotations

from .base import PlannedAdapter, PlatformAdapter


class PlatformRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, PlatformAdapter] = {}

    def register(self, adapter: PlatformAdapter) -> None:
        if adapter.platform_id in self._adapters:
            raise ValueError(f"平台插件已注册：{adapter.platform_id}")
        self._adapters[adapter.platform_id] = adapter

    def get(self, platform_id: str) -> PlatformAdapter:
        return self._adapters[platform_id]

    def all(self) -> list[PlatformAdapter]:
        return list(self._adapters.values())


def default_registry() -> PlatformRegistry:
    registry = PlatformRegistry()
    registry.register(PlannedAdapter("douyin", "抖音"))
    registry.register(PlannedAdapter("xiaohongshu", "小红书"))
    registry.register(PlannedAdapter("kuaishou", "快手"))
    registry.register(PlannedAdapter("bilibili", "哔哩哔哩"))
    return registry

