"""조직 리포트 그림: 직무 군상(사람마다 자기 물 높이) + 조직 물때 막대.
저장소 루트에서: python3 tools/build_lineup.py reports/out/<회사>/metrics.json
그림체는 tools/dither.py(물때 테스트와 같은 글리프 망점). 사람 그림은 pipeline/inputs/illo/figs/<fig>.png.
물 높이: 노출도를 사람 키 비율로 바꾼다(0% → 발 아래, 65% 이상 → 턱). 단계 경계와 같은 눈금이라 그림만 봐도 단계가 읽힌다.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
from dither import render, INK_LIGHT, PAPER

FIG = 'pipeline/inputs/illo/figs/'
FB = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'; FR = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
INK = (22, 22, 26); MUT = (107, 107, 118)
def font(p, s): return ImageFont.truetype(p, s, index=1)
def level(e):            # 노출도 → 물 높이(사람 키 대비). 단계 경계: 20%→무릎(.28) 35%→허리(.47) 50%→가슴(.66) 65%→턱(.86)
    pts = [(0, .03), (.2, .28), (.35, .47), (.5, .66), (.65, .86), (1, .95)]
    for (a, x), (b, y) in zip(pts, pts[1:]):
        if e <= b: return x + (y - x) * (e - a) / (b - a)
    return .95

def panel(fig, e, name, n, e30, stg, w=300):
    m = render(FIG + fig + '.png', cell=5, width=w, level=level(e))
    img = Image.new('RGB', m.size, PAPER); img.paste(Image.new('RGB', m.size, INK_LIGHT), (0, 0), m)
    h = img.height; out = Image.new('RGB', (w, h + 118), PAPER); out.paste(img, (0, 0)); d = ImageDraw.Draw(out)
    d.text((6, h + 10), name, font=font(FB, 22), fill=INK)
    d.text((6, h + 42), f'{round(e*100)}%', font=font(FB, 34), fill=INK_LIGHT)
    d.text((6 + d.textlength(f'{round(e*100)}%', font=font(FB, 34)) + 10, h + 56), f'노출 {stg} · {n}명', font=font(FR, 18), fill=MUT)
    d.text((6, h + 88), f'2030년 {round(e30*100)}%', font=font(FR, 17), fill=MUT)
    return out

TIER = ['낮음', '보통', '상당', '높음', '매우 높음']   # 리포트용 노출 수준(물때 5단계와 같은 경계: 20·35·50·65%)
def lineup(M, per_row=None, w=300, gap=14):
    R = M['roles']; ST = TIER
    import math
    if not per_row: per_row = math.ceil(len(R) / math.ceil(len(R) / 7))   # 줄마다 고르게(외톨이 줄 없게)
    ps = [panel(r['fig'], r['e26'], r['name'], r['n'], r['e30'], ST[r['stage']], w) for r in R]
    rows = [ps[i:i + per_row] for i in range(0, len(ps), per_row)]
    H = sum(max(p.height for p in row) + gap for row in rows) + 40
    W = per_row * (w + gap) + 40
    out = Image.new('RGB', (W, H), PAPER); y = 20
    for row in rows:
        x = 20
        for p in row: out.paste(p, (x, y)); x += w + gap
        y += max(p.height for p in row) + gap
    return out

if __name__ == '__main__':
    M = json.load(open(sys.argv[1])); od = os.path.dirname(sys.argv[1])
    L = lineup(M); L.save(f'{od}/lineup.png', optimize=True); print('lineup', L.size)
