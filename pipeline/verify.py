# pipeline/out 결과를 저장소의 실제 파일과 비교한다. 사용: python3 pipeline/verify.py [출력 폴더]
# JSON은 키 순서를 무시하고 값만 비교한다(원래 실행은 파이썬 문자열 해시가 매번 달라 dict 키 순서가 실행마다 달랐다).
# PNG는 픽셀을 비교한다.
import json, os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'out')
ok = True
for f in ['city_meta.json', 'ksco_titles.json', 'ksco_soc_map.json']:
    a, b = json.load(open(os.path.join(OUT, f))), json.load(open(os.path.join(REPO, f)))
    same = json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    byte = open(os.path.join(OUT, f), 'rb').read() == open(os.path.join(REPO, f), 'rb').read()
    print(f'{f:20s} 값 {"같음" if same else "다름"} · 바이트 {"같음" if byte else "다름(키 순서)"}'); ok &= same
for f in ['city_index.png', 'city_roads.png']:
    x, y = np.array(Image.open(os.path.join(OUT, f))), np.array(Image.open(os.path.join(REPO, f)))
    d = x.shape == y.shape and not (x != y).any()
    print(f'{f:20s} 픽셀 {"같음" if d else "다름"}'); ok &= d
sys.exit(0 if ok else 1)
