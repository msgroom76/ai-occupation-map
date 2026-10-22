"""데이터 자동 점검. 표준 라이브러리만 쓴다.
사용: python3 tools/check_data.py            (저장소 루트에서)
      python3 tools/check_data.py --feed-only (소식 갱신 작업용: feed.json만)
오류(ERROR)가 하나라도 있으면 종료 코드 1 → 정기 작업은 push하지 말고 보고만 한다.
경고(WARN)는 진행하되 보고에 적는다."""
import json, math, sys, re
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
E, Wn = [], []
def err(m): E.append(m)
def warn(m): Wn.append(m)

feed_only = '--feed-only' in sys.argv
cm = json.load(open('city_meta.json'))
import os
TK = json.load(open('tasks.json')) if os.path.exists('tasks.json') else None
R = cm['R']

# ---------- feed.json ----------
feed = json.load(open('feed.json'))
ids = [n.get('id') for n in feed['items']]
if len(ids) != len(set(ids)): err('feed: id 중복 ' + str([i for i in set(ids) if ids.count(i) > 1]))
ST = {'pending', 'hold', 'none', 'applied'}
TIER = {'1차 출처', '신뢰 매체', '확인 필요'}
for n in feed['items']:
    i = n.get('id', '?')
    if n.get('st') not in ST: err(f'feed {i}: st 값 이상 {n.get("st")}')
    if n.get('tier') not in TIER: err(f'feed {i}: tier 값 이상 {n.get("tier")}')
    if not str(n.get('url', '')).startswith('https://'): err(f'feed {i}: url이 https가 아님')
    bad = [r for r in n.get('r', []) if r not in R]
    if bad: err(f'feed {i}: 없는 업무 코드 {bad}')
    if len(n.get('r', [])) > 3: warn(f'feed {i}: 업무 코드가 3개 초과')
    if n.get('st') == 'pending' and n.get('tier') == '확인 필요': err(f'feed {i}: 확인 필요인데 pending')
    if not n.get('hd'): err(f'feed {i}: 제목 없음')
    if 'dwa' in n:
        for x in n['dwa']:
            if not (isinstance(x, list) and len(x) == 2 and x[1] in ('a', 'd', 'f')): err(f'feed {i}: dwa 형식 이상 {x} (["DWA ID","a|d|f"])')
            elif TK and x[0] not in TK['dwa']: err(f'feed {i}: 직업 목록에 없는 세부 작업 {x[0]} (tools/find_dwa.py로 찾은 ID만)')
        if len(n['dwa']) > 6: warn(f'feed {i}: 세부 작업이 6개 초과')
        if not n.get('ind'): warn(f'feed {i}: dwa가 있는데 업종(ind)이 없음 — 모든 업종에 퍼짐(범용 발표면 괜찮음)')
    if 'grp' in n and not (isinstance(n['grp'], str) and n['grp']): err(f'feed {i}: grp 형식 이상')
    if n.get('st') == 'pending' and n.get('r') and not n.get('grp'): warn(f'feed {i}: 반영 대기 소식에 묶음(grp)이 없음 — 같은 기능 제품이 중복 반영될 수 있음')
    if 'ind' in n and not (isinstance(n['ind'], list) and all(isinstance(x, str) and x.isdigit() and 1 <= len(x) <= 4 for x in n['ind'])):
        err(f'feed {i}: ind 형식 이상 {n.get("ind")} (한국표준직업분류 코드 앞자리 문자열 목록, 예: ["27"], ["33","28"])')
    try: datetime.fromisoformat(n['ts'])
    except Exception: err(f'feed {i}: ts 형식 이상')
try:
    up = datetime.fromisoformat(feed['updated'])
    age = (datetime.now(KST) - up).total_seconds() / 3600
    if age > 36: warn(f'feed: 마지막 갱신이 {age:.0f}시간 전 (소식 갱신 작업이 멈췄을 수 있음)')
except Exception: err('feed: updated 형식 이상')
_nb = [n for n in feed['items'] if not n.get('base')]
if len(_nb) > 60: warn(f'feed: 기준 발표를 뺀 항목 {len(_nb)}개 (60개 초과)')

# ---------- 저항·쟁점 (feed.front) ----------
JOBC = {j['code'] for j in cm['jobs']} | set(cm['sm'])
FK = {'법·규제', '판결·소송', '사용 거부', '노사', '직능단체', '여론'}
fr = feed.get('front', [])
fids = [n.get('id') for n in fr]
if len(fids) != len(set(fids)): err('front: id 중복')
if set(fids) & set(ids): err('front: items와 id가 겹침 ' + str(sorted(set(fids) & set(ids))))
if len(fr) > 150: warn(f'front: {len(fr)}건 (150건 초과)')
for n in fr:
    i = n.get('id', '?')
    if n.get('sig') != '저항': err(f'front {i}: sig는 저항')
    if n.get('st') != 'none': err(f'front {i}: st는 none (지수에 반영하지 않음)')
    if n.get('tier') not in ('1차 출처', '신뢰 매체'): err(f'front {i}: tier는 1차 출처·신뢰 매체만')
    if n.get('fx') not in ('강', '중', '약'): err(f'front {i}: fx 값 이상 {n.get("fx")}')
    if n.get('kind') not in FK: err(f'front {i}: kind 값 이상 {n.get("kind")}')
    if not str(n.get('url', '')).startswith('https://'): err(f'front {i}: url이 https가 아님')
    if not n.get('hd'): err(f'front {i}: 제목 없음')
    bad = [c for c in n.get('ind', []) if c not in JOBC]
    if bad: err(f'front {i}: 없는 직업 코드 {bad}')
    if not re.match(r'^\d{4}-\d{2}-\d{2}T', str(n.get('ts', ''))): err(f'front {i}: ts 형식 이상')
# 쟁점은 들어온 뒤 다음 월요일 독립 검토를 받는다(rvw = 검토한 주). 3주 넘게 검토 없이 남아 있으면 경고
from datetime import datetime as _dt
for n in feed.get('front', []):
    if n.get('rvw'): continue
    try: age = (datetime.now(KST) - _dt.fromisoformat(n['ts'])).days
    except Exception: continue
    if n.get('added') and (datetime.now(KST) - _dt.fromisoformat(n['added'])).days > 21: warn(f'front {n.get("id")}: 들어온 지 3주가 넘었는데 독립 검토 기록(rvw)이 없음')
for n in feed['items']:
    if n.get('sig') == '저항': err(f'feed {n.get("id")}: 저항 소식은 items가 아니라 front에')

# ---------- 수집 기록 (feed.runs): 두 갈래를 같은 노력으로 찾았는지 ----------
RN_ = feed.get('runs', [])
if len(RN_) > 90: warn(f'runs: {len(RN_)}건 (최근 90회만 남긴다)')
for r in RN_:
    for side in ('push', 'front'):
        x = r.get(side)
        if not isinstance(x, dict) or not all(isinstance(x.get(k), int) and x.get(k) >= 0 for k in ('q', 'cand', 'acc')):
            err(f'runs {r.get("at")}: {side}는 {{q, cand, acc}} 0 이상 정수'); continue
        if x['acc'] > x['cand']: err(f'runs {r.get("at")}: {side} 채택 수가 후보 수보다 많음')
if len(RN_) >= 6 and all(r.get('front', {}).get('q', 0) == 0 for r in RN_[:6]):
    warn('runs: 최근 6회 연속 쟁점 검색을 하지 않음')

# ---------- 구조적 보호막 (protect.json) ----------
if os.path.exists('protect.json'):
    PR = json.load(open('protect.json'))
    for L in PR.get('licenses', []):
        if L.get('type') not in ('독점', '자격', '배치'): err(f'protect {L.get("name")}: type 값 이상')
        if not str(L.get('url', '')).startswith('https://'): err(f'protect {L.get("name")}: url 이상')
        bad = [c for c, cov in L.get('sm', []) if c not in cm['sm'] or cov not in ('전부', '일부')]
        if bad: err(f'protect {L.get("name")}: 소분류 코드·범위 이상 {bad}')
    for A in PR.get('ai_act', {}).get('areas', []):
        bad = [c for c in A.get('sm', []) if c not in cm['sm']]
        if bad: err(f'protect AI기본법 {A.get("item")}: 없는 소분류 {bad}')

if not feed_only:
    # ---------- city_meta.json ----------
    J = cm['jobs']
    def p(r, y, a): m, k, K = R[r]; return K / (1 + math.exp(-k * (y - m + a.get(r, 0))))
    def occ(j, y, a): return min(.99, j['cal'] * sum(x * p(r, y, a) for r, x in j['w41'].items()))
    WS = sum(j['ws'] for j in J)
    if not 2850 <= WS <= 2960: err(f'meta: 취업자 합계 {WS:.0f}만 명 (2,904만 근처여야 함)')
    if len(J) != 56: warn(f'meta: 중분류 {len(J)}개 (56개가 아님)')
    codes = [j['code'] for j in J]
    if len(codes) != len(set(codes)): err('meta: 직업 코드 중복')
    for j in J:
        c = j['code']
        s = sum(j['w41'].values())
        if abs(s - 1) > .02: err(f'meta {c}: 업무 비중 합 {s:.3f}')
        if any(r not in R for r in j['w41']): err(f'meta {c}: 없는 업무 코드')
        if not 0 < j['cal'] <= 1.5: err(f'meta {c}: cal {j["cal"]}')
        for k in ('e', 'il', 'ob', 'ms'):
            v = j.get(k)
            if v is not None and not 0 <= v <= 1: err(f'meta {c}: {k}={v} 범위 밖')
        if j['ws'] <= 0: err(f'meta {c}: 취업자 0 이하')
        v26 = occ(j, 2026, {})
        if j.get('e') is not None and j.get('il') is not None:
            tgt = (j['e'] + j['il']) / 2
            if abs(v26 - tgt) > .12: warn(f'meta {c} {j["name"]}: 2026 노출도 {v26:.2f}가 두 연구 평균 {tgt:.2f}와 12%p 넘게 차이')
        if j.get('ob') is not None and j['ob'] > v26 + .02: warn(f'meta {c}: 실제 사용 {j["ob"]:.2f} > 노출도 {v26:.2f} (화면에서는 상한 적용)')
        if j.get('e') is not None and j.get('il') is not None and abs(j['e'] - j['il']) > .3:
            warn(f'meta {c} {j["name"]}: 두 연구 값 차이 {abs(j["e"]-j["il"])*100:.0f}%p — 연결표 확인 대상')
    for code, s in cm.get('sm', {}).items():
        for k in ('e', 'il', 'ob'):
            v = s.get(k)
            if v is not None and not 0 <= v <= 1: err(f'sm {code}: {k}={v} 범위 밖')
    thin = sorted(c for c, s in cm.get('sm', {}).items() if s.get('n', 1) <= 1)
    if thin: warn(f'sm: 미국 직업 연결이 0~1개인 소분류 {len(thin)}개 (공식 연계표로 바꿀 때 우선 확인): ' + ', '.join(thin))
    for r, (m, k, K) in R.items():
        if not (2018 <= m <= 2050 and 0 < k < 5 and 0 < K <= 1): err(f'R {r}: 곡선 값 이상 {m},{k},{K}')

    # ---------- index.json ----------
    idx = json.load(open('index.json'))
    wk = [w for w in idx['weeks'] if w.get('total') is not None]
    tot = lambda a: sum(j['ws'] * occ(j, 2026, a) for j in J) / WS
    for w in wk:
        calc = tot(w['adj'])
        if abs(calc - w['total']) > .0005: err(f'index {w["week"]}: 저장된 total {w["total"]:.4f} ≠ 재계산 {calc:.4f}')
        bad = [r for r in w['adj'] if r not in R]
        if bad: err(f'index {w["week"]}: 없는 업무 코드 {bad}')
        for a in w.get('applied', []):
            if a not in ids: warn(f'index {w["week"]}: 반영 소식 {a}가 feed에 없음(60건 밖으로 밀렸을 수 있음)')
    if len(wk) >= 2:
        a, b = wk[-2], wk[-1]
        d = (tot(b['adj']) - tot(a['adj'])) * 100
        lim = .2 if b.get('rules') == 'v2' else .5   # v2 규칙: 주당 0.15%p 상한 + 반올림 여유
        if abs(d) > lim: err(f'index {b["week"]}: 전체가 한 주에 {d:+.2f}%p 움직임 ({lim}%p 초과)')
        if b.get('ledger') is not None:  # 반영 원장으로 adj를 다시 만들 수 있어야 한다
            re_ = dict(a['adj'])
            for e in b['ledger']:
                for r in e['r']: re_[r] = min(1.0, re_.get(r, 0) + e['w'])
            bad = [r for r in set(re_) | set(b['adj']) if abs(re_.get(r, 0) - b['adj'].get(r, 0)) > .002]
            if bad: err(f'index {b["week"]}: 반영 원장(ledger)으로 다시 계산한 adj와 다름 {bad}')
        for j in J:
            dj = (occ(j, 2026, b['adj']) - occ(j, 2026, a['adj'])) * 100
            if abs(dj) > 3: warn(f'index {b["week"]} {j["name"]}: 한 주에 {dj:+.1f}%p')
        if not b.get('applied') and abs(d) > .001: err(f'index {b["week"]}: 반영 소식이 없는데 숫자가 움직임')
    # 독립 검토(2026-W44부터): 지수를 움직인 소식은 모두 검토 파일에서 ok|fix 판정을 받았어야 한다
    import glob
    for w in idx['weeks']:
        if w.get('rules') != 'v2' or w['week'] < '2026-W44': continue
        rv = w.get('review')
        if not rv: err(f'index {w["week"]}: 독립 검토 기록(review)이 없음'); continue
        if rv.get('by') == 'skipped': warn(f'index {w["week"]}: 독립 검토 없이 발표함(--no-review)'); continue
        if rv.get('by') != 'independent': warn(f'index {w["week"]}: 검토를 같은 작업이 함(by={rv.get("by")}) — 독립 검토가 아님')
        f = f'review/{w["week"]}.json'
        if not os.path.exists(f): err(f'index {w["week"]}: {f} 없음'); continue
        V = {x.get('id'): x.get('v') for x in json.load(open(f)).get('items', [])}
        miss = [e['id'] for e in w.get('ledger', []) if e.get('w', 0) > 0 and V.get(e['id']) not in ('ok', 'fix')]
        if miss: err(f'index {w["week"]}: 검토 통과 없이 반영된 소식 {miss}')
    for f in glob.glob('review/*.json'):
        if f.endswith('.queue.json'): continue
        try: X = json.load(open(f))
        except Exception as ex: err(f'{f}: JSON 아님 {ex}'); continue
        if X.get('by') not in ('independent', 'self'): err(f'{f}: by 값이 independent|self가 아님')
        for x in X.get('items', []) + X.get('front', []):
            if x.get('v') not in ('ok', 'fix', 'hold'): err(f'{f}: {x.get("id")} 판정 값 이상 {x.get("v")}')
            if x.get('v') in ('fix', 'hold') and not x.get('note'): warn(f'{f}: {x.get("id")} {x.get("v")} 사유(note)가 없음')
    for w in idx['weeks']:
        if any(v > 1.5 for v in w['adj'].values()): warn(f'index {w["week"]}: 한 업무가 1.5년 넘게 앞당겨짐 — 누적 반영 점검')

for m in Wn: print('WARN ', m)
for m in E: print('ERROR', m)
print(f'점검 끝: 오류 {len(E)}건, 경고 {len(Wn)}건')
sys.exit(1 if E else 0)
