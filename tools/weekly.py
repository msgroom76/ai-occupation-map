"""주간 지수 발표: feed.json의 st=pending 소식을 반영해 index.json에 새 주를 추가한다.
사용: python3 tools/weekly.py 2026-10-26 --queue  (① 독립 검토할 소식 목록 review/<주>.queue.json 만들기)
      python3 tools/weekly.py 2026-10-26 --dry    (파일을 바꾸지 않고 결과만 보기)
      python3 tools/weekly.py 2026-10-26          (③ 검토 결과 review/<주>.json을 반영해 발표)

독립 검토(2026-10-22): 지수를 움직일 소식은 발표 전에, 소식을 고른 작업과 따로 도는 검토자가 원문을 다시 열어 판정한다.
- review/<주>.json = {"week","by":"independent|self","at","items":[{"id","v":"ok|fix|hold","note","fix":{...}}]}
- hold → 이번 주에 반영하지 않고 st=hold(사유 rv). fix → 고칠 수 있는 칸(FIXABLE)만 고친 뒤 반영.
- 검토 목록에 없던 소식(검토 뒤에 들어온 것)은 이번 주에 반영하지 않고 다음 주로 넘긴다.
- 검토 파일이 없으면 발표하지 않는다(--no-review로만 건너뛸 수 있고, 그 주는 check_data가 경고한다).

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
DRY = '--dry' in sys.argv; QUEUE = '--queue' in sys.argv; NOREV = '--no-review' in sys.argv
FIXABLE = ('tier', 'kr', 'sig', 'ind', 'r', 'dwa', 'grp')
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

# ---------- 독립 검토 ----------
def basic(n):  # 묶음 처리 전, 이 소식 혼자의 이동(0이면 검토할 필요 없음)
    return 0 if n.get('grp') in recent else weight(n)[0]
if QUEUE:
    os.makedirs('review', exist_ok=True)
    keys = ('id', 'ts', 'src', 'url', 'tier', 'kr', 'sig', 'ind', 'hd', 'r', 'dwa', 'grp')
    q = [{k: n[k] for k in keys if k in n} for n in feed['items'] if n.get('st') == 'pending' and n.get('r') and basic(n) > 0]
    json.dump({'week': wk, 'date': D, 'made': dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec='seconds'), 'items': q}, open(f'review/{wk}.queue.json', 'w'), ensure_ascii=False, indent=1)
    print(f'review/{wk}.queue.json: 검토할 소식 {len(q)}건'); sys.exit(0)
RV = None; rvf = f'review/{wk}.json'
if os.path.exists(rvf):
    RV = json.load(open(rvf))
    if RV.get('week') != wk: sys.exit(f'{rvf}: week 값이 {wk}가 아님')
elif not (DRY or NOREV):
    sys.exit(f'{rvf} 없음 — 먼저 --queue로 목록을 만들고 독립 검토 결과를 받아야 발표할 수 있어요(급할 때만 --no-review)')
rv_ids, rv_stat = set(), {'ok': 0, 'fix': 0, 'hold': 0}
if RV:
    byid = {n['id']: n for n in feed['items']}
    for x in RV.get('items', []):
        n = byid.get(x.get('id')); v = x.get('v')
        if v not in rv_stat: sys.exit(f"{rvf}: {x.get('id')} 판정 값이 ok|fix|hold가 아님")
        rv_stat[v] += 1
        if not n: continue
        rv_ids.add(n['id'])
        if v == 'hold': n['st'] = 'hold'; n['rv'] = (x.get('note') or '독립 검토에서 보류')[:200]; continue
        if v == 'fix':
            for k, val in (x.get('fix') or {}).items():
                if k not in FIXABLE: sys.exit(f"{rvf}: {n['id']} 고칠 수 없는 칸 {k}")
                if val is None: n.pop(k, None)
                else: n[k] = val
            n['rv'] = (x.get('note') or '독립 검토에서 수정')[:200]
late = [n['id'] for n in feed['items'] if RV and n.get('st') == 'pending' and n.get('r') and basic(n) > 0 and n['id'] not in rv_ids]
if late: print('검토 뒤에 들어와 다음 주로 넘김: ' + ', '.join(late))
cand = [(n, *weight(n)) for n in feed['items'] if n.get('st') == 'pending' and n.get('r') and n['id'] not in late]
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
# 소식별 기여(%p): 그 소식 하나만 반영했을 때의 변화를, 합이 실제 변화와 같도록 나눈다
solo = {}
for e in ledger:
    if e['w'] <= 0: continue
    a = dict(base)
    for r in e['r']: a[r] = min(CAP_R, a.get(r, 0) + e['w'])
    solo[e['id']] = total(a) - t0
ssum = sum(solo.values())
for e in ledger: e['dp'] = round(solo.get(e['id'], 0) / ssum * (t1 - t0), 6) if ssum > 0 else 0
applied = [e['id'] for e in ledger]
print(f"{wk} 전체 {t0*100:.3f}% → {t1*100:.3f}% ({(t1-t0)*100:+.3f}%p), 소식 {len(ledger)}건 중 반영 {sum(1 for e in ledger if e['w']>0)}건, 축소 비율 {scale}")
for e in ledger: print(f"  {e['w']:.4f}년 {e['dp']*100:+.4f}%p {e['id']} [{e['why']}]")
if RV: print(f"독립 검토({RV.get('by')}): 확인 {rv_stat['ok']} · 수정 {rv_stat['fix']} · 보류 {rv_stat['hold']}")
if DRY: sys.exit(0)
for n in feed['items']:
    if n['id'] in applied: n['st'] = 'applied'; n['wk'] = wk
if last.get('total') is None and len(idx['weeks']) == 1: last['total'] = round(total({}), 5)
idx['weeks'].append({'week': wk, 'date': D, 'adj': adj, 'total': round(t1, 5), 'applied': applied, 'ledger': ledger, 'scale': scale, 'rules': 'v2',
                    'review': ({'by': RV.get('by', '?'), **rv_stat, 'late': late} if RV else {'by': 'skipped'})})
# 두 파일을 임시 파일에 쓴 뒤 한꺼번에 바꾼다(중간 실패로 한쪽만 바뀌지 않게)
json.dump(idx, open('index.json.tmp', 'w'), ensure_ascii=False, indent=1)
json.dump(feed, open('feed.json.tmp', 'w'), ensure_ascii=False, indent=1)
os.replace('index.json.tmp', 'index.json'); os.replace('feed.json.tmp', 'feed.json')
