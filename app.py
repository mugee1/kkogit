"""꼬깃 진입점: 전역 스타일, 데모 컨트롤(사이드바), 라우팅, 하단 탭 바."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import streamlit as st

import db
from components.tabbar import active_tab_css, render_tabbar

st.set_page_config(
    page_title="꼬깃",
    page_icon=":material/mail:",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------- 데이터 준비 ----------
@st.cache_resource
def _init_db_once() -> bool:
    db.init_db()
    return True


_init_db_once()

# ---------- 세션 상태 기본값 ----------
users = db.list_users()
st.session_state.setdefault("demo_user_id", users[0].id)
st.session_state.setdefault("demo_date", date.today())

# 데모 컨트롤 위젯의 값은 st.switch_page로 화면을 옮길 때 지워진다.
# 실제 값은 demo_user_id·demo_date에 따로 두고, 매 실행 위젯에 다시 채운다.
st.session_state["_demo_user"] = st.session_state.demo_user_id
st.session_state["_demo_date"] = st.session_state.demo_date


def _on_demo_user_change() -> None:
    st.session_state.demo_user_id = st.session_state._demo_user
    st.session_state.demo_user_switched = True  # 라우팅 뒤에 서랍으로 보낸다


def _on_demo_date_change() -> None:
    st.session_state.demo_date = st.session_state._demo_date

# 전역 CSS (컬러 토큰의 단일 출처)
css = (Path(__file__).parent / "styles" / "theme.css").read_text(encoding="utf-8")
bg_color = re.search(r"--bg:\s*(#[0-9A-Fa-f]{6})", css).group(1)

# ---------- 사이드바: 데모 컨트롤 (실제 서비스 UI 아님) ----------
with st.sidebar:
    st.subheader("데모 컨트롤")
    st.caption("시연용 설정이에요. 실제 앱 화면에는 나오지 않아요.")
    nicknames = {u.id: u.nickname for u in users}
    st.segmented_control(
        "사용자",
        options=list(nicknames),
        format_func=nicknames.get,
        required=True,
        key="_demo_user",
        on_change=_on_demo_user_change,
        width="stretch",
    )
    st.date_input("데모 날짜", key="_demo_date", on_change=_on_demo_date_change, format="YYYY.MM.DD")

    # iPhone '홈 화면에 추가' 시 Safe Area(env())가 동작하도록 viewport와 웹앱 메타를 보강한다.
    # 사이드바에 두어 본문 레이아웃에 빈 공간이 생기지 않게 한다.
    st.html(
        """<script>
        (function () {
          const BG = "__BG__";
          const head = document.head;
          const vp = head.querySelector('meta[name="viewport"]');
          if (vp && !vp.content.includes("viewport-fit")) {
            vp.content += ", viewport-fit=cover";
          }
          const metas = {
            "apple-mobile-web-app-capable": "yes",
            "mobile-web-app-capable": "yes",
            "apple-mobile-web-app-title": "꼬깃",
            "apple-mobile-web-app-status-bar-style": "default",  // 라이트 화면: 상태바 글자를 어둡게
            "theme-color": BG,
          };
          for (const [name, content] of Object.entries(metas)) {
            if (!head.querySelector(`meta[name="${name}"]`)) {
              const m = document.createElement("meta");
              m.name = name;
              m.content = content;
              head.appendChild(m);
            }
          }
        })();
        </script>""".replace("__BG__", bg_color),
        unsafe_allow_javascript=True,
    )

# ---------- 라우팅 ----------
PAGES = {
    "drawer": st.Page("views/drawer.py", title="서랍", default=True),
    "keep": st.Page("views/keep.py", title="보관하기", url_path="keep"),
    "me": st.Page("views/me.py", title="내 정보", url_path="me"),
}
# 탭에 없는 하위 화면과, 그 화면에서 선택 상태로 둘 탭
SUB_PAGES = {
    "drawer": [
        st.Page("views/bundle.py", title="편지 묶음", url_path="bundle"),
        st.Page("views/letter.py", title="편지", url_path="letter"),
        st.Page("views/write.py", title="답장 쓰기", url_path="write"),
    ],
}
page = st.navigation(
    list(PAGES.values()) + [p for subs in SUB_PAGES.values() for p in subs],
    position="hidden",
)
active_tab = next((tab_id for tab_id, p in PAGES.items() if p.url_path == page.url_path), None)
if active_tab is None:
    active_tab = next(
        (tab_id for tab_id, subs in SUB_PAGES.items() if page.url_path in [p.url_path for p in subs]),
        None,
    )

# 보관 완료·보내기 완료 화면은 한 번만 보여 준다. 다른 화면으로 나가면 닫는다.
if active_tab != "keep":
    st.session_state.pop("keep_result", None)
if page.url_path != "write":
    st.session_state.pop("write_result", None)

# 데모 사용자를 바꾸면 서랍(홈)에서 다시 시작한다. 보던 편지·묶음은 다른 사용자에게 없을 수 있다.
if st.session_state.pop("demo_user_switched", False):
    st.session_state.pop("keep_result", None)
    st.session_state.pop("write_result", None)
    if page.url_path != PAGES["drawer"].url_path:
        st.switch_page(PAGES["drawer"])

# ---------- 전역 스타일 ----------
# theme.css + 선택된 탭 스타일을 한 번에 주입한다.
css += active_tab_css(active_tab)
st.html(f"<style>{css}</style>")

render_tabbar(PAGES, page)

page.run()
