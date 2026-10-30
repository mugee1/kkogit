"""서랍(홈): 시간대 인사, 도착한 편지 배너, 오늘 꺼내 보면 좋을 편지, 마음을 건넨 사람들."""

import streamlit as st

import db
from beta.flow import home_variant, today_exclude
from components.letter_card import arrived_banner, today_card
from components.people import HOME_PEOPLE, home_order, people_grid
from components.ui import large_title, now, section_title, tappable


def greeting(hour: int) -> str:
    """시간대에 맞는 인사. 앱이 직접 위로하지 않고, 수고한 사람으로 맞이한다."""
    if 5 <= hour < 11:
        return "좋은 아침이에요"
    if 11 <= hour < 17:
        return "잠깐 쉬어 가요"
    if 17 <= hour < 22:
        return "오늘 하루 수고했어요"
    return "오늘도 애썼어요"


# 베타 테스트에서 이전 홈(A안)과 비교하는 차례면 그 홈을 보여 준다
if home_variant() == "A":
    from beta.home_a import render_home_a

    render_home_a()
    st.stop()

user = db.get_user(st.session_state.demo_user_id)
today = st.session_state.demo_date

large_title("서랍", f"{user.nickname}님, {greeting(now().hour)}")

# ---------- 도착한 편지 배너 (앱 내 알림) ----------
arrived = db.list_arrived(user.id)
if arrived:
    if tappable("arrived", arrived_banner(arrived), "도착한 편지 펼쳐 보기"):
        st.switch_page("views/letter.py", query_params={"id": arrived[0].letter.id})

# ---------- 오늘 꺼내 보면 좋을 편지: 한 통만 담백하게 ----------
# 오늘 골라 둔 편지가 더 있으면 작게 권하고, 오늘의 편지 화면에 모아 둔다
today_items = db.pick_today_letters(user.id, today, exclude=today_exclude())
if today_items:
    section_title("오늘 꺼내 보면 좋을 편지")
    first = today_items[0]
    if tappable(f"today_{first.letter.id}", today_card(first, today), f"{first.relation.partner_name}님의 편지 펼쳐 보기"):
        st.switch_page("views/letter.py", query_params={"id": first.letter.id})
    if len(today_items) > 1:
        if st.button(
            "다른 편지도 읽어 볼까요?",
            key="today_more",
            type="tertiary",
            icon=":material/chevron_right:",
            icon_position="right",
        ):
            st.switch_page("views/today.py")

# ---------- 마음을 건넨 사람들 (사람별 편지 묶음) ----------
# 홈에는 2×2(4명)까지만 둔다. 더 많으면 '모두 보기'로 사람들 화면에 모아 둔다.
# 사람 수 같은 숫자는 쌓이는 압박이 되어 보여 주지 않는다
bundles = db.list_bundles(user.id)
with st.container(key="people_head", horizontal=True, vertical_alignment="center"):
    section_title("마음을 건넨 사람들")
    if len(bundles) > HOME_PEOPLE:
        if st.button("모두 보기", key="people_all", type="tertiary", icon=":material/chevron_right:", icon_position="right"):
            st.switch_page("views/people.py")
if not bundles:
    st.html('<p class="kk-empty">서랍이 아직 가벼워요. 오래 간직하고 싶은 편지가 있다면 넣어 둘까요?</p>')
    if st.button("손편지 보관하기", type="primary", width="stretch"):
        st.switch_page("views/keep.py")
else:
    picked = people_grid(home_order(bundles)[:HOME_PEOPLE], bundles)
    if picked:
        st.switch_page("views/bundle.py", query_params={"relation": picked})
