"""꼬깃 표지: 사진 대신 서랍에 보이는 기본 썸네일 5종. 모양은 styles/theme.css의 .kk-cover--1~5.

1 봉투 · 2 줄 노트 · 3 우표 · 4 소인 · 5 접힌 자국
"""

from __future__ import annotations

import random

from models import COVER_DESIGNS


def random_design() -> int:
    """보관할 때 꼬깃 표지 하나를 무작위로 고른다."""
    return random.randint(1, COVER_DESIGNS)


def cover_html(design: int) -> str:
    """종이(.kk-paper) 안을 채우는 표지 HTML."""
    text = "To." if design == 5 else ""
    return f'<div class="kk-cover kk-cover--{design}"><i></i><b>{text}</b></div>'
