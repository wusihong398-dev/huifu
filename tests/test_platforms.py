import pytest

from huifu.platforms import UnsupportedOperation, default_registry


def test_default_platform_registry() -> None:
    registry = default_registry()
    assert [adapter.platform_id for adapter in registry.all()] == [
        "douyin",
        "xiaohongshu",
        "kuaishou",
        "bilibili",
    ]


def test_unimplemented_platform_is_explicit() -> None:
    adapter = default_registry().get("douyin")
    capabilities = adapter.detect_reply_capabilities("serial", {})
    assert capabilities.verified is False
    with pytest.raises(UnsupportedOperation):
        adapter.search("serial", "关键词")

