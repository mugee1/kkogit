"""종이가 접히고 펼쳐지는 모션 HTML. 스타일·키프레임은 styles/theme.css의 .kk-motion-*.

CSS 애니메이션만 쓴다(자바스크립트·iframe 없음). 움직임 줄이기 설정이면 바로 끝 상태로 보인다.
"""

from __future__ import annotations


def fold_into_drawer(cover: str = "") -> str:
    """보관하기: 종이가 반으로 접힌 뒤 서랍 안으로 들어간다. (접힘 320ms → 들어감 280ms)

    cover는 종이를 채울 표지 HTML(사진 img 또는 꼬깃 표지). 비우면 빈 종이로 접는다.
    """
    return (
        '<div class="kk-motion-keep" aria-hidden="true">'
        '<div class="kk-motion-paper">'
        f'<div class="kk-motion-half kk-motion-bottom">{cover}</div>'
        '<div class="kk-motion-half kk-motion-top">'
        f'<div class="kk-motion-face">{cover}<i class="kk-fold"></i></div>'
        '<div class="kk-motion-back"></div>'
        "</div></div>"
        '<div class="kk-motion-drawer"><span></span></div>'
        "</div>"
    )
