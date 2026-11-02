"""'내 직업 전망'(/test) 결과의 근거 자료를 작게 묶는다 → evidence.json
직업(소분류 3자리·중분류 2자리)마다:
  d  : 이 직업이 가장 많이 하는 세부 작업(O*NET DWA) 상위 8개 [한국어 이름, 41개 업무 중 어디에 속하는지(R id), 비중]
  us : 업무 구성을 가져온 미국 직업(O*NET) 한국어 이름 최대 8개, n: 전체 개수
쓰는 자료: tasks.json(세부 작업·미국 직업 이름), ksco_soc_map.json(한국 직업 ↔ 미국 SOC), city_meta.json(업무 id 순서)
사용: python3 tools/build_evidence.py"""
import json
T = json.load(open('tasks.json'))
K = json.load(open('ksco_soc_map.json'))
CM = json.load(open('city_meta.json'))
# 41개 업무(GWA)의 O*NET 요소 번호(4.A.x.y.z)를 정렬하면 city_meta의 업무 id(A1…D17) 순서와 같다(Work Activities.txt로 확인)
order = sorted(CM['RN'], key=lambda r: (r[0], int(r[1:])))
EL = ['4.A.1.a.1', '4.A.1.a.2', '4.A.1.b.1', '4.A.1.b.2', '4.A.1.b.3', '4.A.2.a.1', '4.A.2.a.2', '4.A.2.a.3', '4.A.2.a.4',
      '4.A.2.b.1', '4.A.2.b.2', '4.A.2.b.3', '4.A.2.b.4', '4.A.2.b.5', '4.A.2.b.6', '4.A.3.a.1', '4.A.3.a.2', '4.A.3.a.3', '4.A.3.a.4',
      '4.A.3.b.1', '4.A.3.b.2', '4.A.3.b.4', '4.A.3.b.5', '4.A.3.b.6'] + [f'4.A.4.a.{i}' for i in range(1, 9)] + [f'4.A.4.b.{i}' for i in range(1, 7)] + [f'4.A.4.c.{i}' for i in range(1, 4)]
els = sorted(EL)
assert len(els) == 41
G = dict(zip(els, order))

def us(prefixes, l):
    # 이 직업의 세부 작업과 많이 겹치는 미국 직업부터(대표성이 높은 순)
    mine = dict(l)
    cand = [(sum(min(w, mine.get(d, 0)) for d, w in v[1]), v[0]) for c, v in T['occ'].items() if any(c.startswith(p) for p in prefixes)]
    return [n for _, n in sorted(cand, key=lambda x: (-x[0], x[1]))]

out = {'v': 1, 'sm': {}, 'mid': {}}
for kind, src, ref in (('sm', T['sm'], K['small']), ('mid', T['mid'], K['map'])):
    for code, l in src.items():
        d = [[T['dwa'].get(x, x), G['.'.join(x.split('.')[:5])], round(w, 4)] for x, w in l[:8]]
        info = ref.get(code) or {}
        u = us(info.get('soc_prefix') or [], l)
        out[kind][code] = {'d': d, 'us': u[:8], 'n': info.get('onet_occupations') or len(u)}
# 비슷한 일을 하는 직업: 41개 업무 비중의 코사인 유사도(3할)와 세부 작업 겹침(같은 작업 비중의 최솟값 합, 7할)
import math
def cos(a, b):
    k = set(a) | set(b); num = sum(a.get(x, 0) * b.get(x, 0) for x in k)
    return num / (math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values())) or 1)
def ovl(a, b):
    A, B = dict(a), dict(b); return sum(min(A[x], B[x]) for x in A if x in B)
for kind, W, D in (('sm', {c: v['w'] for c, v in CM['sm'].items()}, T['sm']), ('mid', {j['code']: j['w41'] for j in CM['jobs']}, T['mid'])):
    for c in W:
        sc = sorted(((0.3 * cos(W[c], W[o]) + 0.7 * ovl(D.get(c, []), D.get(o, [])), o) for o in W if o != c), reverse=True)[:10]
        out[kind].setdefault(c, {'d': [], 'us': [], 'n': 0})['sim'] = [[o, round(s, 3)] for s, o in sc]
json.dump(out, open('evidence.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('evidence.json', len(out['sm']), len(out['mid']))
