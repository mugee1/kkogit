"""손편지 보관하기: 1) 사진 → 2) 누구에게·언제 → 보관 완료(접혀서 서랍으로).

사진은 [서랍에 넣기]를 누를 때 저장한다. 그 전까지는 session_state에만 있고,
중간에 다른 탭으로 나갔다 와도 이어서 할 수 있다.
"""

from html import escape

import streamlit as st

import db
from components.covers import cover_html, random_design
from components.letter_card import cover_option, photo_tile, photo_uri
from components.motion import fold_into_drawer
from components.ui import format_date, large_title, section_title, tappable
from models import RELATION_LABELS

ss = st.session_state
user_id = ss.demo_user_id
today = ss.demo_date

DESIGN = "design"  # 표지 선택값: 꼬깃 표지

ss.setdefault("keep_step", "photos")  # photos → info
ss.setdefault("keep_photos", [])      # prepare_photo()를 거친 JPEG 바이트, 올린 순서대로
ss.setdefault("keep_upload_n", 0)     # 올린 뒤 업로더를 비우려고 key를 바꾼다
ss.setdefault("keep_new_type", None)  # 새로운 사람의 관계(friend/lover)
ss.setdefault("keep_design", random_design())  # 이번 편지에 들어갈 꼬깃 표지(1~5)
ss.setdefault("keep_cover", DESIGN)  # 표지: "design"(꼬깃 표지) 또는 사진 순서(0부터)

# 보낸 사람 위젯은 데모 사용자마다 따로 둔다 (사용자를 바꾸면 서랍이 달라지므로)
SENDER_KEY = f"keep_sender_u{user_id}"
NAME_KEY = f"keep_name_u{user_id}"
NEW = "new"


def reset_keep() -> None:
    """보관하기를 처음 상태로."""
    for key in [k for k in ss if k.startswith(("keep_sender_", "keep_name_", "keep_date"))]:
        del ss[key]
    ss.keep_step = "photos"
    ss.keep_photos = []
    ss.keep_new_type = None
    ss.keep_design = random_design()
    ss.keep_cover = DESIGN
    ss.pop("keep_notice", None)


# ---------- 콜백 ----------

def add_photos(key: str) -> None:
    """업로더에 올라온 사진을 보관용 JPEG로 바꿔 목록 뒤에 붙인다."""
    failed = 0
    for f in ss.get(key) or []:
        try:
            ss.keep_photos.append(db.prepare_photo(f.getvalue()))
        except Exception:  # 손상됐거나 이미지가 아닌 파일
            failed += 1
    ss.keep_upload_n += 1
    ss.keep_notice = f"열 수 없는 사진 {failed}장은 빼 두었어요" if failed else None


MOVE_FORWARD, MOVE_BACK, REMOVE = "앞으로 옮기기", "뒤로 옮기기", "빼기"


def photo_action(i: int) -> None:
    """사진 순서 바꾸기·빼기. 표지로 고른 사진은 자리를 따라간다."""
    photos = ss.keep_photos
    action = ss.get(f"keep_photo_menu_{i}")
    if action in (MOVE_FORWARD, MOVE_BACK):
        j = i - 1 if action == MOVE_FORWARD else i + 1
        if not 0 <= j < len(photos):
            return
        photos[i], photos[j] = photos[j], photos[i]
        if ss.keep_cover == i:
            ss.keep_cover = j
        elif ss.keep_cover == j:
            ss.keep_cover = i
    elif action == REMOVE:
        photos.pop(i)
        if ss.keep_cover == i:
            ss.keep_cover = DESIGN
        elif ss.keep_cover != DESIGN and ss.keep_cover > i:
            ss.keep_cover -= 1


def on_name_change() -> None:
    """새로운 사람 이름을 다 쓰면 관계 바텀시트를 띄운다."""
    if ss.get(NAME_KEY, "").strip() and ss.keep_new_type is None:
        ss.keep_open_sheet = True


@st.dialog("어떤 사이인가요?", width="small")
def relation_sheet(name: str) -> None:
    """관계 선택 바텀시트 (모양은 theme.css의 .stDialog)."""
    st.html(f'<p class="kk-sheet-sub">{escape(name)}님과의 편지 묶음에 표시돼요</p>')
    for value, label in RELATION_LABELS.items():
        selected = ss.keep_new_type == value
        if st.button(
            label,
            key=f"keep_type_{value}",
            icon=":material/check:" if selected else None,
            type="secondary",
            width="stretch",
        ):
            ss.keep_new_type = value
            st.rerun()


# ---------- 보관 완료 ----------

result = ss.get("keep_result")
if result:
    st.html(fold_into_drawer(result["cover"]))
    pages = f" {result['pages']}장" if result["pages"] > 1 else ""
    st.html(
        '<div class="kk-motion-after">'
        '<h1 class="kk-large-title">서랍에 잘 넣어 뒀어요</h1>'
        f'<p class="kk-subtitle">{escape(result["name"])}님에게 받은 손편지{pages}'
        f' · {format_date(result["received_at"])}</p>'
        f'<div class="kk-suggest"><p class="kk-suggest-title">고마운 마음, {escape(result["name"])}님에게도 전해 볼까요?</p>'
        '<p class="kk-suggest-sub">답장은 이 손편지와 같은 묶음에 차곡차곡 쌓여요</p></div>'
        "</div>"
    )
    with st.container(key="keep_cta"):
        if st.button("답장해 보기", type="primary", width="stretch"):
            ss.pop("keep_result")
            st.switch_page("views/bundle.py", query_params={"relation": result["relation_id"]})
        if st.button("서랍으로", width="stretch"):
            ss.pop("keep_result")
            st.switch_page("views/drawer.py")
    st.stop()


# ---------- 1단계: 사진 ----------

def upload_area(big: bool) -> None:
    """사진 찍기·고르기 영역. 보이지 않는 업로더를 카드 위에 덮는다 (theme.css의 .st-key-keep_upload)."""
    if big:
        card = (
            '<div class="kk-upload kk-upload--big">'
            '<span class="kk-icon" aria-hidden="true">add_a_photo</span>'
            '<p class="kk-upload-title">사진 찍기 · 고르기</p>'
            '<p class="kk-upload-sub">여러 장이면 한 번에 올려도 돼요</p></div>'
        )
    else:
        card = (
            '<div class="kk-upload kk-upload--tile">'
            '<span class="kk-icon" aria-hidden="true">add</span>'
            '<p class="kk-upload-title">더 올리기</p></div>'
        )
    key = f"keep_uploader_{ss.keep_upload_n}"
    with st.container(key="keep_upload", gap=None):
        st.html(card)
        st.file_uploader(
            "손편지 사진 찍기 또는 고르기",
            type=["jpg", "jpeg", "png", "heic"],
            accept_multiple_files=True,
            key=key,
            on_change=add_photos,
            args=(key,),
            label_visibility="collapsed",
        )


if ss.keep_step == "photos":
    photos = ss.keep_photos
    st.html('<p class="kk-step">1 / 2</p>')
    large_title("보관하기", "받은 손편지를 찍어 주세요")

    if not photos:
        upload_area(big=True)
    else:
        cells = [*range(len(photos)), None]  # 마지막 칸은 '더 올리기'
        for row in range(0, len(cells), 2):
            cols = st.columns(2, gap="small")
            for col, i in zip(cols, cells[row:row + 2]):
                with col:
                    if i is None:
                        upload_area(big=False)
                        continue
                    st.html(photo_tile(photos[i], i + 1))
                    actions = [
                        a for a, ok in [
                            (MOVE_FORWARD, i > 0),
                            (MOVE_BACK, i < len(photos) - 1),
                            (REMOVE, True),
                        ] if ok
                    ]
                    st.menu_button(
                        f"{i + 1}번째 장",
                        actions,
                        key=f"keep_photo_menu_{i}",
                        on_click=photo_action,
                        args=(i,),
                        type="tertiary",
                        icon=":material/more_horiz:",
                        width="stretch",
                    )
        st.html(f'<p class="kk-hint">{len(photos)}장 · 첫 장이 서랍에서 표지가 돼요</p>')

    if ss.get("keep_notice"):
        st.html(f'<p class="kk-hint">{escape(ss.keep_notice)}</p>')

    with st.container(key="keep_cta"):
        if st.button("다음", type="primary", width="stretch", disabled=not photos):
            ss.keep_step = "info"
            st.rerun()
    st.stop()


# ---------- 2단계: 누구에게·언제 ----------

if not ss.keep_photos:  # 사진 없이 들어온 경우
    ss.keep_step = "photos"
    st.rerun()

if st.button("사진", icon=":material/chevron_left:", key="back", type="tertiary"):
    ss.keep_step = "photos"
    st.rerun()

st.html('<p class="kk-step">2 / 2</p>')
large_title("누구에게 받았나요", f"사진 {len(ss.keep_photos)}장을 서랍에 넣어 둘게요")

# 보낸 사람: 기존 편지 묶음 + 새로운 사람
relations = db.list_relations(user_id)
names = {r.id: r.partner_name for r in relations}
section_title("보낸 사람")
if relations:
    sender = st.pills(
        "보낸 사람",
        [*names, NEW],
        format_func=lambda v: ":material/add: 새로운 사람" if v == NEW else names[v],
        key=SENDER_KEY,
        label_visibility="collapsed",
    )
else:
    sender = NEW

relation_id = None
new_name = ""
if sender == NEW:
    new_name = st.text_input(
        "이름",
        key=NAME_KEY,
        placeholder="보낸 사람 이름",
        max_chars=20,
        on_change=on_name_change,
        label_visibility="collapsed",
    ).strip()
    same = next((r for r in relations if r.partner_name == new_name), None)
    if same:
        # 같은 이름의 묶음이 이미 있으면 새로 만들지 않고 거기에 넣는다
        relation_id = same.id
        st.html(f'<p class="kk-hint">서랍에 있는 {escape(same.partner_name)}님 묶음에 넣을게요</p>')
    elif new_name:
        label = RELATION_LABELS.get(ss.keep_new_type)
        if st.button(
            f"관계 · {label}" if label else "관계 고르기",
            key="keep_type_open",
            icon=":material/expand_less:",
            width="stretch",
        ):
            relation_sheet(new_name)
        elif ss.pop("keep_open_sheet", False):
            relation_sheet(new_name)
elif sender is not None:
    relation_id = sender

# 받은 날짜: 데모 날짜가 오늘이고, 그 이후는 고를 수 없다
section_title("받은 날짜")
if "keep_date" not in ss or ss.keep_date > today:
    ss.keep_date = today
received_at = st.date_input(
    "받은 날짜", key="keep_date", max_value=today, format="YYYY.MM.DD", label_visibility="collapsed"
)

# 서랍에 보일 표지: 꼬깃 표지(기본, 5종 중 무작위) 또는 올린 사진 중 한 장
section_title("서랍에 보일 표지")
cover_options = [(DESIGN, cover_html(ss.keep_design), "꼬깃 표지")] + [
    (i, f'<img src="{photo_uri(data)}" alt="">', f"{i + 1}장") for i, data in enumerate(ss.keep_photos)
]
with st.container(key="keep_covers", horizontal=True, gap=12):
    for value, inner, label in cover_options:
        name = "꼬깃 표지" if value == DESIGN else f"{label} 사진"
        tile = cover_option(inner, label, ss.keep_cover == value)
        if tappable(f"cover_{value}", tile, f"{name}를 표지로 고르기", width=72):
            ss.keep_cover = value
            st.rerun()
st.html(
    '<p class="kk-hint">'
    + ("편지를 펼치면 원본 손글씨가 보여요" if ss.keep_cover == DESIGN else "서랍에서 이 사진이 표지로 보여요")
    + "</p>"
)

ready = relation_id is not None or bool(new_name and ss.keep_new_type)
if sender is None:
    hint = "보낸 사람을 골라 주세요"
elif sender == NEW and not new_name:
    hint = "보낸 사람 이름을 적어 주세요"
elif not ready:
    hint = "관계를 골라 주세요"
else:
    hint = None

with st.container(key="keep_cta"):
    if hint:
        st.html(f'<p class="kk-hint kk-hint--center">{hint}</p>')
    if st.button("서랍에 넣기", type="primary", width="stretch", disabled=not ready):
        letter_id, kept_relation = db.keep_handwritten(
            user_id,
            ss.keep_photos,
            received_at,
            relation_id=relation_id,
            partner_name=new_name,
            relation_type=ss.keep_new_type,
            cover_design=ss.keep_design if ss.keep_cover == DESIGN else None,
            cover_page=0 if ss.keep_cover == DESIGN else ss.keep_cover,
        )
        ss.keep_result = {
            "letter_id": letter_id,
            "relation_id": kept_relation,
            "name": names.get(relation_id, new_name),
            "pages": len(ss.keep_photos),
            "received_at": received_at,
            "cover": next(inner for value, inner, _ in cover_options if value == ss.keep_cover),
        }
        reset_keep()
        st.rerun()
