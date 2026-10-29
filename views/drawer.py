"""서랍(홈): 도착한 편지 배너, 오늘 다시 펼쳐 볼 편지, 사람별 편지 묶음."""

import streamlit as st

import db
from components.letter_card import arrived_banner, bundle_row, today_card
from components.ui import large_title, section_title, tappable

user = db.get_user(st.session_state.demo_user_id)
today = st.session_state.demo_date

large_title("서랍", f"{user.nickname}님의 편지가 모여 있어요")

# ---------- 도착한 편지 배너 (앱 내 알림) ----------
arrived = db.list_arrived(user.id)
if arrived:
    if tappable("arrived", arrived_banner(arrived), "도착한 편지 펼쳐 보기"):
        st.switch_page("views/letter.py", query_params={"id": arrived[0].letter.id})

# ---------- 오늘 다시 펼쳐 볼 편지 ----------
today_items = db.pick_today_letters(user.id, today)
if today_items:
    section_title("오늘 다시 펼쳐 볼 편지")
    with st.container(key="today_carousel", horizontal=True, wrap=False, gap=12):
        for item in today_items:
            label = f"{item.relation.partner_name}님의 편지 펼쳐 보기"
            if tappable(f"today_{item.letter.id}", today_card(item, today), label, width=148):
                st.switch_page("views/letter.py", query_params={"id": item.letter.id})

# ---------- 사람별 편지 묶음 ----------
bundles = db.list_bundles(user.id)
section_title("편지 묶음", f"{len(bundles)}명" if bundles else None)
if not bundles:
    st.html('<p class="kk-empty">아직 서랍이 비어 있어요. 받은 손편지를 먼저 넣어 볼까요?</p>')
    if st.button("손편지 보관하기", type="primary", width="stretch"):
        st.switch_page("views/keep.py")
else:
    with st.container(gap=None):
        for summary in bundles:
            rel = summary.relation
            if tappable(f"bundle_{rel.id}", bundle_row(summary), f"{rel.partner_name}님과의 편지 묶음 열기"):
                st.switch_page("views/bundle.py", query_params={"relation": rel.id})
