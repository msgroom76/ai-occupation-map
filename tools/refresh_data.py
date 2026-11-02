"""자료 자동 반영: 출처마다 새 판이 나왔는지 확인하고, 자동으로 넣을 수 있는 것은 내려받아 파이프라인·점검까지 돌린다.
사이트 숫자를 바꾸는 반영은 GitHub Actions(.github/workflows/data-refresh.yml)가 PR로 올리고, 운영자가 병합해야 사이트에 나간다.
예측 채점(forecasts/score-*.json)은 기준을 미리 공개했으므로 결과와 상관없이 함께 올린다.

자동 반영:  aei  — Anthropic 경제지수 직업별 관측 노출(job_exposure.csv). 바뀌면 교체 + 예측 채점
            lfs  — 지역별고용조사 직업 소분류 취업자(KOSIS). 우리 사이트의 /api/kosis 중계를 거쳐 받는다(열쇠는 서버에만 있음)
알림만:     onet(O*NET 새 판), gh(연구 저장소 변경) — 구조가 바뀔 수 있어 사람이 보고 넣는다
사용: python3 tools/refresh_data.py [--dry] [--report 경로]   (저장소 루트에서)
끝나면 --report 파일에 PR 본문용 요약을 쓰고, 반영한 것이 있으면 종료 코드 0, 없으면 3.
"""
import json, os, re, sys, glob, hashlib, datetime, subprocess, urllib.request, math
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
DRY = '--dry' in sys.argv
REPORT = sys.argv[sys.argv.index('--report') + 1] if '--report' in sys.argv else 'reports/refresh-latest.md'
TODAY = datetime.date.today().isoformat()
UA = {'User-Agent': 'aijido.org data refresh (+https://aijido.org)'}
def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        b = r.read(); return b if binary else b.decode('utf-8')
def run(cmd): print('$', cmd); subprocess.run(cmd, shell=True, check=True)
SRC = open('functions/_sources.js', encoding='utf-8').read()
def have(i): m = re.search(r"\{ id: '" + i + r"',.*?have: '([^']*)'", SRC); return m.group(1) if m else None
done, notes, manual = [], [], []

# ── aei: Anthropic 경제지수 job_exposure.csv ─────────────────────────────
try:
    p = 'pipeline/inputs/dl2/job_exposure.csv'
    new = get('https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/labor_market_impacts/job_exposure.csv', True)
    tree = json.loads(get('https://huggingface.co/api/datasets/Anthropic/EconomicIndex/tree/main/labor_market_impacts'))
    oid = next(x['oid'] for x in tree if x['path'].endswith('job_exposure.csv'))
    if hashlib.sha256(new).hexdigest() != hashlib.sha256(open(p, 'rb').read()).hexdigest():
        if not DRY:
            os.makedirs('pipeline/inputs/dl2/history', exist_ok=True)
            old_copy = f'pipeline/inputs/dl2/history/job_exposure_until_{TODAY}.csv'
            os.replace(p, old_copy); open(p, 'wb').write(new)
            # 예측 채점: 이 자료보다 먼저 공개한 기록 중 가장 최근 것(기준 파일이 적용되는 기록부터)
            snaps = [s for s in json.load(open('forecasts/index.json')) if s['date'][:10] < TODAY and os.path.exists(f"forecasts/{s['date']}.baseline.json")]
            if snaps:
                s = snaps[-1]['date']
                run(f'python3 tools/score_forecast.py --snap {s} --usage {p} --usage-date {TODAY} --usage-old {old_copy} --usage-old-date {snaps[-1]["date"][:10]}')
                sc = json.load(open(f'forecasts/score-{s}-{TODAY}.json'))
                notes.append(f"**예측 채점** ({s} 기록): {sc['verdict']}" + (f" · 방향 일치 {sc['direction']['say']}" if 'direction' in sc else ''))
            SRC = SRC.replace(have('aei'), oid).replace(re.search(r"id: 'aei'.*?haveLabel: '([^']*)'", SRC).group(1), f'{TODAY[:7].replace("-", ".")} 반영본(job_exposure.csv)')
        done.append(f'Anthropic 경제지수 직업별 관측 노출 — 새 판(파일 해시 {oid[:10]}) 반영')
    else: notes.append('Anthropic 경제지수: 바뀐 것 없음')
except Exception as e: manual.append(f'Anthropic 경제지수 확인 실패: {e}')

# ── lfs: 지역별고용조사 직업 소분류 취업자 ────────────────────────────────
try:
    files = sorted(glob.glob('pipeline/inputs/dl_lfs/occ_*.json')); cur = json.load(open(files[-1]))
    cur_prd = re.sub(r'\D', '', cur['as_of'])  # '2025.2/2' → '202522' → 반기 비교용으로 바꾼다
    cur_key = cur_prd[:4] + '0' + cur_prd[4]
    d = json.loads(get('https://aijido.org/api/kosis?org=101&tbl=DT_1ES3B32J&type=data'))
    rows = [r for r in d.get('rows', []) if r.get('item') == '취업자']
    prd = max(r['prd'] for r in rows) if rows else None
    if prd and prd > cur_key:
        name2 = {r['name']: r for r in cur['rows']}
        miss = [r['c1'] for r in rows if r['prd'] == prd and r['c1'] not in name2]
        if miss: raise RuntimeError('직업 이름이 바뀐 줄이 있어 자동으로 넣지 않음: ' + ', '.join(miss[:5]))
        y, h = prd[:4], int(prd[4:])
        out = {'src': f'국가데이터처 지역별고용조사 {y}년 {"상" if h == 1 else "하"}반기, KOSIS DT_1ES3B32J (전국 직업/성별 취업자, KSCO 8차), 단위 천명 · aijido.org/api/kosis로 자동 수집 {TODAY}',
               'as_of': f'{y}.{h}/2', 'rows': [{'lv': name2[r['c1']]['lv'], 'code': name2[r['c1']]['code'], 'name': r['c1'], 'k': float(r['v'])} for r in rows if r['prd'] == prd]}
        if not DRY:
            json.dump(out, open(f'pipeline/inputs/dl_lfs/occ_{y}h{h}.json', 'w'), ensure_ascii=False, indent=0)
            m = re.search(r"(\{ id: 'lfs',.*?have: ')([^']*)(', haveLabel: ')([^']*)(')", SRC)
            SRC = SRC[:m.start()] + m.group(1) + prd + m.group(3) + f'{y}년 {"상" if h == 1 else "하"}반기' + m.group(5) + SRC[m.end():]
        tot0 = next(r['k'] for r in cur['rows'] if r['code'] == '0'); tot1 = next(r['k'] for r in out['rows'] if r['code'] == '0')
        done.append(f'지역별고용조사 직업별 취업자 {cur["as_of"]} → {out["as_of"]} 반영 (전체 {tot0:,.0f}천 명 → {tot1:,.0f}천 명)')
    else: notes.append(f'지역별고용조사: 최신({cur["as_of"]}) 그대로')
except Exception as e: manual.append(f'지역별고용조사 확인 실패: {e}')

# ── 알림만: O*NET, 연구 저장소 ─────────────────────────────────────────
try:
    h = get('https://www.onetcenter.org/database.html')
    v = max(re.findall(r'O\*NET (\d+\.\d+) Database', h), key=float)
    if float(v) > float(have('onet')): manual.append(f'O*NET {v} 판이 나왔어요(지금 {have("onet")}). 업무 구성이 바뀌므로 extract_onet.py로 사람이 넣어 주세요')
    else: notes.append(f'O*NET: 최신({v}) 그대로')
except Exception as e: manual.append(f'O*NET 확인 실패: {e}')

if not DRY and done:
    open('functions/_sources.js', 'w', encoding='utf-8').write(SRC)

# ── 반영한 것이 있으면: 파이프라인 → 점검 → 페이지 ─────────────────────
changes = []
if done and not DRY:
    before = json.load(open('city_meta.json'))
    run('bash pipeline/run.sh')
    for f in ['city_meta.json', 'ksco_soc_map.json', 'tasks.json', 'city_index.png', 'city_roads.png']: run(f'cp pipeline/out/{f} {f}')
    run('python3 tools/build_evidence.py')
    run('python3 tools/validate.py' + (' --aioe ' + os.environ['AIOE_DIR'] if os.environ.get('AIOE_DIR') else '') + ' > /dev/null')
    run('python3 tools/build_jobs.py')
    # 일하는 사람 수(가중치)가 바뀌면 지난 주들의 전체 지수(total)도 새 가중치로 다시 계산한다(통계 개정). 주간 소식 반영(adj)은 그대로.
    M2 = json.load(open('city_meta.json')); Rr = M2['R']; WS = sum(j['ws'] for j in M2['jobs'])
    def oc(j, a): return min(.99, j['cal'] * sum(x * Rr[r][2] / (1 + math.exp(-Rr[r][1] * (2026 - Rr[r][0] + a.get(r, 0)))) for r, x in j['w41'].items()))
    IX = json.load(open('index.json')); moved = []
    for w in IX['weeks']:
        if w.get('total') is None: continue
        t = round(sum(j['ws'] * oc(j, w.get('adj') or {}) for j in M2['jobs']) / WS, 5)
        if abs(t - w['total']) > 1e-5: moved.append((w['week'], w['total'], t)); w['total'] = t
    if moved:
        IX.setdefault('revisions', []).append({'date': TODAY, 'why': '; '.join(done), 'weeks': len(moved), 'last': {'week': moved[-1][0], 'from': moved[-1][1], 'to': moved[-1][2]}})
        json.dump(IX, open('index.json', 'w'), ensure_ascii=False, indent=1)
        notes.append(f'지난 {len(moved)}주의 전체 지수를 새 가중치로 다시 계산했어요(최근 {moved[-1][0]}: {moved[-1][1]*100:.2f}% → {moved[-1][2]*100:.2f}%). index.json revisions에 기록')
    run('python3 tools/check_data.py')
    after = json.load(open('city_meta.json')); R = after['R']
    def occ(s): return min(.99, s['cal'] * sum(x * R[r][2] / (1 + math.exp(-R[r][1] * (2026 - R[r][0]))) for r, x in s['w'].items()))
    name = {c: n for j in after['jobs'] for c, n, _ in j['smalls']}
    for c in after['sm']:
        if c in before['sm']:
            a, b = occ(before['sm'][c]) * 100, occ(after['sm'][c]) * 100
            if abs(b - a) >= .5: changes.append((abs(b - a), c, name.get(c, ''), a, b))
    changes.sort(reverse=True)
    V = json.load(open('validation.json'))['summary']

L = [f'# 자료 자동 반영 {TODAY}', '']
L += ['## 반영한 자료', ''] + ([f'- {x}' for x in done] or ['- 없음'])
if done and not DRY:
    L += ['', '## 사이트 숫자 변화 (2026 노출도, 0.5%p 이상)', '']
    L += ([f'- {c} {n}: {a:.1f}% → {b:.1f}%' for _, c, n, a, b in changes[:20]] or ['- 0.5%p 넘게 바뀐 직업 없음'])
    if len(changes) > 20: L.append(f'- 외 {len(changes) - 20}개')
    L += ['', f"신뢰도(취업자 평균) {V['conf_disp']}% · 근거 등급 A {V['grades'].get('A', 0)} · B {V['grades'].get('B', 0)} · C {V['grades'].get('C', 0)}"]
L += ['', '## 그 밖', ''] + [f'- {x}' for x in notes]
if manual: L += ['', '## 사람이 볼 것', ''] + [f'- {x}' for x in manual]
L += ['', '병합하면 사이트에 나가요. 숫자가 이상하면 병합하지 말고 닫아 주세요. 예측 기록(forecasts/)은 분기마다 따로 고정해요.']
os.makedirs(os.path.dirname(REPORT), exist_ok=True); open(REPORT, 'w').write('\n'.join(L) + '\n'); print('\n'.join(L))
sys.exit(0 if done else 3)
