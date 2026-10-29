"""여러 화면에서 쓰는 작은 UI 조각."""

from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st


def large_title(title: str, subtitle: str | None = None) -> None:
    """화면 상단 큰 제목(Large Title, 28px Bold)."""
    sub = f'<p class="kk-subtitle">{escape(subtitle)}</p>' if subtitle else ""
    st.html(f'<h1 class="kk-large-title">{escape(title)}</h1>{sub}')


def section_title(title: str, aside: str | None = None) -> None:
    """섹션 제목(20px SemiBold). aside는 오른쪽의 보조 정보(예: 개수)."""
    side = f'<span class="kk-section-aside">{escape(aside)}</span>' if aside else ""
    st.html(f'<div class="kk-section-title"><h2>{escape(title)}</h2>{side}</div>')


def tappable(key: str, html: str, label: str, width: int | str = "stretch") -> bool:
    """HTML로 그린 카드 전체를 누를 수 있게 한다.

    카드 위에 투명한 st.button을 덮는다. label은 스크린 리더가 읽는 이름이다.
    모양은 theme.css의 [class*="st-key-tap_"], [class*="st-key-open_"] 규칙.
    """
    with st.container(key=f"tap_{key}", gap=None, width=width):
        st.html(html)
        return st.button(label, key=f"open_{key}")


def back_button(label: str, page: str) -> None:
    """좌상단 뒤로 가기 ‹ 버튼."""
    if st.button(label, icon=":material/chevron_left:", key="back", type="tertiary"):
        st.switch_page(page)


def format_date(d: date) -> str:
    return f"{d:%Y.%m.%d}"


def time_ago(d: date, today: date) -> str:
    """'2년 전', '3개월 전'처럼 받은 지 얼마나 됐는지."""
    months = (today.year - d.year) * 12 + (today.month - d.month) - (today.day < d.day)
    if months >= 12:
        return f"{months // 12}년 전"
    if months >= 1:
        return f"{months}개월 전"
    days = (today - d).days
    return "오늘" if days <= 0 else f"{days}일 전"
