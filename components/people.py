"""마음을 건넨 사람들: 정사각형 색 카드 2열. 홈(최대 4명)과 사람들 화면이 함께 쓴다.

카드 모양은 components/letter_card.py의 person_card, 격자는 theme.css의 .st-key-people.
"""

from __future__ import annotations

import streamlit as st

from components.letter_card import person_card, person_colors
from components.ui import tappable
from models import BundleSummary

HOME_PEOPLE = 4  # 홈에 보여 줄 사람 수 (2×2). 더 많으면 '모두 보기'


def home_order(bundles: list[BundleSummary]) -> list[BundleSummary]:
    """홈에 먼저 보일 순서: 새 편지가 있는 사람 → 최근에 편지가 오간 사람."""
    return sorted(bundles, key=lambda s: not s.unread_count)  # list_bundles가 최근 순이라 순서가 유지된다


def people_grid(shown: list[BundleSummary], everyone: list[BundleSummary]) -> int | None:
    """사람 카드 격자를 그리고, 누른 사람의 묶음(relation) id를 돌려준다.

    shown은 보여 줄 사람, everyone은 그 사용자의 모든 사람(색을 화면마다 같게 정하려고 쓴다).
    """
    colors = person_colors(everyone)
    picked = None
    with st.container(key="people"):
        for summary in shown:
            rel = summary.relation
            card = person_card(summary, colors[rel.id])
            if tappable(f"bundle_{rel.id}", card, f"{rel.partner_name}님과의 편지 묶음 열기"):
                picked = rel.id
    return picked
