"""편지 읽기 HTML: 펼쳐지는 전환, 손편지 원본 넘겨 보기, 쓴 편지 본문. 스타일은 theme.css의 .kk-read-*.

화면 로직 없이 HTML 문자열만 만든다.
"""

from __future__ import annotations

from html import escape

from components.letter_card import thumbnail_uri
from components.stamp import stamp_html
from models import Letter

PAGE_WIDTH = 1080  # 원본 손글씨가 또렷하게 보이는 너비 (393pt 화면의 레티나 2.7배)


def unfold(inner: str) -> str:
    """카드가 펼쳐지며 나타나는 전환 (360ms)."""
    return f'<div class="kk-unfold">{inner}</div>'


# 손편지 사진을 옆으로 밀어 다음/이전 장을 본다 (터치 스와이프, PC는 마우스로 끌기).
# 손편지 사진(.kk-read-pages) 위에서만 동작한다. 손가락으로 이미 장이 넘어갔으면 그대로 두고,
# 마우스로 끈 경우처럼 스크롤이 안 움직였으면 한 장 넘긴다. 더 넘길 장이 없으면 살짝 튕긴다.
# 문서에 한 번만 붙이고(event delegation), 다시 그려져도 중복으로 붙지 않는다.
SWIPE_SCRIPT = """<script>
(function () {
  if (window.__kkPageSwipe) return;
  window.__kkPageSwipe = true;
  const MIN = 50;  // 이만큼(px) 가로로 밀어야 넘긴다
  let start = null;

  const begin = (x, y, target) => {
    const pages = target.closest && target.closest('.kk-read-pages');
    start = pages ? { x, y, pages, scroll: pages.scrollLeft } : null;
  };

  const end = (x, y) => {
    if (!start) return;
    const { pages, scroll } = start;
    const dx = x - start.x, dy = y - start.y;
    start = null;
    if (Math.abs(dx) < MIN || Math.abs(dx) < Math.abs(dy) * 1.5) return;
    if (Math.abs(pages.scrollLeft - scroll) > 4) return;  // 손가락으로 이미 장을 넘겼다
    const dir = dx < 0 ? 1 : -1;  // 왼쪽으로 밀면 다음 장
    const max = pages.scrollWidth - pages.clientWidth;
    const canMove = dir > 0 ? pages.scrollLeft < max - 4 : pages.scrollLeft > 4;
    if (canMove) {
      const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      pages.scrollBy({ left: dir * pages.clientWidth, behavior: reduce ? 'auto' : 'smooth' });
      return;
    }
    pages.classList.remove('kk-swipe-edge');  // 첫·마지막 장: 살짝 튕겨서 끝임을 알린다
    void pages.offsetWidth;
    pages.classList.add('kk-swipe-edge');
  };

  document.addEventListener('touchstart', (e) => {
    const t = e.touches[0];
    if (e.touches.length === 1) begin(t.clientX, t.clientY, e.target); else start = null;
  }, { passive: true });
  document.addEventListener('touchend', (e) => {
    const t = e.changedTouches[0];
    end(t.clientX, t.clientY);
  }, { passive: true });
  document.addEventListener('mousedown', (e) => {
    if (e.button === 0) begin(e.clientX, e.clientY, e.target);
  });
  document.addEventListener('mouseup', (e) => end(e.clientX, e.clientY));
})();
</script>"""


def scroll_to_top(letter_id: int) -> str:
    """목록에서 다른 편지를 고르면 화면 맨 위(펼쳐진 편지)로 올린다. 같은 편지를 다시 그릴 때는 그대로 둔다."""
    return f"""<script>
(function () {{
  if (window.__kkReading === {letter_id}) return;
  window.__kkReading = {letter_id};
  const main = document.querySelector('[data-testid="stMain"]');
  if (main) main.scrollTo({{ top: 0 }});
  window.scrollTo(0, 0);
}})();
</script>"""


def handwritten_pages(letter: Letter) -> str:
    """손편지 원본 사진. 여러 장이면 옆으로 넘겨 본다 (가로 스크롤 캐러셀)."""
    total = len(letter.images)
    slides = []
    for i, path in enumerate(letter.images, start=1):
        uri = thumbnail_uri(path, PAGE_WIDTH)
        img = f'<img src="{uri}" alt="손편지 {i}번째 장">' if uri else '<span class="kk-read-missing">사진을 찾을 수 없어요</span>'
        count = f'<figcaption class="kk-read-count">{i} / {total}</figcaption>' if total > 1 else ""
        slides.append(f'<figure class="kk-read-page">{img}{count}</figure>')
    hint = '<p class="kk-hint kk-hint--center">옆으로 넘겨 다음 장을 보세요</p>' if total > 1 else ""
    return f'<div class="kk-read-pages">{"".join(slides)}</div>{hint}'


def written_letter(letter: Letter, to_name: str, from_name: str) -> str:
    """앱에서 쓴 편지: 종이 + 우표 + To./본문/From."""
    return (
        '<article class="kk-read-paper">'
        '<i class="kk-fold"></i>'
        f"{stamp_html(letter.stamp)}"
        f'<p class="kk-read-to">To. {escape(to_name)}</p>'
        f'<p class="kk-read-body">{escape(letter.body)}</p>'
        f'<p class="kk-read-from">From. {escape(from_name)}</p>'
        "</article>"
    )
