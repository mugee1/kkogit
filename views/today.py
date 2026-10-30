"""오늘의 편지: 홈에서 '다른 편지도 읽어 볼까요?'로 들어온다. 오늘 골라 둔 편지를 한 장씩 세로로 보여 준다.

같은 사용자·같은 날짜면 홈과 같은 편지가 같은 순서로 나온다(db.pick_today_letters).
"""

import streamlit as st

import db
from components.letter_card import today_card
from components.ui import back_button, large_title, tappable

user_id = st.session_state.demo_user_id
today = st.session_state.demo_date

back_button("서랍", "views/drawer.py")
large_title("오늘 꺼내 보면 좋을 편지", f"{today:%m월 %d일}에 골라 둔 편지예요")

items = db.pick_today_letters(user_id, today)
if not items:
    st.html('<p class="kk-empty">오늘은 골라 둔 편지가 없어요</p>')
    st.stop()

with st.container(gap="medium"):
    for item in items:
        label = f"{item.relation.partner_name}님의 편지 펼쳐 보기"
        if tappable(f"today_{item.letter.id}", today_card(item, today), label):
            st.switch_page("views/letter.py", query_params={"id": item.letter.id})
