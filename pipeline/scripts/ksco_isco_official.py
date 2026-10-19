# 국가데이터처 공식 연계표(KSCO 8차 ↔ ISCO-08, 2025.11.03)로 ksco_isco.py를 만든다.
# 소분류 ILO 값 = 소분류 안의 세분류마다 연결된 ISCO 점수를 평균하고(1:N이면 똑같이 나눔), 그 세분류 값들을 다시 평균.
# 결과: I[소분류] = 연결된 ISCO 목록(표시용), IW[소분류] = {ISCO: 가중치}(합 1).
import openpyxl, collections
wb = openpyxl.load_workbook('ksco_isco/KSCO8_ISCO08_20251103.xlsx', read_only=True)
ws = wb['4-1. (연계표) 세분류 연계표(KSCO-ISCO)']
pairs = collections.defaultdict(list)
for i, r in enumerate(ws.iter_rows(values_only=True)):
    if i == 0 or r[0] is None: continue
    k = str(r[0]).strip(); s = str(r[4]).strip().lstrip('*').zfill(4)
    if not k[:1].isdigit(): continue  # 군인(A) 제외
    pairs[k].append(int(s))
by_small = collections.defaultdict(dict)
for k, isos in pairs.items():
    isos = list(dict.fromkeys(isos)); by_small[k[:3]][k] = isos
I, IW = {}, {}
for sm, units in sorted(by_small.items()):
    w = collections.Counter()
    for u, isos in units.items():
        for x in isos: w[x] += 1 / len(isos) / len(units)
    IW[sm] = {x: round(v, 6) for x, v in w.items()}
    I[sm] = sorted(w, key=lambda x: -w[x])
with open('ksco_isco.py', 'w') as f:
    f.write('# 자동 생성: ksco_isco_official.py (국가데이터처 KSCO8-ISCO08 연계표 2025.11.03)\n')
    f.write('I=' + repr(I) + '\nIW=' + repr(IW) + '\n')
print('소분류', len(I), '세분류', len(pairs))
