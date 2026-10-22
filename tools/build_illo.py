"""'물때' 일러스트와 공유 이미지를 만든다. 저장소 루트에서: python3 tools/build_illo.py
바탕 그림(pipeline/inputs/illo/, AI로 만든 흑백 사진풍 그림)에 tools/dither.py 필터를 입혀 기준 그림체로 바꾼다.
물 높이는 코드가 정한다(사람 키 대비, 발=0 · 머리=1). 그림체를 바꾸려면 dither.py만 고치고 이 파일을 다시 돌리면 된다.

결과(img/water/):
  s1~s5-light.png · s1~s5-dark.png   단계별 한 사람 그림(배경 투명, 밝은/어두운 화면)
  crowd-s1~s5-light/dark.png          다섯 직업이 함께 선 그림(페이지 머리)
  crowd-s1~s5-mail.png                같은 그림, 종이색 바탕(주간 메일 머리, 그 주 전체 물때에 맞춰 고름)
  og-test.png · og-s1~s5.png          공유 이미지(1200×630)
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
from dither import render, save, INK_LIGHT, INK_DARK, PAPER

# 단계: (이름, 노출도 하한, 물 높이)
STAGES = [('발목', 0.0, 0.08), ('무릎', 0.20, 0.28), ('허리', 0.35, 0.47), ('가슴', 0.50, 0.66), ('목까지', 0.65, 0.86)]
SRC = 'pipeline/inputs/illo/'
OUT = 'img/water/'
os.makedirs(OUT, exist_ok=True)
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
FONT_R = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'

def font(path, size):
    try: return ImageFont.truetype(path, size, index=1)   # 1 = KR
    except Exception: return ImageFont.truetype(path, size)

def paper(mask, ink=INK_LIGHT):
    out = Image.new('RGB', mask.size, PAPER); out.paste(Image.new('RGB', mask.size, ink), (0, 0), mask); return out

for n, (name, lo, lv) in enumerate(STAGES, 1):
    m = render(SRC + 'figure.png', cell=6, width=720, level=lv)
    save(m, INK_LIGHT, f'{OUT}s{n}-light.png'); save(m, INK_DARK, f'{OUT}s{n}-dark.png')
    c = render(SRC + 'crowd.png', cell=8, width=1200, level=lv)
    save(c, INK_LIGHT, f'{OUT}crowd-s{n}-light.png'); save(c, INK_DARK, f'{OUT}crowd-s{n}-dark.png')
    save(c, INK_LIGHT, f'{OUT}crowd-s{n}-mail.png', PAPER)
    # 공유 이미지: 왼쪽 그림, 오른쪽 글
    big = render(SRC + 'figure.png', cell=7, width=504, level=lv)
    og = Image.new('RGB', (1200, 630), PAPER); fig = paper(big).crop((0, 0, 504, 630))
    og.paste(fig, (40, 0)); d = ImageDraw.Draw(og)
    d.text((600, 120), '내 직업은 언제 소멸될까?', font=font(FONT_R, 36), fill=(22, 22, 26))
    d.text((600, 200), f'물때 {n}단계', font=font(FONT, 40), fill=INK_LIGHT)
    d.text((596, 252), name, font=font(FONT, 150), fill=INK_LIGHT)
    d.text((600, 470), '사라지는 날이 아니라, 차오르는 높이를 재요.', font=font(FONT_R, 28), fill=(107, 107, 118))
    d.text((600, 530), 'aijido.org/test', font=font(FONT, 28), fill=(22, 22, 26))
    og.save(f'{OUT}og-s{n}.png', optimize=True)

# 테스트 첫 화면 공유 이미지: 다섯 직업이 함께 선 그림(무릎) + 제목
c = render(SRC + 'crowd.png', cell=8, width=1200, level=0.28)
og = Image.new('RGB', (1200, 630), PAPER); og.paste(paper(c).crop((0, 0, 1200, 515)).resize((1200, 515)), (0, 115))
d = ImageDraw.Draw(og)
d.text((48, 34), '내 직업은 언제 소멸될까?', font=font(FONT, 56), fill=(22, 22, 26))
d.text((900, 52), 'aijido.org/test', font=font(FONT, 26), fill=INK_LIGHT)
og.save(f'{OUT}og-test.png', optimize=True)
print('ok', sorted(os.listdir(OUT)))
