"""조직 리포트 계산기. 저장소 루트에서: python3 tools/org_report.py reports/<회사>.json
입력(회사 JSON): {"name", "asof", "headcount", "basis": 인원 근거 설명, "roles":[{"id","name","n","code": 소분류(3자리) 또는 중분류(2자리),"fig": 그림 이름,"note"?}]}
출력: reports/out/<회사>/metrics.json (직무별·조직 수치) — 리포트 문서와 그림이 이 숫자만 쓴다.

계산은 지도와 같다(city_meta 곡선 + index.json 마지막 주 보정). 숫자를 새로 지어내지 않는다.
- 노출도: 그 직무 업무 가운데 AI가 해낼 수 있는 몫(2026·2030). 물때 단계는 물때 테스트와 같은 경계.
- 대체형·보완형: 업무 41개 중 사람이 하던 것을 AI가 대신하기 쉬운 업무(SUB) 몫과 사람을 돕는 업무 몫.
- 업무시간·인건비 환산: 인원 × 노출도 = 'AI가 해낼 수 있는 업무량'의 사람 수 환산(FTE). 인건비는 직종 대분류 월임금총액(고용형태별근로실태조사 2025)으로 곱한 근사치.
  실제 절감액이 아니라 '걸려 있는 규모'다. 리포트에 그렇게 적는다.
- 옮겨가기: 같은 조직 안에서 업무 구성이 비슷하면서(코사인 유사도) 노출도가 낮은 직무.
"""
import json, math, os, sys
cm = json.load(open('city_meta.json')); idx = json.load(open('index.json'))
PR = json.load(open('protect.json')); LB = json.load(open('labor.json')); UK = json.load(open('us_kr.json'))
feed = json.load(open('feed.json'))
R = cm['R']; RN = cm['RN']; SM = cm['sm']; JC = {j['code']: j for j in cm['jobs']}
ADJ = (idx['weeks'][-1] if idx.get('weeks') else {}).get('adj', {})
SUB = {'A5', 'B2', 'B9', 'C1', 'C2', 'C3', 'C4', 'C5', 'C9', 'D15', 'D3'}
ST = [('발목', 0), ('무릎', .2), ('허리', .35), ('가슴', .5), ('목까지', .65)]
WS = sum(j['ws'] for j in cm['jobs'])

def p(r, y): m, k, K = R[r]; return K / (1 + math.exp(-k * (y - m + ADJ.get(r, 0))))
def prof(code):
    """직무 코드 → (가중치 dict, cal, 출처 객체, 중분류 코드)"""
    if len(code) == 3 and code in SM: d = SM[code]; return d['w'], d['cal'], d, code[:2]
    j = JC[code[:2]]; return j['w41'], j['cal'], j, code[:2]
def occ(code, y):
    w, cal, _, _ = prof(code); return min(.99, cal * sum(x * p(r, y) for r, x in w.items()))
def stg(v):
    s = 0
    while s < 4 and v >= ST[s + 1][1]: s += 1
    return s
def split(code, y=2026):
    w, cal, _, _ = prof(code); s = sum(x * p(r, y) for r, x in w.items() if r in SUB); a = sum(x * p(r, y) for r, x in w.items() if r not in SUB)
    return s / max(s + a, 1e-9)
def tasks(code, y=2026, n=4):
    w, cal, _, _ = prof(code)
    c = sorted(((x * p(r, y) * cal, r) for r, x in w.items()), reverse=True)[:n]
    return [{'id': r, 'name': RN[r][0], 'share': round(x, 3), 'type': '대체형' if r in SUB else '보완형'} for x, r in c]
def cos(a, b):
    k = set(a) | set(b); num = sum(a.get(i, 0) * b.get(i, 0) for i in k)
    return num / math.sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()) or 1)
def lic(code):
    hit = (lambda c: c == code) if len(code) == 3 else (lambda c: c.startswith(code))
    return [{'name': l['name'], 'type': l['type'], 'law': l['law'], 'article': l['article']} for l in PR.get('licenses', []) if any(hit(c) for c, _ in l['sm'])]
def aiact(code):
    hit = (lambda c: c == code) if len(code) == 3 else (lambda c: c.startswith(code))
    return [a['text'] for a in (PR.get('ai_act') or {}).get('areas', []) if any(hit(c) for c in a['sm'])]
def news(mid, kinds=('items',)):
    out = []
    for n in feed.get('items', []):
        if n.get('st') == 'hold': continue
        if any(mid.startswith(c) or c.startswith(mid) for c in n.get('ind', []) or []): out.append(n)
    out.sort(key=lambda n: n['ts'], reverse=True)
    return [{'hd': n['hd'], 'src': n['src'], 'url': n['url'], 'ts': n['ts'][:10]} for n in out[:3]]
def front(mid):
    out = [n for n in feed.get('front', []) if any(mid.startswith(c) or c.startswith(mid) for c in n.get('ind', []) or [])] + [n for n in feed.get('front', []) if not n.get('ind')]
    seen = set(); res = []
    for n in sorted(out, key=lambda n: ({'강': 0, '중': 1, '약': 2}.get(n.get('fx'), 3), n['ts']), reverse=False):
        if n['id'] in seen: continue
        seen.add(n['id']); res.append({'hd': n['hd'], 'src': n['src'], 'url': n['url'], 'fx': n.get('fx'), 'kind': n.get('kind'), 'ts': n['ts'][:10], 'all': not n.get('ind')})
    return res[:3]

def run(path):
    C = json.load(open(path)); out_dir = f"reports/out/{C['id']}"; os.makedirs(out_dir, exist_ok=True)
    rows = []
    for r in C['roles']:
        code = r['code']; w, cal, d, mid = prof(code); mj = mid[0]
        e26, e30 = occ(code, 2026), occ(code, 2030)
        wage = LB['wage']['major'].get(mj, {}).get('wage', {}).get('all')
        hours = LB['wage']['major'].get(mj, {}).get('hours', {}).get('all')
        un = (PR.get('union') or {}).get('major', {}).get(mj, {})
        ug = UK['us'].get(UK['map'].get(mid))
        rows.append({**r, 'job': JC[mid]['name'], 'sm': (next((n for c, n, *_ in JC[mid].get('smalls', []) if c == code), None) if len(code) == 3 else None),
                     'e26': round(e26, 4), 'e30': round(e30, 4), 'stage': stg(e26), 'stage30': stg(e30), 'sub': round(split(code), 3),
                     'ob': round(min(d.get('ob', 0) or 0, e26), 4), 'ob_raw': d.get('ob'), 'tasks': tasks(code),
                     'wage_k': wage, 'hours': hours, 'fte': round(r['n'] * e26, 2), 'fte30': round(r['n'] * e30, 2),
                     'cost_m': round(r['n'] * e26 * (wage or 0) * 12 / 1e5, 2),       # 억 원/년 (천원 단위 임금)
                     'union_kr': un.get('all'), 'union_us': ug and ug['union'], 'lic_us': ug and ug['license'],
                     'licenses': lic(code), 'aiact': aiact(code), 'news': news(mid), 'front': front(mid), '_w': w})
    N = sum(r['n'] for r in rows)
    org = {'n': N, 'e26': round(sum(r['n'] * r['e26'] for r in rows) / N, 4), 'e30': round(sum(r['n'] * r['e30'] for r in rows) / N, 4),
           'kr26': round(sum(j['ws'] * occ(j['code'], 2026) for j in cm['jobs']) / WS, 4), 'kr30': round(sum(j['ws'] * occ(j['code'], 2030) for j in cm['jobs']) / WS, 4),
           'fte': round(sum(r['fte'] for r in rows), 1), 'fte30': round(sum(r['fte30'] for r in rows), 1), 'cost': round(sum(r['cost_m'] for r in rows), 1),
           'payroll': round(sum(r['n'] * (r['wage_k'] or 0) * 12 / 1e5 for r in rows), 1),
           'sub': round(sum(r['fte'] * r['sub'] for r in rows) / max(sum(r['fte'] for r in rows), 1e-9), 3)}
    org['stage'] = stg(org['e26']); org['stage30'] = stg(org['e30'])
    # 조직 전체에서 AI가 가장 많이 해낼 업무(인원 가중)
    agg = {}
    for r in rows:
        w, cal, _, _ = prof(r['code'])
        for t, x in w.items(): agg[t] = agg.get(t, 0) + r['n'] * x * p(t, 2026) * cal
    org['tasks'] = [{'id': t, 'name': RN[t][0], 'fte': round(v, 2), 'type': '대체형' if t in SUB else '보완형'} for t, v in sorted(agg.items(), key=lambda kv: -kv[1])[:8]]
    # 옮겨가기: 노출도 높은 직무 → 업무가 비슷하고 노출도가 10%p 이상 낮은 사내 직무
    for r in rows:
        cand = [(cos(r['_w'], o['_w']), o) for o in rows if o is not r and o['e26'] <= r['e26'] - .10]
        cand.sort(key=lambda x: -x[0])
        r['moves'] = [{'to': o['name'], 'sim': round(s, 2), 'gap': round(r['e26'] - o['e26'], 3)} for s, o in cand[:2] if s >= .55]
    for r in rows: r.pop('_w')
    rows.sort(key=lambda r: -r['e26'])
    M = {'company': {k: C[k] for k in C if k != 'roles'}, 'org': org, 'roles': rows, 'stages': ST,
         'src': {'wage': LB['wage']['src'], 'union': (PR.get('union') or {}).get('survey', {}).get('src'), 'us': UK['src']}}
    json.dump(M, open(f'{out_dir}/metrics.json', 'w'), ensure_ascii=False, indent=1)
    return M

if __name__ == '__main__':
    M = run(sys.argv[1]); o = M['org']
    print(f"{M['company']['name']}: {o['n']}명 · 2026 {o['e26']*100:.1f}% ({ST[o['stage']][0]}) · 2030 {o['e30']*100:.1f}% · 한국 {o['kr26']*100:.1f}% · FTE {o['fte']} · 걸린 인건비 {o['cost']}억/{o['payroll']}억 · 대체형 {o['sub']*100:.0f}%")
    for r in M['roles']: print(f"  {r['name']:<14} {r['n']:>4}명 {r['e26']*100:5.1f}% → {r['e30']*100:5.1f}% {ST[r['stage']][0]:<3} 대체 {r['sub']*100:3.0f}% FTE {r['fte']:5.1f} 이동 {[m['to'] for m in r['moves']]}")
