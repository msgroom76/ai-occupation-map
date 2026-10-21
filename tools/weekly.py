"""주간 지수 발표: feed.json의 st=pending 소식을 반영해 index.json에 새 주를 추가한다.
사용: python3 tools/weekly.py 2026-10-26          (발표일, 월요일)
      python3 tools/weekly.py 2026-10-26 --dry    (파일을 바꾸지 않고 결과만 보기)

반영 규칙 v2 (2026-10-21, 서비스 검증 후 개정 — PIPELINE.md '주간 지수 규칙')
- 기본 이동: 1차 출처 0.25년, 신뢰 매체 1/12년, 확인 필요 0.
- 한국 밖 발표(kr이 아님)는 절반, 한 기관의 '도입' 소식은 절반(노출도는 '할 수 있는가'의 지표라서).
- 업종(ind)이 있으면 그 업종 취업자 비중만큼만 반영(병원 한 곳의 도입이 모든 직업의 기록 업무를 앞당기지 않게).
- 같은 묶음(grp: 같은 기능의 제품군)은 13주 안에 한 번만. 같은 주에 여러 건이면 가장 센 것 하나.
- 업무별 누적 이동은 최대 1년.
- 한 주에 소식으로 움직이는 전체 폭은 최대 0.15%p(곡선이 이미 담고 있는 자연 추세 수준). 넘으면 그 주 이동을 같은 비율로 줄인다.
- 반영 내역은 주마다 ledger로 남겨 언제든 다시 계산·되돌릴 수 있게 한다.
"""
import json, math, sys, os, datetime as dt

args = [a for a in sys.argv[1:] if not a.startswith('--')]
DRY = '--dry' in sys.argv
D = args[0] if args else dt.date.today().isoformat()
feed = json.load(open('feed.json')); idx = json.load(open('index.json')); cm = json.load(open('city_meta.json'))
SHIFT = {'1차 출처': .25, '신뢰 매체': 1 / 12, '확인 필요': 0}
CAP_R = 1.0        # 업무별 누적 이동 상한(년)
CAP_WEEK = .0015   # 한 주 전체 이동 상한(0.15%p)
GRP_WEEKS = 13     # 같은 묶음 재반영 금지 기간
last = idx['weeks'][-1]; base = dict(last['adj'])
y, w, _ = dt.date.fromisoformat(D).isocalendar(); wk = f'{y}-W{w:02d}'
if last['week'] == wk: sys.exit(f'{wk} 이미 발표됨')
J = cm['jobs']; WS = sum(j['ws'] for j in J)

def ind_share(n):
    ind = n.get('ind')
    if not ind: return 1.0
    s = sum(j['ws'] for j in J if any(j['code'].startswith(p) or p.startswith(j['code']) for p in ind))
    return s / WS

def weight(n):
    if n.get('st') != 'pending' or not n.get('r'): return 0, ''
    sh = SHIFT.get(n['tier'], 0)
    why = [f"{n['tier']} {sh:.3f}년"]
    if not n.get('kr'): sh *= .5; why.append('해외 ×0.5')
    if n.get('sig') == '도입': sh *= .5; why.append('도입 ×0.5')
    s = ind_share(n)
    if s < 1: sh *= s; why.append(f'업종 비중 ×{s:.2f}')
    return sh, ' · '.join(why)

# 최근 13주 안에 반영된 묶음
recent = set()
for wkx in idx['weeks'][-GRP_WEEKS:]:
    for e in wkx.get('ledger', []):
        if e.get('grp') and e.get('w', 0) > 0: recent.add(e['grp'])
for n in feed['items']:  # ledger가 생기기 전에 반영된 소식
    if n.get('st') == 'applied' and n.get('grp') and n.get('wk') and n['wk'] >= idx['weeks'][max(0, len(idx['weeks']) - GRP_WEEKS)]['week']:
        recent.add(n['grp'])

cand = [(n, *weight(n)) for n in feed['items'] if n.get('st') == 'pending' and n.get('r')]
best = {}
for n, sh, why in cand:
    g = n.get('grp') or n['id']
    if g not in best or sh > best[g][1]: best[g] = (n, sh, why)
ledger = []
for n, sh, why in cand:
    g = n.get('grp') or n['id']
    if n.get('grp') in recent: sh, why = 0, f"같은 묶음({n['grp']}) 최근 {GRP_WEEKS}주 안에 반영됨"
    elif best[g][0] is not n: sh, why = 0, f"같은 묶음({g})의 더 센 소식으로 대신"
    ledger.append({'id': n['id'], 'grp': n.get('grp'), 'r': n['r'], 'w': round(sh, 5), 'why': why})

R = cm['R']
def p(r, yr, a): m, k, K = R[r]; return K / (1 + math.exp(-k * (yr - m + a.get(r, 0))))
def occ(j, yr, a): return min(.99, j['cal'] * sum(x * p(r, yr, a) for r, x in j['w41'].items()))
def total(a): return sum(j['ws'] * occ(j, 2026, a) for j in J) / WS

def apply(scale):
    a = dict(base)
    for e in ledger:
        for r in e['r']: a[r] = min(CAP_R, a.get(r, 0) + e['w'] * scale)
    return {r: round(v, 4) for r, v in a.items()}

t0 = total(base); adj = apply(1); t1 = total(adj); scale = 1.0
if t1 - t0 > CAP_WEEK:
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if total(apply(mid)) - t0 > CAP_WEEK: hi = mid
        else: lo = mid
    scale = round(lo, 4); adj = apply(scale); t1 = total(adj)
for e in ledger: e['w'] = round(e['w'] * scale, 5)
applied = [e['id'] for e in ledger]
print(f"{wk} 전체 {t0*100:.3f}% → {t1*100:.3f}% ({(t1-t0)*100:+.3f}%p), 소식 {len(ledger)}건 중 반영 {sum(1 for e in ledger if e['w']>0)}건, 축소 비율 {scale}")
for e in ledger: print(f"  {e['w']:.4f}년 {e['id']} [{e['why']}]")
if DRY: sys.exit(0)
for n in feed['items']:
    if n['id'] in applied: n['st'] = 'applied'; n['wk'] = wk
if last.get('total') is None and len(idx['weeks']) == 1: last['total'] = round(total({}), 5)
idx['weeks'].append({'week': wk, 'date': D, 'adj': adj, 'total': round(t1, 5), 'applied': applied, 'ledger': ledger, 'scale': scale, 'rules': 'v2'})
# 두 파일을 임시 파일에 쓴 뒤 한꺼번에 바꾼다(중간 실패로 한쪽만 바뀌지 않게)
json.dump(idx, open('index.json.tmp', 'w'), ensure_ascii=False, indent=1)
json.dump(feed, open('feed.json.tmp', 'w'), ensure_ascii=False, indent=1)
os.replace('index.json.tmp', 'index.json'); os.replace('feed.json.tmp', 'feed.json')
