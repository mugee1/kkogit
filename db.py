"""SQLite 연결과 쿼리."""

from __future__ import annotations

import io
import json
import random
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from models import COVER_DESIGN_PREFIX, BundleSummary, Letter, LetterInDrawer, Relation, User

DATA_DIR = Path(__file__).parent / "data"
IMAGE_DIR = DATA_DIR / "images"
DB_PATH = DATA_DIR / "app.db"

register_heif_opener()  # iPhone 사진(HEIC)을 Pillow로 열 수 있게 한다

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname    TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS relations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    partner_name     TEXT NOT NULL,
    partner_user_id  INTEGER REFERENCES users(id),
    type             TEXT NOT NULL CHECK (type IN ('friend', 'lover')),
    created_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS letters (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    relation_id       INTEGER NOT NULL REFERENCES relations(id),
    sender_user_id    INTEGER REFERENCES users(id),
    receiver_user_id  INTEGER REFERENCES users(id),
    kind              TEXT NOT NULL CHECK (kind IN ('handwritten', 'written')),
    images            TEXT NOT NULL DEFAULT '[]',
    body              TEXT NOT NULL DEFAULT '',
    stamp             TEXT,
    written_at        TEXT,
    status            TEXT NOT NULL CHECK (status IN ('draft', 'sent', 'read')),
    created_at        TEXT NOT NULL,
    cover             TEXT
);

CREATE INDEX IF NOT EXISTS idx_letters_relation ON letters(relation_id);
CREATE INDEX IF NOT EXISTS idx_letters_receiver ON letters(receiver_user_id, status);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """요청마다 연결을 열고 닫는다. (Streamlit은 실행마다 스레드가 다를 수 있다)"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """테이블을 만들고, 비어 있으면 샘플 데이터를 넣는다."""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        # 표지 기능 이전에 만든 DB에는 cover 열이 없다
        columns = {r["name"] for r in conn.execute("PRAGMA table_info(letters)")}
        if "cover" not in columns:
            conn.execute("ALTER TABLE letters ADD COLUMN cover TEXT")
        empty = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    if empty:
        from seed import seed_sample_data

        seed_sample_data()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------- 행 → 모델 변환 ----------

def _to_user(row: sqlite3.Row) -> User:
    return User(row["id"], row["nickname"], datetime.fromisoformat(row["created_at"]))


def _to_relation(row: sqlite3.Row) -> Relation:
    return Relation(
        id=row["id"],
        user_id=row["user_id"],
        partner_name=row["partner_name"],
        partner_user_id=row["partner_user_id"],
        type=row["type"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _to_letter(row: sqlite3.Row) -> Letter:
    return Letter(
        id=row["id"],
        relation_id=row["relation_id"],
        sender_user_id=row["sender_user_id"],
        receiver_user_id=row["receiver_user_id"],
        kind=row["kind"],
        images=json.loads(row["images"]),
        body=row["body"],
        stamp=row["stamp"],
        written_at=date.fromisoformat(row["written_at"]) if row["written_at"] else None,
        status=row["status"],
        created_at=datetime.fromisoformat(row["created_at"]),
        cover=row["cover"],
    )


# ---------- 생성 ----------

def create_user(nickname: str) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (nickname, created_at) VALUES (?, ?)", (nickname, _now())
        )
        return cur.lastrowid


def create_relation(
    user_id: int, partner_name: str, type: str, partner_user_id: int | None = None
) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO relations (user_id, partner_name, partner_user_id, type, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, partner_name, partner_user_id, type, _now()),
        )
        return cur.lastrowid


def create_letter(
    relation_id: int,
    kind: str,
    *,
    sender_user_id: int | None = None,
    receiver_user_id: int | None = None,
    images: list[str] | None = None,
    body: str = "",
    stamp: str | None = None,
    written_at: date | None = None,
    status: str = "read",
    cover: str | None = None,
) -> int:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO letters (relation_id, sender_user_id, receiver_user_id, kind,"
            " images, body, stamp, written_at, status, created_at, cover)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                relation_id,
                sender_user_id,
                receiver_user_id,
                kind,
                json.dumps(images or [], ensure_ascii=False),
                body,
                stamp,
                written_at.isoformat() if written_at else None,
                status,
                _now(),
                cover,
            ),
        )
        return cur.lastrowid


# ---------- 손편지 보관 ----------

PHOTO_MAX_SIDE = 2400  # 원본 손글씨가 읽힐 만큼만 남기고 줄인다


def prepare_photo(data: bytes) -> bytes:
    """올린 사진을 보관용 JPEG로 바꾼다. HEIC도 JPEG로, iPhone 사진의 회전 정보도 반영한다."""
    with Image.open(io.BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((PHOTO_MAX_SIDE, PHOTO_MAX_SIDE))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def keep_handwritten(
    user_id: int,
    photos: list[bytes],
    received_at: date,
    *,
    relation_id: int | None = None,
    partner_name: str = "",
    relation_type: str | None = None,
    cover_design: int | None = None,
    cover_page: int = 0,
) -> tuple[int, int]:
    """손편지를 서랍에 보관한다. 기존 관계(relation_id)가 없으면 새 관계를 만든다.

    photos는 prepare_photo()를 거친 JPEG. 표지는 꼬깃 표지(cover_design 1~5)이거나,
    없으면 photos[cover_page] 사진. 반환값은 (letter_id, relation_id).
    """
    if not photos:
        raise ValueError("사진이 한 장 이상 있어야 해요")
    if relation_id is None:
        relation_id = create_relation(user_id, partner_name.strip(), relation_type)

    folder = f"u{user_id}"
    (IMAGE_DIR / folder).mkdir(parents=True, exist_ok=True)
    stem = f"{datetime.now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:6]}"
    images = []
    for i, data in enumerate(photos, start=1):
        rel_path = f"{folder}/{stem}_{i}.jpg"
        (IMAGE_DIR / rel_path).write_bytes(data)
        images.append(rel_path)

    letter_id = create_letter(
        relation_id,
        "handwritten",
        receiver_user_id=user_id,
        images=images,
        written_at=received_at,
        status="read",
        cover=f"{COVER_DESIGN_PREFIX}{cover_design}" if cover_design else images[cover_page],
    )
    return letter_id, relation_id


# ---------- 답장 보내기 ----------

def send_letter(
    user_id: int, relation: Relation, body: str, stamp: str, written_at: date
) -> int:
    """편지를 보낸다. 상대가 앱 사용자면 상대 서랍에 '도착한 편지'(status=sent)로 들어간다.

    상대 쪽에 나를 가리키는 관계가 없으면 만들어 준다(그래야 상대 서랍에 묶음이 생긴다).
    상대가 앱 사용자가 아니면 receiver_user_id 없이 내 묶음에만 쌓인다.
    """
    partner_id = relation.partner_user_id
    if partner_id is not None and not any(
        r.partner_user_id == user_id for r in list_relations(partner_id)
    ):
        create_relation(partner_id, get_user(user_id).nickname, relation.type, user_id)
    return create_letter(
        relation.id,
        "written",
        sender_user_id=user_id,
        receiver_user_id=partner_id,
        body=body.strip(),
        stamp=stamp,
        written_at=written_at,
        status="sent",
    )


# ---------- 조회 ----------

def list_users() -> list[User]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    return [_to_user(r) for r in rows]


def get_user(user_id: int) -> User | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _to_user(row) if row else None


def list_relations(user_id: int) -> list[Relation]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM relations WHERE user_id = ? ORDER BY id", (user_id,)
        ).fetchall()
    return [_to_relation(r) for r in rows]


def list_bundle_letters(user_id: int, relation: Relation) -> list[Letter]:
    """사람별 편지 묶음: 내가 보관한 손편지 + 그 사람과 주고받은 편지를 시간순으로.

    임시 저장(draft)은 보낸 사람에게만 보인다.
    상대가 앱 사용자가 아니면, 내가 이 묶음에서 쓴 편지(receiver 없음)도 함께 보인다.
    """
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM letters
            WHERE (kind = 'handwritten' AND relation_id = :rid)
               OR (kind = 'written' AND :pid IS NOT NULL AND (
                     (sender_user_id = :uid AND receiver_user_id = :pid)
                  OR (sender_user_id = :pid AND receiver_user_id = :uid AND status != 'draft')
               ))
               OR (kind = 'written' AND :pid IS NULL AND relation_id = :rid
                   AND sender_user_id = :uid AND receiver_user_id IS NULL)
            ORDER BY written_at, id
            """,
            {"rid": relation.id, "uid": user_id, "pid": relation.partner_user_id},
        ).fetchall()
    return [_to_letter(r) for r in rows]


def get_relation(relation_id: int) -> Relation | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM relations WHERE id = ?", (relation_id,)).fetchone()
    return _to_relation(row) if row else None


def get_letter(letter_id: int) -> Letter | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM letters WHERE id = ?", (letter_id,)).fetchone()
    return _to_letter(row) if row else None


def _is_unread(user_id: int, letter: Letter) -> bool:
    return letter.kind == "written" and letter.receiver_user_id == user_id and letter.status == "sent"


def is_unread(user_id: int, letter: Letter) -> bool:
    """도착했지만 아직 펼쳐 보지 않은 편지인가."""
    return _is_unread(user_id, letter)


def _is_received(user_id: int, letter: Letter) -> bool:
    """내가 받은 편지인가 (보관한 손편지 포함)."""
    return letter.kind == "handwritten" or letter.receiver_user_id == user_id


def list_timeline(user_id: int, relation: Relation) -> list[Letter]:
    """편지 묶음 화면에 보일 편지: 손편지와 주고받은 편지를 시간순으로. (임시 저장 제외)"""
    return [l for l in list_bundle_letters(user_id, relation) if l.status != "draft"]


def relation_for_letter(user_id: int, letter: Letter) -> Relation | None:
    """이 편지가 내 서랍의 어느 묶음에 속하는지. 내가 볼 수 없는 편지면 None.

    받은 쓴 편지의 relation_id는 보낸 사람 쪽 관계라, 상대 사용자로 내 관계를 찾는다.
    """
    if letter.kind == "handwritten" or (letter.sender_user_id == user_id and letter.receiver_user_id is None):
        # 손편지, 또는 앱 사용자가 아닌 사람에게 쓴 편지: relation_id가 곧 내 관계
        relation = get_relation(letter.relation_id)
        return relation if relation and relation.user_id == user_id else None
    if letter.sender_user_id == user_id:
        partner = letter.receiver_user_id
    elif letter.receiver_user_id == user_id and letter.status != "draft":
        partner = letter.sender_user_id
    else:
        return None
    return next((r for r in list_relations(user_id) if r.partner_user_id == partner), None)


def mark_read(user_id: int, letter_id: int) -> bool:
    """받은 편지를 펼쳐 읽으면 읽음으로 바꾼다. 바뀌었으면 True."""
    with connect() as conn:
        cur = conn.execute(
            "UPDATE letters SET status = 'read'"
            " WHERE id = ? AND receiver_user_id = ? AND kind = 'written' AND status = 'sent'",
            (letter_id, user_id),
        )
        return cur.rowcount > 0


def _letters_in_drawer(user_id: int) -> list[LetterInDrawer]:
    """내 모든 묶음의 편지를 나의 관계와 함께 펼친다. (임시 저장 제외)"""
    return [
        LetterInDrawer(letter, relation)
        for relation in list_relations(user_id)
        for letter in list_bundle_letters(user_id, relation)
        if letter.status != "draft"
    ]


def list_bundles(user_id: int) -> list[BundleSummary]:
    """서랍의 사람별 편지 묶음. 최근에 편지가 오간 순서."""
    summaries = []
    for relation in list_relations(user_id):
        letters = [l for l in list_bundle_letters(user_id, relation) if l.status != "draft"]
        dates = [l.written_at for l in letters if l.written_at]
        handwritten = [l for l in letters if l.kind == "handwritten"]
        summaries.append(
            BundleSummary(
                relation=relation,
                letter_count=len(letters),
                last_written_at=max(dates) if dates else None,
                unread_count=sum(_is_unread(user_id, l) for l in letters),
                cover_image=handwritten[-1].cover_image if handwritten else None,
                cover_design=handwritten[-1].cover_design if handwritten else None,
            )
        )
    return sorted(
        summaries,
        key=lambda s: s.last_written_at or s.relation.created_at.date(),
        reverse=True,
    )


def list_arrived(user_id: int) -> list[LetterInDrawer]:
    """도착했지만 아직 펼쳐 보지 않은 편지. 최근 것부터."""
    arrived = [x for x in _letters_in_drawer(user_id) if _is_unread(user_id, x.letter)]
    return sorted(arrived, key=lambda x: (x.letter.written_at, x.letter.id), reverse=True)


def pick_today_letters(user_id: int, on: date, k: int = 3) -> list[LetterInDrawer]:
    """'오늘 다시 펼쳐 볼 편지': 이미 읽은 받은 편지 중에서 날짜마다 다르게 k통을 고른다.

    같은 사용자·같은 날짜면 항상 같은 편지가 나온다(데모 날짜로 시연 가능).
    """
    candidates = [
        x for x in _letters_in_drawer(user_id)
        if _is_received(user_id, x.letter)
        and not _is_unread(user_id, x.letter)
        and x.letter.written_at
        and x.letter.written_at <= on
    ]
    rng = random.Random(f"{user_id}:{on.isoformat()}")
    return rng.sample(candidates, min(k, len(candidates)))


def count_kept_letters(user_id: int) -> int:
    """내 서랍에 있는 편지 수 (보관한 손편지 + 받은 편지 + 보낸 편지)."""
    with connect() as conn:
        return conn.execute(
            """
            SELECT COUNT(*) FROM letters
            WHERE (kind = 'handwritten' AND receiver_user_id = :uid)
               OR (kind = 'written' AND sender_user_id = :uid AND status != 'draft')
               OR (kind = 'written' AND receiver_user_id = :uid AND status != 'draft')
            """,
            {"uid": user_id},
        ).fetchone()[0]
