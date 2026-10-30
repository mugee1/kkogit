"""편지 관련 카드 HTML: 오늘 꺼내 보면 좋을 편지 카드, 마음을 건넨 사람 카드, 묶음 안의 편지 한 통, 도착 배너.

화면 로직 없이 HTML 문자열만 만든다. 스타일은 styles/theme.css의 .kk-* 클래스.
"""

from __future__ import annotations

import base64
import io
from datetime import date
from html import escape
from pathlib import Path

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
    """'오늘 꺼내 보면 좋을 편지' 한 통: 화면 너비의 편지 한 장 (홈과 오늘의 편지 목록이 함께 쓴다).

    - 기억하고 싶은 한 줄이 있으면 그 한 줄이 먼저 보인다(펼치면 원본 손글씨).
    - 없으면 쓴 편지는 본문 앞부분, 손편지는 표지 썸네일과 '펼치면 원본 손글씨가 보여요'.
    """
    letter = item.letter
    if letter.highlight:
        body = f'<p class="kk-feature-quote">{escape(letter.highlight)}</p>'
    elif letter.kind == "written":
        body = f'<p class="kk-feature-text">{escape(letter.body)}</p>'
    else:
        cover = letter_cover(letter.cover_image, letter.cover_design, 200) or '<span class="kk-lines"></span>'
        pages = f" · {len(letter.images)}장" if len(letter.images) > 1 else ""
        body = (
            f'<div class="kk-feature-photo">{_paper(cover, extra_class="kk-paper--mini")}'
            f'<p><b>손편지{pages}</b><span>펼치면 원본 손글씨가 보여요</span></p></div>'
        )
    mark = _postmark(letter.written_at, "kk-postmark--inline") if letter.written_at else ""
    return (
        f'<article class="kk-today-card"><i class="kk-fold"></i>{body}'
        f'<div class="kk-feature-foot"><p class="kk-feature-from">From. {escape(item.relation.partner_name)}'
        f"<span>{time_ago(letter.written_at, today)}</span></p>{mark}</div>"
        f"</article>"
    )


PERSON_COLORS = 6  # 사람 카드 색 수 (theme.css의 --card-1~6)
CARD_IMAGE_DIR = Path(__file__).parent.parent / "assets" / "cards"


@st.cache_data(show_spinner=False)
def card_image_uri(color: int) -> str | None:
    """assets/cards/card_{색 번호}.png(또는 .jpg·.webp·.svg)가 있으면 data URI. 없으면 None."""
    for ext, mime in (("png", "image/png"), ("jpg", "image/jpeg"), ("webp", "image/webp"), ("svg", "image/svg+xml")):
        path = CARD_IMAGE_DIR / f"card_{color}.{ext}"
        if path.is_file():
            return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()
    return None


def person_color(relation_id: int) -> int:
    """사람마다 정해진 카드 색(1~6). 묶음 id로 정해서 다시 열어도 같은 색이다."""
    return (relation_id - 1) % PERSON_COLORS + 1


def person_card(summary: BundleSummary) -> str:
    """마음을 건넨 사람 한 명: 정사각형 색 카드 + 이름 + 관계·마지막 날짜.

    카드 위 이미지는 assets/cards/card_{색 번호}.*로 따로 넣는다. 없으면 색만 보인다.
    편지 수처럼 쌓이는 숫자는 보여 주지 않는다 (조용한 화면).
    """
    rel = summary.relation
    color = person_color(rel.id)
    uri = card_image_uri(color)
    image = f'<img src="{uri}" alt="">' if uri else ""
    meta = [RELATION_LABELS[rel.type]]
    if summary.last_written_at:
        meta.append(format_date(summary.last_written_at))
    new = '<span class="kk-person-new"><i></i>새 편지</span>' if summary.unread_count else ""
    return (
        f'<div class="kk-person kk-person--{color}">{image}{new}'
        f'<div class="kk-person-body"><p class="kk-person-name">{escape(rel.partner_name)}</p>'
        f'<p class="kk-person-meta">{" · ".join(meta)}</p></div></div>'
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
    """'편지가 도착했어요' 배너 (앱 내 알림). 통수는 세지 않고, 코랄은 점 하나만.

    제목은 무슨 일인지 바로 알게, 부제는 누가 마음을 보냈는지 다정하게.
    """
    first = arrived[0]
    name = escape(first.relation.partner_name)
    others = len({x.relation.id for x in arrived}) - 1
    title = "편지가 도착했어요"
    sub = f"{name}님 외 {others}명이 마음을 보냈어요" if others else f"{name}님이 마음을 보냈어요"
    return (
        f'<div class="kk-banner">'
        f'<span class="kk-icon kk-banner-icon" aria-hidden="true">mail</span>'
        f'<div><p class="kk-banner-title">{title}<i class="kk-dot" aria-hidden="true"></i></p>'
        f'<p class="kk-banner-sub">{sub}</p></div>'
        f'<span class="kk-chevron" aria-hidden="true">›</span></div>'
    )
