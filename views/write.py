"""답장 쓰기: 직전 편지(접어서 보기) → 본문 → 우표(바텀시트) → [보내기] → 접혀서 날아가는 모션.

쓰던 본문과 고른 우표는 데모 사용자·묶음마다 session_state에 남아,
직전 편지를 다시 읽으러 나갔다 와도 이어서 쓸 수 있다.
"""

from html import escape

import streamlit as st

import db
from components.letter_card import kind_label
from components.letter_view import handwritten_pages, written_letter
from components.motion import fold_and_send
from components.stamp import STAMPS, stamp_html, stamp_option, stamp_row
from components.ui import back_button, format_date, large_title, section_title, tappable

ss = st.session_state
user_id = ss.demo_user_id
today = ss.demo_date

# ---------- 보낸 뒤: 접혀서 날아가는 모션 ----------
result = ss.get("write_result")
if result:
    st.html(fold_and_send(stamp_html(result["stamp"])))
    st.html(
        '<div class="kk-motion-after">'
        '<h1 class="kk-large-title">편지를 보냈어요</h1>'
        f'<p class="kk-subtitle">{escape(result["name"])}님의 답장을 기다리고 있어요</p>'
        "</div>"
    )
    with st.container(key="write_cta"):
        if st.button("편지 묶음으로", type="primary", width="stretch"):
            ss.pop("write_result")
            st.switch_page("views/bundle.py", query_params={"relation": result["relation_id"]})
        if st.button("서랍으로", width="stretch"):
            ss.pop("write_result")
            st.switch_page("views/drawer.py")
    st.stop()

# ---------- 누구에게 ----------
rid = st.query_params.get("relation", "")
relation = db.get_relation(int(rid)) if rid.isdigit() else None
if relation is None or relation.user_id != user_id:
    back_button("서랍", "views/drawer.py")
    large_title("편지 묶음을 찾을 수 없어요")
    st.stop()

partner = relation.partner_name
me = db.get_user(user_id)
BODY_KEY = f"write_body_u{user_id}_r{relation.id}"
STAMP_KEY = f"write_stamp_u{user_id}_r{relation.id}"
ss.setdefault(STAMP_KEY, None)

if st.button(partner, icon=":material/chevron_left:", key="back", type="tertiary"):
    st.switch_page("views/bundle.py", query_params={"relation": relation.id})

large_title("답장 쓰기", f"To. {partner}")

# ---------- 직전 편지: 접어 두었다가 펼쳐 본다 ----------
timeline = db.list_timeline(user_id, relation)
if timeline:
    last = timeline[-1]
    sent_by_me = last.sender_user_id == user_id
    when = f" · {format_date(last.written_at)}" if last.written_at else ""
    with st.expander(f"직전 편지 · {kind_label(last, sent_by_me)}{when}", icon=":material/mail:"):
        if last.kind == "handwritten":
            st.html(handwritten_pages(last))
        else:
            to_name, from_name = (partner, me.nickname) if sent_by_me else (me.nickname, partner)
            st.html(written_letter(last, to_name, from_name))


# ---------- 우표 바텀시트 ----------
@st.dialog("우표를 골라 주세요", width="small")
def stamp_sheet() -> None:
    st.html('<p class="kk-sheet-sub">편지 오른쪽 위에 붙여 드릴게요</p>')
    ids = list(STAMPS)
    for row in range(0, len(ids), 2):
        for col, stamp_id in zip(st.columns(2, gap="small"), ids[row:row + 2]):
            with col:
                tile = stamp_option(stamp_id, ss[STAMP_KEY] == stamp_id)
                if tappable(f"stamp_{stamp_id}", tile, f"{STAMPS[stamp_id]} 우표 붙이기"):
                    ss[STAMP_KEY] = stamp_id
                    ss.pop("write_notice", None)
                    st.rerun()


# ---------- 본문 ----------
section_title("편지")
body = st.text_area(
    "편지 본문",
    key=BODY_KEY,
    placeholder=f"{partner}님에게 하고 싶은 이야기를 적어 주세요",
    height=280,
    max_chars=2000,
    label_visibility="collapsed",
)
if body.strip() and ss.get("write_notice"):
    ss.pop("write_notice")
st.html(f'<p class="kk-hint kk-write-from">From. {escape(me.nickname)}</p>')

# ---------- 우표 ----------
stamp = ss[STAMP_KEY]
if tappable("write_stamp", stamp_row(stamp), "우표 바꾸기" if stamp else "우표 고르기"):
    stamp_sheet()

# ---------- 보내기 (하단 고정, 엄지 영역) ----------
# 입력 중에는 본문이 아직 서버에 없을 수 있어 버튼을 막지 않고, 누른 뒤에 확인한다.
with st.container(key="write_cta"):
    if ss.get("write_notice"):
        st.html(f'<p class="kk-hint kk-hint--center">{ss.write_notice}</p>')
    label = "보내기" if stamp else "우표 고르기"
    if st.button(label, type="primary", width="stretch", icon=":material/send:" if stamp else None):
        if not body.strip():
            ss.write_notice = "편지를 먼저 적어 주세요"
            st.rerun()
        elif not stamp:
            ss.pop("write_notice", None)
            stamp_sheet()
        else:
            db.send_letter(user_id, relation, body, stamp, today)
            ss.write_result = {"relation_id": relation.id, "name": partner, "stamp": stamp}
            for key in (BODY_KEY, STAMP_KEY, "write_notice"):
                ss.pop(key, None)
            st.rerun()
