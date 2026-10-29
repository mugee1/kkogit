"""꼬깃 데이터 구조 정의."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

RelationType = Literal["friend", "lover"]
LetterKind = Literal["handwritten", "written"]  # 손편지(사진) / 앱에서 쓴 편지
LetterStatus = Literal["draft", "sent", "read"]

RELATION_LABELS: dict[str, str] = {"friend": "친구", "lover": "연인"}

COVER_DESIGNS = 5             # 꼬깃 표지(기본 썸네일) 종류 수
COVER_DESIGN_PREFIX = "design:"


@dataclass
class User:
    id: int
    nickname: str
    created_at: datetime


@dataclass
class Relation:
    """한 사용자가 가진 '사람별 편지 묶음'의 상대.

    상대도 앱 사용자면 partner_user_id로 연결하고,
    상대 쪽에도 나를 가리키는 Relation이 따로 있다.
    """

    id: int
    user_id: int
    partner_name: str
    partner_user_id: int | None
    type: RelationType
    created_at: datetime


@dataclass
class Letter:
    """편지 한 통.

    - 손편지: relation_id = 보관한 사람의 관계, receiver_user_id = 보관한 사람,
      sender_user_id = None. 보관한 사람만 볼 수 있다.
    - 쓴 편지: sender_user_id → receiver_user_id 로 오가며,
      relation_id = 보낸 사람 쪽 관계.
    """

    id: int
    relation_id: int
    sender_user_id: int | None
    receiver_user_id: int | None
    kind: LetterKind
    images: list[str] = field(default_factory=list)  # data/images/ 기준 상대 경로
    body: str = ""
    stamp: str | None = None
    written_at: date | None = None  # 받은 날짜(손편지) / 쓴 날짜(쓴 편지)
    status: LetterStatus = "read"
    created_at: datetime | None = None
    # 서랍에 보일 표지: "design:1"~"design:5"(꼬깃 표지) 또는 images 중 한 장의 경로.
    # 비어 있으면 첫 장 사진을 쓴다(표지 기능 이전에 보관한 편지).
    cover: str | None = None

    @property
    def cover_design(self) -> int | None:
        """꼬깃 표지 번호(1~5). 사진 표지면 None."""
        if self.cover and self.cover.startswith(COVER_DESIGN_PREFIX):
            return int(self.cover.removeprefix(COVER_DESIGN_PREFIX))
        return None

    @property
    def cover_image(self) -> str | None:
        """표지로 쓸 사진 경로. 꼬깃 표지거나 사진이 없으면 None."""
        if self.cover_design:
            return None
        return self.cover or (self.images[0] if self.images else None)


@dataclass
class BundleSummary:
    """서랍 목록에 보여 줄 사람별 편지 묶음 요약."""

    relation: Relation
    letter_count: int
    last_written_at: date | None
    unread_count: int          # 도착했지만 아직 펼쳐 보지 않은 편지 수
    cover_image: str | None    # 가장 최근 손편지의 표지 사진 (없으면 None)
    cover_design: int | None   # 가장 최근 손편지가 꼬깃 표지면 그 번호


@dataclass
class LetterInDrawer:
    """내 서랍 기준으로 본 편지: 편지 + 그 편지가 속한 나의 관계."""

    letter: Letter
    relation: Relation
