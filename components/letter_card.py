"""편지 관련 카드 HTML: 오늘 다시 펼쳐 볼 편지 카드, 편지 묶음 행, 묶음 안의 편지 한 통, 도착 배너.

화면 로직 없이 HTML 문자열만 만든다. 스타일은 styles/theme.css의 .kk-* 클래스.
"""

from __future__ import annotations

import base64
import io
from datetime import date
from html import escape

import streamlit as st
from PIL import Image

import db
from components.covers import cover_html
from components.ui import format_date, time_ago
from models import RELATION_LABELS, BundleSummary, Letter, LetterInDrawer


def _jpeg_uri(img: Image.Image, width: int) -> str:
    img = img.convert("RGB")
    img.thumbnail((width, round(width * 1.41)))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


@st.cache_data(max_entries=200, show_spinner=False)
def thumbnail_uri(rel_path: str, width: int = 320) -> str | None:
    """data/images 안의 이미지를 작은 JPEG data URI로 만든다."""
    path = db.IMAGE_DIR / rel_path
    if not path.is_file():
        return None
    with Image.open(path) as img:
        return _jpeg_uri(img, width)


@st.cache_data(max_entries=50, show_spinner=False)
def photo_uri(data: bytes, width: int = 320) -> str:
    """아직 저장하지 않은 사진(보관 중인 JPEG 바이트)의 미리보기 data URI."""
    with Image.open(io.BytesIO(data)) as img:
        return _jpeg_uri(img, width)


def photo_tile(data: bytes, page: int) -> str:
    """보관하기의 사진 미리보기: 종이 모양 + 몇 번째 장인지."""
    inner = f'<img src="{photo_uri(data)}" alt="{page}번째 장">'
    return _paper(f'{inner}<span class="kk-page-no" aria-hidden="true">{page}</span>')


def cover_option(inner: str, label: str, selected: bool) -> str:
    """표지 고르기 칸: 작은 종이 + 이름. 선택되면 코랄 테두리와 체크 표시."""
    mark = '<span class="kk-icon kk-cover-check" aria-hidden="true">check</span>' if selected else ""
    state = " kk-cover-option--selected" if selected else ""
    return (
        f'<div class="kk-cover-option{state}"><div class="kk-cover-frame">{_paper(inner)}{mark}</div>'
        f'<p class="kk-cover-label">{escape(label)}</p></div>'
    )


def letter_cover(cover_image: str | None, cover_design: int | None, width: int = 320) -> str | None:
    """서랍에 보일 표지 HTML: 꼬깃 표지 또는 사진. 둘 다 없으면 None."""
    if cover_design:
        return cover_html(cover_design)
    uri = thumbnail_uri(cover_image, width) if cover_image else None
    return f'<img src="{uri}" alt="">' if uri else None


def _postmark(d: date, extra_class: str = "") -> str:
    """소인 모양 날짜 도장."""
    return (
        f'<span class="kk-postmark {extra_class}" aria-hidden="true">'
        f"<b>{d:%m.%d}</b><span>{d:%Y}</span></span>"
    )


def _paper(inner: str, *, postmark: date | None = None, extra_class: str = "") -> str:
    """접힌 모서리가 있는 종이(1:1.41)."""
    mark = _postmark(postmark) if postmark else ""
    return f'<div class="kk-paper {extra_class}">{inner}<i class="kk-fold"></i>{mark}</div>'


def today_card(item: LetterInDrawer, today: date) -> str:
    """'오늘 다시 펼쳐 볼 편지' 카드: 손편지면 고른 표지(사진 또는 꼬깃 표지), 쓴 편지면 본문 일부."""
    letter = item.letter
    inner = letter_cover(letter.cover_image, letter.cover_design)
    if inner is None:
        inner = f'<p class="kk-paper-text">{escape(letter.body)}</p>'
    pages = f" · {len(letter.images)}장" if len(letter.images) > 1 else ""
    return (
        f'<div class="kk-today-card">'
        f"{_paper(inner, postmark=letter.written_at)}"
        f'<p class="kk-meta"><b>{escape(item.relation.partner_name)}</b>'
        f"<span>{time_ago(letter.written_at, today)}{pages}</span></p>"
        f"</div>"
    )


def bundle_row(summary: BundleSummary) -> str:
    """사람별 편지 묶음 한 줄: 종이 묶음 썸네일 + 이름 + 관계·편지 수·마지막 날짜."""
    rel = summary.relation
    cover = letter_cover(summary.cover_image, summary.cover_design, 120) or '<span class="kk-lines"></span>'
    stack = (
        f'<div class="kk-stack{" kk-stack--single" if summary.letter_count < 2 else ""}"'
        f' aria-hidden="true"><span></span>{_paper(cover, extra_class="kk-paper--mini")}</div>'
    )

    meta = [RELATION_LABELS[rel.type], f"편지 {summary.letter_count}통"]
    if summary.last_written_at:
        meta.append(format_date(summary.last_written_at))
    new = (
        f'<span class="kk-new"><i></i>새 편지 {summary.unread_count}</span>'
        if summary.unread_count else ""
    )
    return (
        f'<div class="kk-bundle-row">{stack}'
        f'<div class="kk-bundle-body"><p class="kk-bundle-name">{escape(rel.partner_name)}{new}</p>'
        f'<p class="kk-bundle-meta">{" · ".join(meta)}</p></div>'
        f'<span class="kk-chevron" aria-hidden="true">›</span></div>'
    )


# 편지 종류: (아이콘, 이름). 묶음 목록과 편지 읽기에서 같은 이름을 쓴다.
LETTER_KINDS = {
    "handwritten": ("photo_library", "손편지"),
    "received": ("mail", "받은 편지"),
    "sent": ("send", "보낸 편지"),
}


def letter_kind(letter: Letter, sent_by_me: bool) -> str:
    """편지 종류 키: 보관한 손편지 / 앱으로 받은 편지 / 내가 쓴 편지."""
    if letter.kind == "handwritten":
        return "handwritten"
    return "sent" if sent_by_me else "received"


def kind_label(letter: Letter, sent_by_me: bool) -> str:
    """'손편지 · 2장', '받은 편지', '보낸 편지'."""
    label = LETTER_KINDS[letter_kind(letter, sent_by_me)][1]
    if letter.kind == "handwritten" and len(letter.images) > 1:
        label += f" · {len(letter.images)}장"
    return label


def kind_chip(letter: Letter, sent_by_me: bool) -> str:
    """편지 읽기 제목 위의 종류 표시: 아이콘 + 이름 (색 대신 아이콘과 글자로 구분)."""
    icon = LETTER_KINDS[letter_kind(letter, sent_by_me)][0]
    return (
        f'<p class="kk-kind"><span class="kk-icon" aria-hidden="true">{icon}</span>'
        f"{kind_label(letter, sent_by_me)}</p>"
    )


def timeline_entry(
    letter: Letter, from_name: str, *, sent_by_me: bool, unread: bool, current: bool = False
) -> str:
    """편지 묶음 안의 편지 한 통: 종이 썸네일 + From. 보낸 사람 + 종류 + 소인(날짜).

    내가 보낸 편지는 오른쪽으로, 받은 편지(손편지 포함)는 왼쪽으로 붙여 주고받은 흐름이 보이게 한다.
    current면 지금 읽고 있는 편지로 표시한다(코랄 테두리 + '읽는 중').
    """
    cover = letter_cover(letter.cover_image, letter.cover_design, 120) or '<span class="kk-lines"></span>'
    new = '<span class="kk-new"><i></i>새 편지</span>' if unread else ""
    reading = '<b class="kk-entry-reading">읽는 중</b>' if current else ""
    mark = _postmark(letter.written_at, "kk-postmark--inline") if letter.written_at else ""
    classes = "kk-entry" + (" kk-entry--sent" if sent_by_me else "") + (" kk-entry--current" if current else "")
    return (
        f'<div class="{classes}">'
        f'<div class="kk-entry-thumb" aria-hidden="true">{_paper(cover, extra_class="kk-paper--mini")}</div>'
        f'<div class="kk-entry-body"><p class="kk-entry-from">From. {escape(from_name)}{new}</p>'
        f'<p class="kk-entry-meta">{kind_label(letter, sent_by_me)}{reading}</p></div>{mark}</div>'
    )


def arrived_banner(arrived: list[LetterInDrawer]) -> str:
    """'편지가 도착했어요' 배너 (앱 내 알림)."""
    first = arrived[0]
    name = escape(first.relation.partner_name)
    if len(arrived) == 1:
        title = "편지가 도착했어요"
        sub = f"{name}님이 보낸 편지를 펼쳐 볼까요?"
    else:
        others = len({x.relation.id for x in arrived}) - 1
        title = f"편지 {len(arrived)}통이 도착했어요"
        sub = f"{name}님 외 {others}명이 보냈어요" if others else f"{name}님이 보냈어요"
    return (
        f'<div class="kk-banner">'
        f'<span class="kk-icon kk-banner-icon" aria-hidden="true">mail</span>'
        f'<div><p class="kk-banner-title">{title}</p><p class="kk-banner-sub">{sub}</p></div>'
        f'<span class="kk-chevron" aria-hidden="true">›</span></div>'
    )
