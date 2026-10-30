"""마음을 건넨 사람들 전체: 홈의 '모두 보기'로 들어온다. 이름으로 찾고, 연인/친구로 걸러 본다.

카드는 홈과 같은 정사각형 색 카드 2열(components/people.py). 순서는 최근에 편지가 오간 순.
"""

import streamlit as st

import db
from components.people import people_grid
from components.ui import back_button, large_title
from models import RELATION_LABELS

user_id = st.session_state.demo_user_id

back_button("서랍", "views/drawer.py")
large_title("마음을 건넨 사람들")

bundles = db.list_bundles(user_id)

# 이름으로 찾기 (편지를 찾는 기준 1순위가 보낸 사람)
query = st.text_input(
    "이름으로 찾기",
    key=f"people_query_u{user_id}",
    placeholder="이름으로 찾기",
    max_chars=20,
    icon=":material/search:",
    label_visibility="collapsed",
).strip()

# 연인/친구가 섞여 있을 때만 걸러 보기. 숫자는 붙이지 않는다
types = {s.relation.type for s in bundles}
show = "all"
if len(types) > 1:
    labels = {"all": "전체", **RELATION_LABELS}
    show = st.segmented_control(
        "관계",
        list(labels),
        format_func=labels.get,
        default="all",
        required=True,
        key=f"people_type_u{user_id}",
        label_visibility="collapsed",
        width="stretch",
    )

shown = [
    s for s in bundles
    if (show == "all" or s.relation.type == show) and query.lower() in s.relation.partner_name.lower()
]
if not shown:
    st.html('<p class="kk-empty">찾는 이름이 없어요</p>')
else:
    picked = people_grid(shown, bundles)
    if picked:
        st.switch_page("views/bundle.py", query_params={"relation": picked})
