"""비교용 이전 홈(A안). 홈을 '편지 한 통 + 사람 카드'(B안, views/drawer.py)로 바꾸기 전 모습.

- 제목 "○○님의 편지가 모여 있어요"
- 오늘 다시 펼쳐 볼 편지: 종이 카드 3장을 가로로 넘겨 본다(캐러셀)
- 편지 묶음: 사람마다 한 줄 목록 + 편지 수
도착 배너만 지금 것과 같게 두어, 홈의 모양만 비교되게 한다. 커밋 bdf03a1의 홈에서 옮겨 왔다.
"""

from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

import db
from beta.flow import today_exclude
from components.letter_card import _paper, arrived_banner, letter_cover
from components.ui import format_date, large_title, section_title, tappable, time_ago
from models import RELATION_LABELS, BundleSummary, LetterInDrawer


def _today_card(item: LetterInDrawer, today: date) -> str:
    """오늘 다시 펼쳐 볼 편지 카드: 손편지면 표지, 쓴 편지면 본문 일부 + 보낸 사람·얼마나 됐는지."""
    letter = item.letter
    inner = letter_cover(letter.cover_image, letter.cover_design)
    if inner is None:
        inner = f'<p class="kk-a-paper-text">{escape(letter.body)}</p>'
    pages = f" · {len(letter.images)}장" if len(letter.images) > 1 else ""
    return (
        f'<div class="kk-a-today">'
        f"{_paper(inner, postmark=letter.written_at)}"
        f'<p class="kk-a-meta"><b>{escape(item.relation.partner_name)}</b>'
        f"<span>{time_ago(letter.written_at, today)}{pages}</span></p>"
        f"</div>"
    )


def _bundle_row(summary: BundleSummary) -> str:
    """편지 묶음 한 줄: 종이 묶음 썸네일 + 이름 + 관계·편지 수·마지막 날짜."""
    rel = summary.relation
    cover = letter_cover(summary.cover_image, summary.cover_design, 120) or '<span class="kk-lines"></span>'
    stack = (
        f'<div class="kk-a-stack{" kk-a-stack--single" if summary.letter_count < 2 else ""}"'
        f' aria-hidden="true"><span></span>{_paper(cover, extra_class="kk-paper--mini")}</div>'
    )
    meta = [RELATION_LABELS[rel.type], f"편지 {summary.letter_count}통"]
    if summary.last_written_at:
        meta.append(format_date(summary.last_written_at))
    new = f'<span class="kk-new"><i></i>새 편지 {summary.unread_count}</span>' if summary.unread_count else ""
    return (
        f'<div class="kk-a-bundle-row">{stack}'
        f'<div class="kk-bundle-body"><p class="kk-bundle-name">{escape(rel.partner_name)}{new}</p>'
        f'<p class="kk-bundle-meta">{" · ".join(meta)}</p></div>'
        f'<span class="kk-chevron" aria-hidden="true">›</span></div>'
    )


def render_home_a() -> None:
    user = db.get_user(st.session_state.demo_user_id)
    today = st.session_state.demo_date

    large_title("서랍", f"{user.nickname}님의 편지가 모여 있어요")

    arrived = db.list_arrived(user.id)
    if arrived:
        if tappable("arrived", arrived_banner(arrived), "도착한 편지 펼쳐 보기"):
            st.switch_page("views/letter.py", query_params={"id": arrived[0].letter.id})

    today_items = db.pick_today_letters(user.id, today, exclude=today_exclude())
    if today_items:
        section_title("오늘 다시 펼쳐 볼 편지")
        with st.container(key="today_carousel", horizontal=True, wrap=False, gap=12):
            for item in today_items:
                label = f"{item.relation.partner_name}님의 편지 펼쳐 보기"
                if tappable(f"today_{item.letter.id}", _today_card(item, today), label, width=148):
                    st.switch_page("views/letter.py", query_params={"id": item.letter.id})

    bundles = db.list_bundles(user.id)
    section_title("편지 묶음", f"{len(bundles)}명" if bundles else None)
    with st.container(gap=None):
        for summary in bundles:
            rel = summary.relation
            if tappable(f"bundle_{rel.id}", _bundle_row(summary), f"{rel.partner_name}님과의 편지 묶음 열기"):
                st.switch_page("views/bundle.py", query_params={"relation": rel.id})
