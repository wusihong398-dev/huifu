from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class UnsupportedOperation(RuntimeError):
    pass


@dataclass(frozen=True)
class ReplyCapabilities:
    text: bool = False
    image: bool = False
    audio: bool = False
    text_image: bool = False
    verified: bool = False
    message: str = "尚未在当前账号和 App 版本验证"


class PlatformAdapter(ABC):
    platform_id: str
    display_name: str

    @abstractmethod
    def detect_login(self, device_serial: str) -> str:
        """Return one of logged_in, logged_out, verification_required, unknown."""

    @abstractmethod
    def detect_reply_capabilities(
        self, device_serial: str, target: dict[str, Any]
    ) -> ReplyCapabilities:
        """Inspect the real UI; never infer support from a static platform name."""

    def search(self, device_serial: str, keyword: str) -> list[dict[str, Any]]:
        raise UnsupportedOperation(f"{self.display_name}搜索适配尚未完成")

    def extract_work(self, device_serial: str, work: dict[str, Any]) -> dict[str, Any]:
        raise UnsupportedOperation(f"{self.display_name}作品提取适配尚未完成")

    def extract_comments(
        self, device_serial: str, work: dict[str, Any], limit: int
    ) -> list[dict[str, Any]]:
        raise UnsupportedOperation(f"{self.display_name}评论提取适配尚未完成")

    def publish(self, device_serial: str, reply: dict[str, Any]) -> dict[str, Any]:
        raise UnsupportedOperation(f"{self.display_name}发布适配尚未完成")

    def verify(self, device_serial: str, expected: dict[str, Any]) -> dict[str, Any]:
        raise UnsupportedOperation(f"{self.display_name}发布核验适配尚未完成")


class PlannedAdapter(PlatformAdapter):
    def __init__(self, platform_id: str, display_name: str):
        self.platform_id = platform_id
        self.display_name = display_name

    def detect_login(self, device_serial: str) -> str:
        return "unknown"

    def detect_reply_capabilities(
        self, device_serial: str, target: dict[str, Any]
    ) -> ReplyCapabilities:
        return ReplyCapabilities(message=f"{self.display_name}能力等待真机验证")

