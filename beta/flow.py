"""베타 테스트 흐름: 시작 안내 → 과업 6개(홈 A/B 비교 4개 + 공통 2개) → 마지막 질문 → 끝.

- 과업을 시작하면 시간을 재고, 목표 화면에 닿으면 성공으로 자동 판정한다.
- 과업이 끝나면 '얼마나 쉬웠나요?'(SEQ, 1~7)를 묻는다. 회차마다 마지막엔 홈 인상(1~5)도 묻는다.
- 홈 두 안(A: 이전 홈, B: 지금 홈)은 참여 순번대로 A→B, B→A를 번갈아 배정한다.

상태는 st.session_state.beta(dict) 하나에 둔다.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

import streamlit as st

import db
from beta import log
from beta.sandbox import create_sandbox, next_number
from components.ui import large_title

ss = st.session_state

TASKS = {
    "today": "오늘 꺼내 보면 좋을 편지를 펼쳐 보세요",
    "find_seoyeon": "서연님에게 받은 2023년 손편지를 찾아 펼쳐 보세요",
    "find_jimin": "지민님에게 받은 2024년 손편지를 찾아 펼쳐 보세요",
    "reply": "지민님에게 우표를 붙여 답장을 보내 보세요",
    "today_more": "오늘 골라 둔 다른 편지도 하나 펼쳐 보세요",
}
# 시트에 적을 과업·단계 이름
TASK_NAMES = {
    "today": "오늘의 편지 펼치기",
    "find_seoyeon": "서연 2023 손편지 찾기",
    "find_jimin": "지민 2024 손편지 찾기",
    "reply": "지민에게 답장 보내기",
    "today_more": "다른 편지도 읽기",
}
PHASE_NAMES = {"final": "마지막 질문", "done": "끝", "free": "자유롭게 둘러보기"}
FIND_TARGETS = {"find_seoyeon": ("서연", 2023), "find_jimin": ("지민", 2024)}

# 홈 두 안의 설명 (마지막 선호 질문에서 어느 홈인지 떠올리게)
HOME_LOOKS = {
    "A": "오늘의 편지 여러 장이 옆으로 넘어가고, 사람이 목록으로 보이는 홈",
    "B": "편지 한 통이 크게 보이고, 사람이 색 카드로 보이는 홈",
}


def _steps(order: str) -> list[dict]:
    first, second = order
    return [
        {"task": "today", "home": first, "round": 1},
        {"task": "find_seoyeon", "home": first, "round": 1, "ask_home": True},
        {"task": "today", "home": second, "round": 2},
        {"task": "find_jimin", "home": second, "round": 2, "ask_home": True},
        {"task": "reply", "home": "B", "round": 3},
        {"task": "today_more", "home": "B", "round": 3},
    ]


# ---------- 켜기 ----------

def enabled() -> bool:
    """베타 테스트 모드인가. 주소에 ?beta=1이 있거나 Secrets의 [beta] enabled = true면 켠다."""
    if "beta_mode" not in ss:
        on = st.query_params.get("beta") == "1"
        if not on and st.secrets.load_if_toml_exists():
            on = bool(st.secrets.get("beta", {}).get("enabled", False))
        ss.beta_mode = on
    return ss.beta_mode


def setup() -> None:
    """접속자마다 샘플 서랍 사본을 만들고, 이 세션의 DB를 그 사본으로 바꾼다."""
    if "beta" not in ss:
        pid = uuid.uuid4().hex[:6]
        ss.db_path = str(create_sandbox(pid))
        ss.beta = {"pid": pid, "order": "", "phase": "intro", "step": 0, "last_view": None}
    db.set_path_provider(lambda: Path(st.session_state.get("db_path") or db.DB_PATH))


def _state() -> dict:
    return ss.beta


def _step() -> dict | None:
    b = _state()
    steps = _steps(b["order"]) if b["order"] else []
    return steps[b["step"]] if b["phase"] in ("task", "rate") and b["step"] < len(steps) else None


def home_variant() -> str:
    """지금 보여 줄 홈: 과업 중이면 그 과업의 안(A/B), 아니면 지금 홈(B)."""
    if not ss.get("beta_mode") or "beta" not in ss:
        return "B"
    step = _step()
    return step["home"] if step else "B"


def today_exclude() -> frozenset[int]:
    """오늘의 편지에서 뺄 편지: '찾아 펼쳐 보기' 과업의 정답 편지.

    오늘의 편지로 먼저 보여 주면 찾는 과업의 답을 미리 알려 주는 셈이라 뺀다. 베타가 아니면 빈 집합.
    """
    if not ss.get("beta_mode") or "beta" not in ss:
        return frozenset()
    b = _state()
    if "exclude" not in b:
        b["exclude"] = frozenset().union(*(_target_letter_ids(task) for task in FIND_TARGETS))
    return b["exclude"]


def blocks_app() -> bool:
    """앱 화면 대신 베타 화면(시작 안내·마지막 질문·끝)을 보여 줄 차례인가."""
    return _state()["phase"] in ("intro", "final", "done")


def _base() -> list:
    """모든 기록 줄 앞에 붙는 참여자·순서."""
    b = _state()
    return [b.get("label", b["pid"]), b["order"]]


# ---------- 과업 진행 ----------

def _target_letter_ids(task: str) -> set[int]:
    uid, today = ss.demo_user_id, ss.demo_date
    if task in ("today", "today_more"):
        ids = [x.letter.id for x in db.pick_today_letters(uid, today, exclude=today_exclude())]
        return set(ids if task == "today" else ids[1:])
    name, year = FIND_TARGETS[task]
    for relation in db.list_relations(uid):
        if relation.partner_name == name:
            return {
                l.id for l in db.list_timeline(uid, relation)
                if l.kind == "handwritten" and l.written_at and l.written_at.year == year
            }
    return set()


def _succeeded(task: str, page) -> bool:
    if task == "reply":
        result = ss.get("write_result")
        return page.url_path == "write" and bool(result) and result["name"] == "지민"
    letter_id = st.query_params.get("id", "")
    return page.url_path == "letter" and letter_id.isdigit() and int(letter_id) in _target_letter_ids(task)


def track(page) -> None:
    """매 실행마다: 화면 이동을 남기고, 과업 성공을 판정한다."""
    b = _state()
    if b["phase"] == "intro":
        return
    step = _step()
    view = [page.title, "&".join(f"{k}={v}" for k, v in sorted(st.query_params.items()))]
    if view != b["last_view"]:
        b["last_view"] = view
        where = (
            [step["round"], step["home"], TASK_NAMES[step["task"]]] if step
            else ["", "B", PHASE_NAMES.get(b["phase"], b["phase"])]
        )
        log.write("events", *_base(), *where, *view)
    if step and b["phase"] == "task" and "result" not in b and _succeeded(step["task"], page):
        b["result"] = "성공"
        b["seconds"] = round(time.time() - b["started"], 1)


def _start_step(index: int) -> None:
    b = _state()
    b.update(step=index, phase="task", started=time.time())
    b.pop("result", None)
    b.pop("seconds", None)


def task_banner() -> None:
    """화면 위 과업 안내. 성공하면 [다음], 그 전에는 [건너뛸게요]."""
    b = _state()
    step = _step()
    if not step or b["phase"] != "task":
        return
    total = len(_steps(b["order"]))
    done = "result" in b
    with st.container(key="beta_task"):
        status = "잘 해냈어요" if done else TASKS[step["task"]]
        st.html(
            f'<div class="kk-beta-task"><span>과업 {b["step"] + 1}/{total}</span><p>{status}</p></div>'
        )
        if done:
            if st.button("다음", type="primary", width="stretch", key="beta_next"):
                b["phase"] = "rate"
                st.rerun()
        elif st.button("잘 모르겠어요, 건너뛸게요", type="tertiary", key="beta_skip"):
            b["result"] = "건너뜀"
            b["seconds"] = round(time.time() - b["started"], 1)
            b["phase"] = "rate"
            st.rerun()


@st.dialog("얼마나 쉬웠나요?", dismissible=False)
def _rate_dialog() -> None:
    b = _state()
    step = _step()
    key = f"beta_seq_{b['step']}"
    st.segmented_control(
        "쉬웠던 정도", list(range(1, 8)), key=key, label_visibility="collapsed", width="stretch"
    )
    st.html('<div class="kk-beta-scale"><span>1 매우 어려움</span><span>7 매우 쉬움</span></div>')

    if step.get("ask_home"):
        st.html('<p class="kk-beta-q">방금 쓴 홈 화면은 어떤 곳에 가까웠나요?</p>')
        st.segmented_control(
            "홈 인상", list(range(1, 6)), key=f"beta_home_{b['step']}",
            label_visibility="collapsed", width="stretch",
        )
        st.html(
            '<div class="kk-beta-scale"><span>1 편지를 정리·보관하는 곳</span>'
            "<span>5 마음을 다시 꺼내 보는 곳</span></div>"
        )
        if step["round"] == 1:
            st.html('<p class="kk-beta-note">다음은 모양이 다른 홈에서 비슷한 일을 해 볼게요.</p>')

    if st.button("다음", type="primary", width="stretch", key="beta_rate_next"):
        log.write(
            "tasks", *_base(), step["round"], step["home"], TASK_NAMES[step["task"]],
            b["result"], b["seconds"], ss.get(key) or "",
        )
        if step.get("ask_home"):
            log.write("answers", *_base(), "홈 인상(1 보관~5 꺼내 봄)", step["home"],
                      ss.get(f"beta_home_{b['step']}") or "", "")
        if b["step"] + 1 < len(_steps(b["order"])):
            _start_step(b["step"] + 1)
        else:
            b["phase"] = "final"
        st.switch_page("views/drawer.py")


def rate_dialog() -> None:
    if _state()["phase"] == "rate":
        _rate_dialog()


# ---------- 앱 대신 보여 주는 화면 ----------

def _intro() -> None:
    large_title("꼬깃 베타 테스트", "몇 번이고 다시 펼쳐 보고 싶은 마음.")
    st.html(
        '<div class="kk-beta-intro">'
        "<p>꼬깃은 받은 손편지를 보관하고, 마음이 필요한 날 다시 꺼내 보는 앱이에요. "
        "<b>하은님의 샘플 서랍</b>으로 여섯 가지 일을 해 보고, 짧은 질문에 답해 주세요. 5분쯤 걸려요.</p>"
        "<ul>"
        "<li>정답은 없어요. 앱을 시험하는 거지, 여러분을 시험하는 게 아니에요.</li>"
        "<li>막히면 '건너뛸게요'를 눌러도 괜찮아요. 그것도 좋은 단서예요.</li>"
        "<li>과업마다 걸린 시간과 지나간 화면, 질문 답이 기록돼요. "
        "이름·연락처는 받지 않고, 사진도 올리지 않아요.</li>"
        "</ul></div>"
    )
    if st.button("시작하기", type="primary", width="stretch", key="beta_start"):
        b = _state()
        n = next_number()
        b["order"] = "AB" if n % 2 else "BA"
        b["label"] = f"P{n:02d}-{b['pid'][:4]}"
        log.write("answers", *_base(), "시작", "", n, "")
        _start_step(0)
        st.switch_page("views/drawer.py")


def _final() -> None:
    b = _state()
    first, second = b["order"]
    large_title("마지막 질문이에요", "거의 다 왔어요")
    choice = st.radio(
        "지친 날 꼬깃을 연다면, 어느 홈이 더 좋을까요?",
        [first, second],
        format_func=lambda v: f"{'첫' if v == first else '두'} 번째로 쓴 홈 · {HOME_LOOKS[v]}",
        index=None,
        key="beta_prefer",
    )
    reason = st.text_input("그렇게 고른 이유를 한 줄로 적어 주세요 (선택)", max_chars=200, key="beta_reason")
    extra = st.text_area("불편했거나 바라는 점이 있다면 (선택)", max_chars=500, key="beta_extra")
    if st.button("보내기", type="primary", width="stretch", key="beta_submit", disabled=choice is None):
        log.write("answers", *_base(), "더 좋은 홈", choice, "", reason.strip())
        if extra.strip():
            log.write("answers", *_base(), "불편·바라는 점", "", "", extra.strip())
        b["phase"] = "done"
        st.rerun()
    if choice is None:
        st.caption("홈을 하나 고르면 보낼 수 있어요")


def _done() -> None:
    large_title("고마워요", "답해 주신 내용은 꼬깃을 다듬는 데 쓸게요.")
    st.html('<p class="kk-beta-note">이제 창을 닫아도 돼요. 더 둘러보고 싶다면 자유롭게 써 보세요.</p>')
    if st.button("꼬깃 더 둘러보기", width="stretch", key="beta_free"):
        _state()["phase"] = "free"
        st.switch_page("views/drawer.py")


def render_screen() -> None:
    {"intro": _intro, "final": _final, "done": _done}[_state()["phase"]]()
