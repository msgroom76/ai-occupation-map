"""세부 작업(O*NET DWA) 찾기 — 소식 갱신 작업이 소식에 dwa를 붙일 때 쓴다. 표준 라이브러리만 쓴다.
사용: python3 tools/find_dwa.py 프로토타입 디자인          (한국어·영어 낱말 여러 개, 모두 들어간 것)
      python3 tools/find_dwa.py --job 2955                  (그 직업이 하는 세부 작업 목록: 세분류 4자리·소분류 3자리·중분류 2자리)
      python3 tools/find_dwa.py --id 4.A.3.b.1.I02.D01      (한 작업의 이름)
결과 한 줄: DWA ID · 한국어 · 영어 · 이 작업을 하는 직업 수"""
import json, sys, csv, collections, os
T = json.load(open('tasks.json'))
EN = {}
ref = 'pipeline/inputs/dl_onet/db_text/DWA Reference.txt'
if os.path.exists(ref):
    for r in csv.DictReader(open(ref, encoding='utf-8'), delimiter='\t'): EN[r['DWA ID']] = r['DWA Title']
use = collections.Counter()
for k in ('sm', 'mid'):
    for c, l in T[k].items():
        for d, w in l: use[d] += 1
for o, (nm, l) in T['occ'].items():
    for d, w in l: use[d] += 1
def show(d): print(f"{d} · {T['dwa'].get(d, '?')} · {EN.get(d, '')} · 직업 {use[d]}곳")
a = sys.argv[1:]
if not a: print(__doc__); sys.exit()
if a[0] == '--id':
    for d in a[1:]: show(d)
elif a[0] == '--job':
    c = a[1]
    if len(c) == 4 and c in T['ks']:
        for o, s in T['ks'][c]:
            print(f"[세부 직무] {T['occ'][o][0]} ({o}) 몫 {s:.0%}")
            for d, w in T['occ'][o][1]: print('   ', f'{w:.0%}', end=' '); show(d)
    else:
        for d, w in (T['sm'].get(c) or T['mid'].get(c) or []): print(f'{w:.0%}', end=' '); show(d)
else:
    q = [x.lower() for x in a]
    n = 0
    for d, ko in T['dwa'].items():
        s = (ko + ' ' + EN.get(d, '')).lower()
        if all(x in s for x in q): show(d); n += 1
    if not n: print('없음 — 더 짧은 낱말이나 영어로 다시 찾아보세요.')
