"""우표: 쓴 편지 오른쪽 위에 붙는 우표. 그림은 assets/stamps/*.svg, 모양은 styles/theme.css의 .kk-stamp.

st.html은 <svg> 태그를 지우므로 SVG를 <img>(data URI)로 넣는다. 이미지 안에는 CSS 변수가 닿지 않아,
선(.ln)과 코랄 포인트(.pt) 색은 theme.css의 토큰 값을 읽어 SVG 안에 채운다.
디자이너 우표가 생기면 같은 파일 이름으로 바꿔 끼우면 된다.
"""

from __future__ import annotations

import base64
import re
from functools import cache
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent.parent
STAMP_DIR = ROOT / "assets" / "stamps"
THEME_CSS = ROOT / "styles" / "theme.css"

# 우표 id: 이름. 바텀시트에 이 순서로 보인다.
STAMPS: dict[str, str] = {
    "sun": "해와 언덕",
    "flower": "꽃 한 송이",
    "plane": "종이비행기",
    "moon": "달과 별",
}
DEFAULT_STAMP = "sun"  # 우표 종류가 생기기 전의 'default' 우표도 해와 언덕으로 보여 준다


def _token(name: str) -> str:
    """theme.css의 컬러 토큰 값(HEX)."""
    css = THEME_CSS.read_text(encoding="utf-8")
    return re.search(rf"--{name}:\s*(#[0-9A-Fa-f]{{6}})", css).group(1)


@cache
def _stamp_uri(stamp_id: str) -> str:
    """선·포인트 색을 채운 우표 SVG의 data URI."""
    style = (
        "<style>"
        f".ln{{fill:none;stroke:{_token('text-secondary')};stroke-width:1.6;"
        "stroke-linecap:round;stroke-linejoin:round}"
        ".ln--dash{stroke-dasharray:2 3}"
        f".pt{{fill:{_token('primary')}}}"
        "</style>"
    )
    svg = (STAMP_DIR / f"{stamp_id}.svg").read_text(encoding="utf-8")
    svg = svg.replace(">", ">" + style, 1)  # 여는 <svg ...> 태그 바로 뒤에 넣는다
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()


def stamp_name(stamp: str) -> str:
    return STAMPS.get(stamp, STAMPS[DEFAULT_STAMP])


def stamp_html(stamp: str | None, extra_class: str = "") -> str:
    """우표 HTML. stamp가 없으면 빈 문자열."""
    if not stamp:
        return ""
    stamp_id = stamp if stamp in STAMPS else DEFAULT_STAMP
    return (
        f'<span class="kk-stamp {extra_class}" role="img" aria-label="{stamp_name(stamp_id)} 우표">'
        f'<img src="{_stamp_uri(stamp_id)}" alt=""></span>'
    )


def stamp_option(stamp_id: str, selected: bool) -> str:
    """우표 고르기 칸: 우표 + 이름. 선택되면 코랄 테두리와 체크 표시 (표지 고르기와 같은 규칙)."""
    mark = '<span class="kk-icon kk-cover-check" aria-hidden="true">check</span>' if selected else ""
    state = " kk-stamp-option--selected" if selected else ""
    return (
        f'<div class="kk-stamp-option{state}">{mark}'
        f'{stamp_html(stamp_id, "kk-stamp--inline")}'
        f'<p class="kk-cover-label">{escape(STAMPS[stamp_id])}</p></div>'
    )


def stamp_row(stamp: str | None) -> str:
    """답장 쓰기의 우표 줄: 고른 우표와 이름. 아직 안 골랐으면 빈 우표 자리."""
    if stamp:
        thumb = stamp_html(stamp, "kk-stamp--inline kk-stamp--small")
        title, sub = "우표", stamp_name(stamp)
    else:
        thumb = '<span class="kk-stamp-empty" aria-hidden="true"></span>'
        title, sub = "우표 고르기", "편지 오른쪽 위에 붙여 드릴게요"
    return (
        f'<div class="kk-stamp-row">{thumb}'
        f'<div class="kk-bundle-body"><p class="kk-bundle-name">{title}</p>'
        f'<p class="kk-bundle-meta">{sub}</p></div>'
        f'<span class="kk-chevron" aria-hidden="true">›</span></div>'
    )
