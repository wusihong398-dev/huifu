from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReplyFormat(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    TEXT_IMAGE = "text_image"


@dataclass(frozen=True)
class ScreeningDecision:
    approved: bool
    relevance_score: int
    need_score: int
    reply_value_score: int
    risk_score: int
    reason: str
    reply_angle: str = ""

    def requires_human_review(self) -> bool:
        return self.risk_score > 30 or 60 <= self.relevance_score < 80


@dataclass(frozen=True)
class ReplyPlan:
    should_reply: bool
    target_type: str
    target_id: str
    goal: str
    recommended_format: ReplyFormat
    reply_angle: str
    fallback_format: ReplyFormat = ReplyFormat.TEXT
    reason: str = ""

