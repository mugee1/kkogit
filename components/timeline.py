"""한 사람과의 편지 목록(시간순, 해가 바뀌면 연도 구분). 편지 묶음과 편지 읽기 화면이 함께 쓴다.

카드 모양은 components/letter_card.py의 timeline_entry, 스타일은 theme.css의 .kk-entry.
"""

from __future__ import annotations

import streamlit as st

import db
from components.letter_card import timeline_entry
from components.ui import tappable
from models import Letter, Relation


def letter_timeline(
    user_id: int,
    relation: Relation,
    letters: list[Letter],
    *,
    key: str,
    current_id: int | None = None,
) -> int | None:
    """편지 카드 목록을 그리고, 누른 편지의 id를 돌려준다. current_id는 '읽는 중'으로 표시한다."""
    my_name = db.get_user(user_id).nickname
    picked = None
    with st.container(key=key, gap="small"):
        year = None
        for letter in letters:
            if letter.written_at and letter.written_at.year != year:
                year = letter.written_at.year
                st.html(f'<p class="kk-year">{year}</p>')
            sent_by_me = letter.sender_user_id == user_id
            from_name = my_name if sent_by_me else relation.partner_name
            current = letter.id == current_id
            entry = timeline_entry(
                letter,
                from_name,
                sent_by_me=sent_by_me,
                unread=db.is_unread(user_id, letter),
                current=current,
            )
            label = "지금 읽고 있는 편지" if current else f"{from_name}의 편지 펼쳐 보기"
            if tappable(f"{key}_{letter.id}", entry, label):
                picked = letter.id
    return picked
