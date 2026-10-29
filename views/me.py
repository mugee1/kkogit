"""내 정보. P0에서는 닉네임과 보관한 편지 수만 보여 준다."""

import streamlit as st

import db
from components.ui import large_title

user = db.get_user(st.session_state.demo_user_id)

large_title("내 정보")
st.subheader(user.nickname, anchor=False)
st.caption(f"서랍에 편지 {db.count_kept_letters(user.id)}통")
