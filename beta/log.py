"""베타 테스트 기록: Google Sheets에 한 줄씩 쌓는다.

시트(탭) 세 개:
- tasks: 과업 하나에 한 줄 (성공 여부, 걸린 시간, 쉬웠던 정도)
- answers: 홈 인상·선호·이유 같은 질문 답
- events: 화면 이동 (어떤 길로 과업을 했는지 볼 때)

Secrets에 [gcp_service_account]와 [beta] sheet_url이 있고 gspread가 설치돼 있으면 Google Sheets로,
아니면 data/beta/logs/*.csv로 쓴다(로컬에서 확인할 때).
시트 쓰기는 1초 가까이 걸려서, 화면이 멈추지 않게 뒤에서 한 줄씩 보낸다.
편지 사진·본문 같은 내용은 기록하지 않는다.
"""

from __future__ import annotations

import csv
import queue
import sys
import threading
from datetime import datetime

import streamlit as st

from beta.sandbox import BETA_DIR
from components.ui import KST

COLUMNS = {
    "tasks": ["시각", "참여자", "순서", "회차", "홈", "과업", "결과", "걸린 시간(초)", "쉬웠던 정도(1~7)"],
    "answers": ["시각", "참여자", "순서", "질문", "홈", "값", "글"],
    "events": ["시각", "참여자", "순서", "회차", "홈", "과업", "화면", "상세"],
}
LOG_DIR = BETA_DIR / "logs"


class _CsvSink:
    def write(self, sheet: str, rows: list[list]) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        path = LOG_DIR / f"{sheet}.csv"
        new = not path.exists()
        with path.open("a", newline="", encoding="utf-8-sig") as f:
            out = csv.writer(f)
            if new:
                out.writerow(COLUMNS[sheet])
            out.writerows(rows)


class _SheetsSink:
    def __init__(self, account: dict, sheet_url: str) -> None:
        import gspread

        self._gspread = gspread
        self._book = gspread.service_account_from_dict(account).open_by_url(sheet_url)
        self._sheets: dict = {}

    def _sheet(self, name: str):
        if name not in self._sheets:
            try:
                ws = self._book.worksheet(name)
            except self._gspread.WorksheetNotFound:
                ws = self._book.add_worksheet(name, rows=1000, cols=len(COLUMNS[name]))
            if not ws.row_values(1):
                ws.append_row(COLUMNS[name])
            self._sheets[name] = ws
        return self._sheets[name]

    def write(self, sheet: str, rows: list[list]) -> None:
        self._sheet(sheet).append_rows(rows, value_input_option="USER_ENTERED")


class _Writer:
    """줄을 큐에 모아 뒤 스레드에서 시트로 보낸다. 실패하면 CSV에라도 남긴다."""

    def __init__(self, sink) -> None:
        self.sink = sink
        self.fallback = _CsvSink()
        self.queue: queue.Queue[tuple[str, list]] = queue.Queue()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        while True:
            sheet, row = self.queue.get()
            rows = [row]
            # 밀린 줄이 있으면 같은 시트끼리 묶어 한 번에 보낸다
            pending: list[tuple[str, list]] = []
            while not self.queue.empty():
                pending.append(self.queue.get())
            rows += [r for s, r in pending if s == sheet]
            for s, r in pending:
                if s != sheet:
                    self.queue.put((s, r))
            try:
                self.sink.write(sheet, rows)
            except Exception as e:  # 네트워크·권한 문제여도 기록은 남긴다
                print(f"[beta] {sheet} 시트 쓰기 실패, CSV로 남겨요: {e}", file=sys.stderr)
                self.fallback.write(sheet, rows)


@st.cache_resource(show_spinner=False)
def _writer() -> _Writer:
    sink = _CsvSink()
    try:
        account = dict(st.secrets["gcp_service_account"])
        sheet_url = st.secrets["beta"]["sheet_url"]
    except Exception:
        print("[beta] Google Sheets 설정이 없어 data/beta/logs에 CSV로 남겨요", file=sys.stderr)
    else:
        try:
            sink = _SheetsSink(account, sheet_url)
        except Exception as e:
            print(f"[beta] Google Sheets에 연결하지 못해 CSV로 남겨요: {e}", file=sys.stderr)
    return _Writer(sink)


def storage_name() -> str:
    """지금 기록이 어디로 가는지 (확인용)."""
    return "Google Sheets" if isinstance(_writer().sink, _SheetsSink) else f"CSV ({LOG_DIR})"


def write(sheet: str, *values) -> None:
    """한 줄 남긴다. 첫 칸(시각)은 자동으로 붙인다."""
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    _writer().queue.put((sheet, [now, *values]))
