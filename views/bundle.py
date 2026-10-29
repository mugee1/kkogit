"""편지 묶음 상세: 한 사람과의 손편지·주고받은 편지를 시간순으로. 하단 [답장 쓰기]."""

import streamlit as st

import db
from components.timeline import letter_timeline
from components.ui import back_button, large_title
from models import RELATION_LABELS

back_button("서랍", "views/drawer.py")

user_id = st.session_state.demo_user_id
rid = st.query_params.get("relation", "")
relation = db.get_relation(int(rid)) if rid.isdigit() else None

if relation is None or relation.user_id != user_id:
    large_title("편지 묶음을 찾을 수 없어요")
    st.stop()

letters = db.list_timeline(user_id, relation)

subtitle = f"{RELATION_LABELS[relation.type]} · 편지 {len(letters)}통"
first = next((l.written_at for l in letters if l.written_at), None)
if first:
    subtitle += f" · {first.year}년부터"
large_title(relation.partner_name, subtitle)

# ---------- 시간순 편지 (해가 바뀌면 연도 구분) ----------
if not letters:
    st.html('<p class="kk-empty">아직 이 묶음에 편지가 없어요</p>')
else:
    picked = letter_timeline(user_id, relation, letters, key="timeline")
    if picked:
        st.switch_page("views/letter.py", query_params={"id": picked})

# ---------- 답장 쓰기 (하단 고정, 엄지 영역) ----------
with st.container(key="bundle_cta"):
    if st.button("답장 쓰기", icon=":material/edit:", type="primary", width="stretch"):
        st.toast("답장 쓰기는 곧 열려요")  # 답장 쓰기·보내기 단계에서 작성 화면으로 연결한다
