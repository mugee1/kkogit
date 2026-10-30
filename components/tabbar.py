"""하단 탭 바: 서랍 / 보관하기 / 내 정보."""

from __future__ import annotations

import streamlit as st

# (탭 id, 라벨, 아이콘)
TABS = [
    ("drawer", "서랍", ":material/inbox:"),
    ("keep", "보관하기", ":material/add_a_photo:"),
    ("me", "내 정보", ":material/person:"),
]


def active_tab_css(active: str | None) -> str:
    """선택된 탭 스타일: 코랄 아이콘 + Text Primary 굵은 라벨 + 상단 포인트 바(--primary).

    색만으로 구분하지 않도록 굵기와 바를 함께 쓴다. app.py에서 전역 CSS와 함께 주입한다.
    """
    if not active:
        return ""
    return f"""
    .st-key-tab_{active} button {{ color: var(--text); }}
    .st-key-tab_{active} button [data-testid="stIconMaterial"] {{ color: var(--primary); }}
    .st-key-tab_{active} button p {{ font-weight: 600; }}
    .st-key-tab_{active} button::before {{
        content: ""; position: absolute; top: -1px; left: 50%;
        width: 24px; height: 2px; transform: translateX(-50%);
        background: var(--primary);
    }}
    """


def render_tabbar(pages: dict[str, st.Page], current: st.Page) -> None:
    """화면 하단에 고정되는 탭 바. 위치·모양은 styles/theme.css의 .st-key-tabbar.

    하위 화면(편지 묶음 등)에서는 서랍 탭이 선택돼 보여도, 누르면 서랍 첫 화면으로 돌아간다.
    """
    with st.container(key="tabbar", horizontal=True):
        for tab_id, label, icon in TABS:
            if st.button(label, icon=icon, key=f"tab_{tab_id}", type="tertiary"):
                if pages[tab_id].url_path != current.url_path:
                    st.switch_page(pages[tab_id])
