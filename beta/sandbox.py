"""접속자마다 샘플 서랍 사본을 만든다.

샘플 데이터(seed.py)로 만든 원본 DB를 한 번 만들어 두고, 접속할 때마다 복사해서 쓴다.
그래서 테스터가 답장을 보내도 다른 테스터의 서랍이나 data/app.db는 바뀌지 않는다.
"""

from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path

import streamlit as st

import db

BETA_DIR = db.DATA_DIR / "beta"
SANDBOX_DIR = BETA_DIR / "sandboxes"
TEMPLATE_PATH = BETA_DIR / "template.db"
COUNTER_PATH = BETA_DIR / "counter.txt"
KEEP_HOURS = 24  # 이보다 오래된 사본은 지운다

_counter_lock = threading.Lock()


@st.cache_resource(show_spinner=False)
def _template() -> Path:
    """샘플 데이터만 든 원본 DB. 서버가 뜰 때 한 번 새로 만든다."""
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_PATH.unlink(missing_ok=True)
    db.init_db(TEMPLATE_PATH)
    return TEMPLATE_PATH


def _cleanup() -> None:
    limit = time.time() - KEEP_HOURS * 3600
    for path in SANDBOX_DIR.glob("*.db"):
        if path.stat().st_mtime < limit:
            path.unlink(missing_ok=True)


def create_sandbox(participant: str) -> Path:
    """이 접속자의 샘플 서랍 사본을 만들고 경로를 돌려준다."""
    template = _template()
    _cleanup()
    path = SANDBOX_DIR / f"{participant}.db"
    shutil.copyfile(template, path)
    return path


def next_number() -> int:
    """참여 순번(1, 2, 3...). 홈 두 안의 순서를 번갈아 배정하는 데 쓴다.

    서버가 다시 뜨면 1부터 다시 센다. 참여자 코드에 임의 글자를 붙여 겹치지 않게 한다.
    """
    with _counter_lock:
        BETA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            n = int(COUNTER_PATH.read_text()) + 1
        except (FileNotFoundError, ValueError):
            n = 1
        COUNTER_PATH.write_text(str(n))
        return n
