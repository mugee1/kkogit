"""편지 읽기: 카드가 펼쳐지며 손편지 원본(여러 장 넘겨 보기) 또는 쓴 편지 본문과 우표를 보여 준다.

- 제목 위에 편지 종류(손편지 / 받은 편지 / 보낸 편지)를 표시한다.
- 받은 편지를 펼치면 읽음으로 바꾼다(서랍의 도착 배너에서 사라진다).
- 아래 목록에서 같은 묶음의 다른 편지를 골라 읽는다(전체 / 손편지 / 주고받은 편지로 걸러 보기).
"""

import streamlit as st

import db
from components.letter_card import kind_chip
from components.letter_view import SWIPE_SCRIPT, handwritten_pages, scroll_to_top, unfold, written_letter
from components.timeline import letter_timeline
from components.ui import back_button, format_date, large_title, section_title

user_id = st.session_state.demo_user_id
lid = st.query_params.get("id", "")
letter = db.get_letter(int(lid)) if lid.isdigit() else None
relation = db.relation_for_letter(user_id, letter) if letter else None

if relation is None:
    back_button("서랍", "views/drawer.py")
    large_title("편지를 찾을 수 없어요")
    st.stop()

if st.button(relation.partner_name, icon=":material/chevron_left:", key="back", type="tertiary"):
    st.switch_page("views/bundle.py", query_params={"relation": relation.id})

# 받은 편지를 펼쳤으니 읽음으로
if db.is_unread(user_id, letter):
    db.mark_read(user_id, letter.id)

me = db.get_user(user_id)
sent_by_me = letter.sender_user_id == user_id
partner = relation.partner_name

# ---------- 제목: 종류(손편지 / 받은 편지 / 보낸 편지) + 누구의 편지인지 ----------
if letter.kind == "handwritten":
    title = f"{partner}님의 손편지"
elif sent_by_me:
    title = f"{partner}님에게 보낸 편지"
else:
    title = f"{partner}님의 편지"
st.html(kind_chip(letter, sent_by_me))
large_title(title, format_date(letter.written_at) if letter.written_at else None)

# ---------- 편지 (펼쳐지는 전환) ----------
if letter.kind == "handwritten":
    # 사진이 여러 장이면 옆으로 밀어 넘겨 본다 (스와이프는 손편지에만)
    body = handwritten_pages(letter) + (SWIPE_SCRIPT if len(letter.images) > 1 else "")
else:
    to_name, from_name = (partner, me.nickname) if sent_by_me else (me.nickname, partner)
    body = written_letter(letter, to_name, from_name)
st.html(unfold(body) + scroll_to_top(letter.id), unsafe_allow_javascript=True)

# ---------- 이 묶음의 편지: 골라서 읽기 ----------
timeline = db.list_timeline(user_id, relation)
if len(timeline) > 1:
    section_title(f"{partner}님과의 편지", f"{len(timeline)}통")

    handwritten = [l for l in timeline if l.kind == "handwritten"]
    written = [l for l in timeline if l.kind == "written"]
    groups = {"all": timeline, "handwritten": handwritten, "written": written}
    labels = {"all": "전체", "handwritten": "손편지", "written": "주고받은 편지"}
    show = "all"
    if handwritten and written:  # 두 종류가 다 있을 때만 걸러 보기
        show = st.segmented_control(
            "편지 종류",
            list(groups),
            format_func=lambda k: f"{labels[k]} {len(groups[k])}",
            default="all",
            required=True,
            key=f"letter_filter_{relation.id}",
            label_visibility="collapsed",
            width="stretch",
        )

    picked = letter_timeline(user_id, relation, groups[show], key="read_list", current_id=letter.id)
    if picked and picked != letter.id:
        st.query_params["id"] = picked
        st.rerun()
