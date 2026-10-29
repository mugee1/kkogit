"""테스트용 샘플 데이터. data/app.db가 비어 있을 때 db.init_db()가 한 번 실행한다.

다시 넣고 싶으면 data/ 폴더를 지우고 앱을 재실행한다.
"""

from __future__ import annotations

import math
import random
from datetime import date

from PIL import Image, ImageDraw

import db

PAPER = (245, 243, 237)  # Paper White
INK = (36, 36, 36)       # Soft Black


def _blend(alpha: float) -> tuple[int, int, int]:
    """Paper White 위에 Soft Black을 alpha만큼 겹친 색."""
    return tuple(round(p + (i - p) * alpha) for p, i in zip(PAPER, INK))


def make_placeholder_letter(name: str, seed: int) -> str:
    """손글씨처럼 보이는 자리표시용 편지 이미지(1:1.41)를 만들고 상대 경로를 돌려준다."""
    rng = random.Random(seed)
    w, h = 600, 846
    img = Image.new("RGB", (w, h), PAPER)
    draw = ImageDraw.Draw(img)

    # 줄 노트
    for y in range(120, h - 60, 44):
        draw.line([(48, y), (w - 48, y)], fill=_blend(0.12), width=1)

    # 줄마다 구불구불한 '글씨' 획
    ink = _blend(0.8)
    for row, y in enumerate(range(112, h - 100, 44)):
        x = 56 + (40 if row == 0 else 0)
        end = w - 56 - (rng.randint(80, 260) if rng.random() < 0.25 else rng.randint(0, 40))
        while x < end:
            word = rng.randint(28, 70)
            pts = [
                (x + t, y - 10 + 7 * math.sin(t / rng.uniform(3, 6)) + rng.uniform(-2, 2))
                for t in range(0, word, 2)
            ]
            draw.line(pts, fill=ink, width=2, joint="curve")
            x += word + rng.randint(10, 18)

    rel_path = f"sample/{name}.jpg"
    out = db.IMAGE_DIR / rel_path
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=85)
    return rel_path


def seed_sample_data() -> None:
    haeun = db.create_user("하은")
    jimin = db.create_user("지민")

    # 하은의 서랍
    h_jimin = db.create_relation(haeun, "지민", "lover", partner_user_id=jimin)
    h_seoyeon = db.create_relation(haeun, "서연", "friend")
    h_doyun = db.create_relation(haeun, "도윤", "friend")
    # 지민의 서랍
    j_haeun = db.create_relation(jimin, "하은", "lover", partner_user_id=haeun)

    # 하은이 보관한 손편지
    db.create_letter(
        h_jimin, "handwritten", receiver_user_id=haeun,
        images=[make_placeholder_letter("jimin_2024_1", 1), make_placeholder_letter("jimin_2024_2", 2)],
        written_at=date(2024, 10, 29),
    )
    db.create_letter(
        h_seoyeon, "handwritten", receiver_user_id=haeun,
        images=[make_placeholder_letter("seoyeon_2023", 3)],
        written_at=date(2023, 3, 14),
    )
    db.create_letter(
        h_seoyeon, "handwritten", receiver_user_id=haeun,
        images=[make_placeholder_letter("seoyeon_2025", 4)],
        written_at=date(2025, 10, 29),
    )
    db.create_letter(
        h_doyun, "handwritten", receiver_user_id=haeun,
        images=[make_placeholder_letter("doyun_2025", 5)],
        written_at=date(2025, 12, 24),
    )

    # 하은 ↔ 지민 주고받은 편지
    db.create_letter(
        j_haeun, "written", sender_user_id=jimin, receiver_user_id=haeun,
        body="하은아, 오랜만에 편지 써. 그때 준 편지 아직 책상 서랍에 있어.\n"
             "이번엔 내가 먼저 답장할게.",
        stamp="default", written_at=date(2026, 5, 2), status="read",
    )
    db.create_letter(
        h_jimin, "written", sender_user_id=haeun, receiver_user_id=jimin,
        body="편지 고마워. 짧은데 몇 번이나 다시 읽었어.\n다음 주에 만나면 직접 말해 줄게.",
        stamp="default", written_at=date(2026, 5, 10), status="read",
    )
    db.create_letter(
        j_haeun, "written", sender_user_id=jimin, receiver_user_id=haeun,
        body="날이 많이 추워졌어. 따뜻하게 입고 다녀.\n주말에 보자.",
        stamp="default", written_at=date(2026, 10, 27), status="sent",
    )
