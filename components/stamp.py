"""우표: 쓴 편지 오른쪽 위에 붙는 우표. 모양은 styles/theme.css의 .kk-stamp.

assets/stamps/에 우표 이미지가 생기기 전까지는 CSS로 그린 기본 우표를 쓴다.
"""

from __future__ import annotations


def stamp_html(stamp: str | None) -> str:
    """우표 HTML. 지금은 'default' 한 종류(톱니 테두리 + 해와 언덕 낙서)."""
    if not stamp:
        return ""
    return '<span class="kk-stamp" role="img" aria-label="우표"><i></i></span>'
