"""종이가 접히는 모션 HTML(보관하기, 보내기). 스타일·키프레임은 styles/theme.css의 .kk-motion-*.

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


def fold_and_send(stamp: str = "") -> str:
    """보내기: 우표 붙은 편지가 반으로 접힌 뒤 날아간다. (접힘 320ms → 날아감 320ms)

    stamp는 접히는 위쪽 절반에 붙일 우표 HTML.
    """
    return (
        '<div class="kk-motion-keep kk-motion-send" aria-hidden="true">'
        '<div class="kk-motion-paper">'
        '<div class="kk-motion-half kk-motion-bottom"><span class="kk-lines"></span></div>'
        '<div class="kk-motion-half kk-motion-top">'
        f'<div class="kk-motion-face"><span class="kk-lines"></span>{stamp}<i class="kk-fold"></i></div>'
        '<div class="kk-motion-back"></div>'
        "</div></div>"
        "</div>"
    )
