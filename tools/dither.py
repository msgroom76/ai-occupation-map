"""AI 점령 지도 일러스트 필터: 흑백 바탕 그림 + 한 가지 색으로 칠한 물 → 한 가지 잉크의 글리프 망점 그림.
기준 그림체(2026-10-22): 사람·사물은 점·십자·X 글리프, 물은 세로 막대 글리프. 잉크 한 색, 배경은 투명 또는 종이색.

사용: python3 tools/dither.py <입력.png> <출력 접두어> [--cell 9] [--w 1080] [--level 0.47]
  --level을 주면 입력의 물 대신 사람 키 대비 그 높이로 물을 그린다(발목 .06 · 무릎 .28 · 허리 .47 · 가슴 .66 · 턱 .86)
  → <접두어>-light.png (진한 분홍 잉크, 밝은 화면·메일용), <접두어>-dark.png (밝은 분홍 잉크, 어두운 화면용) — 둘 다 배경 투명
     <접두어>-mail.png (흰 종이 위 진한 잉크, 메일·공유 이미지용)
입력 그림 약속: 물은 채도 높은 마젠타(#FF00AA 근처) 한 색, 나머지는 흑백.
"""
import sys, argparse
from PIL import Image, ImageDraw
import numpy as np

INK_LIGHT = (138, 8, 90)     # #8a085a  사이트 밝은 테마 분홍
INK_DARK = (255, 140, 205)   # #ff8ccd  사이트 어두운 테마 분홍
PAPER = (246, 246, 248)      # #f6f6f8

def glyph(d, x, y, c, level, kind):
    """칸 하나(c×c)에 어두움 level(0~1)만큼 글리프를 그린다. kind: 'obj'(점·십자·X), 'water'(세로 막대)"""
    if level < 0.06: return
    m = c / 2
    if kind == 'water':
        # 세로 막대: 어두울수록 길고 두껍게. 위아래로 살짝 끊어 결을 만든다
        h = max(1, round(c * (0.25 + 0.75 * level)))
        w = max(1, round(c * (0.2 + 0.45 * level)))
        x0 = x + (c - w) / 2; y0 = y + (c - h) / 2
        d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=1)
        return
    if level < 0.22:          # 작은 점
        r = max(1, c * 0.12)
        d.rectangle([x + m - r, y + m - r, x + m + r - 1, y + m + r - 1], fill=1)
    elif level < 0.45:        # 십자
        t = max(1, round(c * 0.16)); a = c * 0.36
        d.rectangle([x + m - a, y + m - t / 2, x + m + a - 1, y + m + t / 2 - 1], fill=1)
        d.rectangle([x + m - t / 2, y + m - a, x + m + t / 2 - 1, y + m + a - 1], fill=1)
    elif level < 0.86:        # X
        t = max(1, round(c * 0.2)); a = c * 0.38
        d.line([x + m - a, y + m - a, x + m + a, y + m + a], fill=1, width=t)
        d.line([x + m - a, y + m + a, x + m + a, y + m - a], fill=1, width=t)
    else:                     # 거의 꽉 찬 네모(살짝 틈, 아주 진한 곳만)
        g = max(1, round(c * 0.12))
        d.rectangle([x + g / 2, y + g / 2, x + c - g / 2 - 1, y + c - g / 2 - 1], fill=1)

def render(src, cell=9, width=1080, seed=7, level=None):
    """level: 물 높이(사람 키 대비, 발=0 · 머리 꼭대기=1). 주면 그림의 물 대신 코드로 물을 그린다(사람이 물에 잠긴 모습)."""
    im = Image.open(src).convert('RGB')
    h = round(im.height * width / im.width)
    im = im.resize((width, h), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    water = (sat > 0.35) & (r > 0.45) & (b > 0.25) & (g < r * 0.75)       # 마젠타 물
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if level is not None:
        fig = lum < 0.88
        rows = np.where(fig[:, int(width * .15):int(width * .85)].any(1))[0]
        head, feet = (rows.min(), rows.max()) if len(rows) else (0, h)
        yw = feet - level * (feet - head)
        xs = np.arange(width)
        surf = yw + np.sin(xs / width * 2 * np.pi * 3) * cell * 0.6       # 잔물결 수면
        water = np.arange(h)[:, None] >= surf[None, :]
    gy, gx = np.gradient(lum)
    edge = np.hypot(gx, gy) * 3
    edge = np.where(lum > 0.97, 0, edge) if level is None else edge
    rng = np.random.default_rng(seed)
    mask = Image.new('1', (width, h), 0); d = ImageDraw.Draw(mask)
    for y in range(0, h - cell + 1, cell):
        for x in range(0, width - cell + 1, cell):
            wv = water[y:y + cell, x:x + cell].mean()
            if wv > 0.5:
                # 물: 수면 가까이는 성기게, 아래로 갈수록 빽빽하게(깊이감) + 약간의 흔들림.
                # 물속에 잠긴 사람·사물은 더 굵은 막대로 비쳐 보이게 한다
                top = np.argmax(water[:, x + cell // 2]) if water[:, x + cell // 2].any() else y
                depth = min(1, (y - top) / (h * 0.35 + 1))
                body = 1 - lum[y:y + cell, x:x + cell].mean() if level is not None else 0
                lv = 0.22 + 0.42 * depth + 0.55 * body + rng.normal(0, 0.1)
                if rng.random() < 0.06: lv = 0       # 군데군데 빈칸(물결)
                glyph(d, x, y, cell, max(0, min(1, lv)), 'water')
            else:
                lv = 1 - lum[y:y + cell, x:x + cell].mean()
                ed = edge[y:y + cell, x:x + cell].max()
                # 어두운 곳은 X까지만(꽉 찬 네모는 아주 진한 곳만), 밝은 사물은 윤곽선으로 살린다
                lv = (max(0, lv - 0.04) / 0.92) ** 0.9 * 0.82 + min(0.45, ed * 1.6)
                lv = 0 if lv < 0.06 else max(0, min(1, lv + rng.normal(0, 0.04)))   # 빈 바탕에는 잡티를 만들지 않는다
                glyph(d, x, y, cell, lv, 'obj')
    return mask

def save(mask, ink, path, paper=None):
    w, h = mask.size
    out = Image.new('RGBA', (w, h), (*paper, 255) if paper else (0, 0, 0, 0))
    layer = Image.new('RGBA', (w, h), (*ink, 255))
    out.paste(layer, (0, 0), mask)
    if paper: out = out.convert('RGB')
    out.save(path, optimize=True)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('out')
    ap.add_argument('--cell', type=int, default=9); ap.add_argument('--level', type=float, default=None); ap.add_argument('--w', type=int, default=1080)
    o = ap.parse_args()
    m = render(o.src, o.cell, o.w, level=o.level)
    save(m, INK_LIGHT, o.out + '-light.png'); save(m, INK_DARK, o.out + '-dark.png'); save(m, INK_LIGHT, o.out + '-mail.png', PAPER)
    print('ok', o.out, m.size)
