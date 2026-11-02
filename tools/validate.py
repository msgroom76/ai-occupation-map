"""숫자 신뢰도 점검 → validation.json (공개) + reports/validation.md (운영자용)

연구기관들이 지표를 검증하는 방식(OECD·JRC 합성지표 지침, Eloundou 외 2024, IMF 2023, ILO 2025)을 우리 숫자에 그대로 적용한다.
1) 출처끼리 일치: 두 연구(Eloundou 외 β, ILO)의 소분류 순위 상관. 모델 판정 vs 사람 판정(Eloundou 원자료의 human β).
2) 연결 경로 민감도: 우리가 만든 한국→미국 직업 연결표 대신, 공식 경로(국가데이터처 KSCO→ISCO 연계표 → ESCO/ISCO→O*NET 연계표)로 다시 계산.
3) 불확실성 범위: 판단이 들어간 선택(모델/사람 판정, 연결 경로, 미국 고용 가중/균등, 두 연구 섞는 비율 25~75%)을
   무작위로 2,000번 조합해 직업마다 값과 순위의 범위(10~90%)를 낸다. (JRC 지침의 불확실성 분석)
4) 외부 지표와 비교: 실제 사용(Anthropic 경제지수), Microsoft AI 적용도, Felten 외 AIOE(2021)·언어모델 AIOE(2023)와 순위 상관.
5) 근거 등급: 연결된 미국 직업 수, 두 연구의 차이, 범위 폭으로 A·B·C.
6) 주간 소식 판정의 독립 검토 통과율(review/).
사이트 숫자는 바꾸지 않는다. 결과만 따로 낸다.
사용: python3 tools/validate.py [--aioe /경로/aioe 저장소]   (AIOE 저장소가 없으면 4)의 AIOE 비교는 건너뜀)
"""
import csv, json, math, os, sys, random, glob, collections, statistics as st
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'pipeline', 'inputs'); SC = os.path.join(ROOT, 'pipeline', 'scripts')
AIOE = sys.argv[sys.argv.index('--aioe') + 1] if '--aioe' in sys.argv else '/home/claude/aioe-data/aioe'
random.seed(20261102)

ns = {}; exec(open(os.path.join(SC, 'soc_map_small.py')).read(), ns); small_of = ns['small_of']
M = json.load(open(os.path.join(ROOT, 'city_meta.json')))
SM = M['sm']; CODES = sorted(SM)
NAME = {c: n for j in M['jobs'] for c, n, _ in j['smalls']}
EMPK = {c: e for j in M['jobs'] for c, _, e in j['smalls']}

# ── 원자료 ─────────────────────────────────────────────
EMP = {}
for r in csv.DictReader(open(os.path.join(P, 'gpts/national_May2021_dl.csv'), encoding='utf-8-sig')):
    if r['O_GROUP'] == 'detailed':
        try: EMP[r['OCC_CODE']] = float(r['TOT_EMP'].replace(',', ''))
        except ValueError: pass
def emp(soc): return EMP.get(soc) or next((v for k, v in EMP.items() if k[:6] == soc[:6]), 1000.0)
OL = {}
for r in csv.DictReader(open(os.path.join(P, 'gpts/occ_level.csv'))):
    OL[r['O*NET-SOC Code']] = {'dv': float(r['dv_rating_beta']), 'human': float(r['human_rating_beta'])}

# 우리 연결표(수작업) 경로: 소분류 ← 미국 SOC(접두어) ← O*NET 직업
bysoc = collections.defaultdict(list)
for c in OL: bysoc[c[:7]].append(c)
MAN = collections.defaultdict(list)   # 소분류 → [(O*NET, 미국 고용 몫)]
for soc, cs in bysoc.items():
    k = small_of(soc)
    if k:
        for c in cs: MAN[k].append((c, emp(soc) / len(cs)))

# 공식 경로: KSCO 세분류 → ISCO(국가데이터처 연계표) → O*NET(ESCO/ISCO 연계표)
wb = openpyxl.load_workbook(os.path.join(P, 'ksco_isco/KSCO8_ISCO08_20251103.xlsx'), read_only=True)
pairs = collections.defaultdict(list)
for i, r in enumerate(wb['4-1. (연계표) 세분류 연계표(KSCO-ISCO)'].iter_rows(values_only=True)):
    if i == 0 or r[0] is None: continue
    k = str(r[0]).strip()
    if k[:1].isdigit(): pairs[k].append(str(r[4]).strip().lstrip('*').zfill(4))
xw = openpyxl.load_workbook(os.path.join(P, 'onet_xw/ESCO_to_ONET-SOC.xlsx'), read_only=True)
ISCO2ON = collections.defaultdict(set)
for r in xw[xw.sheetnames[0]].iter_rows(values_only=True):
    if r[0] and r[2] and str(r[0])[:4].isdigit() and str(r[2]) in OL: ISCO2ON[str(r[0])[:4]].add(str(r[2]))
OFF = collections.defaultdict(dict)   # 소분류 → {세분류: [ISCO]}
for k, isos in pairs.items(): OFF[k[:3]][k] = list(dict.fromkeys(isos))

def e_manual(c, src, weighting):
    l = MAN.get(c)
    if not l: return None
    if weighting == 'eq': return st.mean(OL[o][src] for o, _ in l)
    z = sum(w for _, w in l); return sum(OL[o][src] * w for o, w in l) / z
def e_official(c, src):
    vals = []
    for u, isos in OFF.get(c, {}).items():
        v = [OL[o][src] for x in isos for o in ISCO2ON.get(x, ())]
        if v: vals.append(st.mean(v))
    return st.mean(vals) if vals else None

def rank(d):  # 1 = 가장 높음
    s = sorted(d, key=lambda c: -d[c]); return {c: i + 1 for i, c in enumerate(s)}
def spearman(a, b):
    ks = [k for k in a if k in b and a[k] is not None and b[k] is not None]
    ra, rb = rank({k: a[k] for k in ks}), rank({k: b[k] for k in ks}); n = len(ks)
    if n < 3: return None, n
    ma, mb = st.mean(ra.values()), st.mean(rb.values())
    num = sum((ra[k] - ma) * (rb[k] - mb) for k in ks)
    den = math.sqrt(sum((ra[k] - ma) ** 2 for k in ks) * sum((rb[k] - mb) ** 2 for k in ks))
    return round(num / den, 3), n

E0 = {c: SM[c]['e'] for c in CODES}; IL = {c: SM[c]['il'] for c in CODES}
T0 = {c: (E0[c] + IL[c]) / 2 for c in CODES}

# ── 1) 2) 출처 일치·경로 민감도 ─────────────────────────
var = {(s, r, w): {} for s in ('dv', 'human') for r in ('manual', 'official') for w in ('emp', 'eq')}
for c in CODES:
    for (s, r, w) in var:
        v = e_manual(c, s, w) if r == 'manual' else e_official(c, s)
        var[(s, r, w)][c] = v
agree = {
    'eloundou_vs_ilo': spearman(E0, IL),
    'model_vs_human': spearman(var[('dv', 'manual', 'emp')], var[('human', 'manual', 'emp')]),
    'our_map_vs_official': spearman(var[('dv', 'manual', 'emp')], var[('dv', 'official', 'emp')]),
    'repro_check': spearman(E0, {c: var[('dv', 'manual', 'emp')][c] for c in CODES if SM[c].get('own')}),
}
gap = {c: (var[('dv', 'official', 'emp')][c] - var[('dv', 'manual', 'emp')][c]) for c in CODES
       if var[('dv', 'official', 'emp')][c] is not None and var[('dv', 'manual', 'emp')][c] is not None and SM[c].get('own')}

# ── 3) 불확실성 범위(몬테카를로) ───────────────────────
N = 2000; draws = collections.defaultdict(list); ranks = collections.defaultdict(list)
for _ in range(N):
    s = random.choice(('dv', 'human')); r = random.choice(('manual', 'official')); w = random.choice(('emp', 'eq'))
    a = random.uniform(.25, .75)
    t = {}
    for c in CODES:
        e = var[(s, r, w)][c]
        if e is None or (r == 'manual' and not SM[c].get('own')):
            e = E0[c] * (var[(s, 'manual', 'emp')].get(c) or E0[c]) / (var[('dv', 'manual', 'emp')].get(c) or E0[c])
        t[c] = a * e + (1 - a) * IL[c]
    rk = rank(t)
    for c in CODES: draws[c].append(t[c] / T0[c]); ranks[c].append(rk[c])
def q(l, p): l = sorted(l); return l[min(len(l) - 1, int(p * len(l)))]
R0 = rank(T0)

# 사이트가 보여 주는 2026 값(주간 조정 포함) — 범위는 이 값에 비율로 얹는다
IDX = json.load(open(os.path.join(ROOT, 'index.json'))); ADJ = (IDX['weeks'][-1] if IDX['weeks'] else {}).get('adj', {})
if isinstance(ADJ, str): ADJ = eval(ADJ)
RP = M['R']
def pv(r, y): return RP[r][2] / (1 + math.exp(-RP[r][1] * (y - RP[r][0] + ADJ.get(r, 0))))
def occ(c, y): s = SM[c]; return min(.99, s['cal'] * sum(x * pv(r, y) for r, x in s['w'].items()))

# ── 4) 외부 지표 ───────────────────────────────────────
ext = {'observed_use(Anthropic)': {c: SM[c].get('ob') for c in CODES}}
U = json.load(open(os.path.join(ROOT, 'pipeline/out/intermediate/usage_agg.json'))) if os.path.exists(os.path.join(ROOT, 'pipeline/out/intermediate/usage_agg.json')) else None
if U: ext['applicability(Microsoft)'] = {c: U['mS'].get(c) for c in CODES}
def soc_index(path, sheet, col):
    d = collections.defaultdict(lambda: [0, 0]); wb = openpyxl.load_workbook(path, read_only=True); hdr = None
    for r in wb[sheet].iter_rows(values_only=True):
        if hdr is None:
            if r and 'SOC Code' in [str(x) for x in r]: hdr = [str(x) for x in r]
            continue
        rr = dict(zip(hdr, r)); soc = str(rr.get('SOC Code') or ''); v = rr.get(col)
        if len(soc) == 7 and isinstance(v, (int, float)):
            k = small_of(soc)
            if k: d[k][0] += v * emp(soc); d[k][1] += emp(soc)
    return {k: a / b for k, (a, b) in d.items() if b}
if os.path.isdir(AIOE):
    try: ext['AIOE(Felten 2021)'] = soc_index(os.path.join(AIOE, 'AIOE_DataAppendix.xlsx'), 'Appendix A', 'AIOE')
    except Exception as ex: print('AIOE 건너뜀', ex)
    try: ext['LM-AIOE(Felten 2023)'] = soc_index(os.path.join(AIOE, 'Language Modeling AIOE and AIIE.xlsx'), 'LM AIOE', 'Language Modeling AIOE')
    except Exception as ex: print('LM-AIOE 건너뜀', ex)
extc = {k: spearman(T0, v) for k, v in ext.items()}

# ── 5) 근거 등급 ───────────────────────────────────────
out = {'v': 1, 'at': IDX['weeks'][-1]['date'] if IDX['weeks'] else None, 'n_draws': N, 'sm': {}}
grades = collections.Counter()
for c in CODES:
    v = occ(c, 2026); lo, hi = v * q(draws[c], .1), v * q(draws[c], .9)
    side = 'up' if lo > v else 'down' if hi < v else None   # 다른 계산 방식 대부분이 우리 값보다 높게/낮게 봄
    lo, hi = min(lo, v), max(hi, v)
    rk = [min(q(ranks[c], .1), R0[c]), max(q(ranks[c], .9), R0[c])]
    MID = next(j for j in M['jobs'] if any(x[0] == c for x in j['smalls']))
    n = SM[c].get('n', 0) if SM[c].get('own') else (MID.get('nocc') or 0)   # 자기 연결이 없으면 중분류의 업무 구성을 쓴다 → 중분류의 미국 직업 수
    d = abs(E0[c] - IL[c]); rw = rk[1] - rk[0]   # 순위가 흔들리는 폭(JRC 지침: 값보다 순위 범위로 본다. 값 폭은 높은 직업일수록 커져서)
    if n >= 3 and d <= .12 and rw <= 15: g = 'A'
    elif n <= 1 or d > .2 or rw > 30: g = 'C'
    else: g = 'B'
    why = []
    if n <= 1: why.append('연결된 미국 직업 %d개' % n)
    if d > .2: why.append('두 연구 차이 %d%%p' % round(d * 100))
    if rw > 30: why.append('계산 방식에 따라 순위가 %d계단 흔들림' % rw)
    if side: why.append('다른 계산 방식 대부분이 더 ' + ('높게' if side == 'up' else '낮게') + ' 봄')
    grades[g] += 1
    out['sm'][c] = {'g': g, 'lo': round(lo * 100), 'hi': round(hi * 100), 'rk': rk, 'r0': R0[c],
                    'n': n, 'e': round(E0[c] * 100), 'il': round(IL[c] * 100), 'side': side, 'why': why}
emp_by = collections.Counter()
for c in CODES: emp_by[out['sm'][c]['g']] += EMPK.get(c, 0)
tot = sum(emp_by.values())

# ── 6) 주간 소식 독립 검토 ─────────────────────────────
rev = []
for f in sorted(glob.glob(os.path.join(ROOT, 'review', '20*-W*.json'))):
    if f.endswith('.queue.json'): continue
    j = json.load(open(f)); it = j.get('items', [])
    cnt = collections.Counter(x.get('v') for x in it)
    rev.append({'week': j.get('week'), 'by': j.get('by'), 'ok': cnt['ok'], 'fix': cnt['fix'], 'hold': cnt['hold'],
                'pass': round(cnt['ok'] / max(1, len(it)), 3)})


# ── 신뢰도 %: 2,000번 다시 계산했을 때 화면이 말하는 물때 단계(발목·무릎·허리·가슴·목까지)가 그대로인 비율
STG = [0, .2, .35, .5, .65]
# 단계 경계에 걸린 직업(신뢰도 80% 미만, 다음으로 많이 나온 단계가 바로 옆)은 두 단계 사이의 신체 부위로 부른다(2026-11-02 운영자 결정)
ZONE = ['정강이', '허벅지', '명치', '어깨']   # 발목~무릎, 무릎~허리, 허리~가슴, 가슴~목까지
def zone(x, s0):
    x['s'] = s0; x['cd'] = x['conf']
    a = x.get('alt')
    if x['conf'] < 80 and a and abs(a[0] - s0) == 1:
        lo = min(a[0], s0); x['zone'] = lo; x['zn'] = ZONE[lo]; x['cd'] = x['conf'] + a[1]
    if x['cd'] < 80: x['cd'] = None   # 80% 미만은 화면에 신뢰도 숫자를 내지 않는다
def stg(v): return sum(1 for t in STG[1:] if v >= t)
for c in CODES:
    v = occ(c, 2026); s0 = stg(v)
    cnt = collections.Counter(stg(v * r) for r in draws[c])
    out['sm'][c]['conf'] = round(cnt[s0] / N * 100)
    alt = [(k, n) for k, n in cnt.most_common() if k != s0]
    if alt: out['sm'][c]['alt'] = [alt[0][0], round(alt[0][1] / N * 100)]   # 다음으로 많이 나온 단계(0~4)와 비율
    zone(out['sm'][c], s0)
out['mid'] = {}
for j in M['jobs']:
    sm = [(c, EMPK.get(c, 0)) for c, _, _ in j['smalls'] if c in SM]
    if not sm: continue
    vm = min(.99, j['cal'] * sum(x * pv(r, 2026) for r, x in j['w41'].items())); s0 = stg(vm)
    z = sum(T0[c] * e for c, e in sm) or 1
    cnt = collections.Counter(stg(vm * sum(T0[c] * draws[c][i] * e for c, e in sm) / z) for i in range(N))
    out['mid'][j['code']] = {'conf': round(cnt[s0] / N * 100)}
    alt = [(k, n) for k, n in cnt.most_common() if k != s0]
    if alt: out['mid'][j['code']]['alt'] = [alt[0][0], round(alt[0][1] / N * 100)]
    zone(out['mid'][j['code']], s0)
conf_all = round(sum(out['sm'][c]['conf'] * EMPK.get(c, 0) for c in CODES) / sum(EMPK.get(c, 0) for c in CODES))
_w = [(out['sm'][c]['cd'], EMPK.get(c, 0)) for c in CODES]
conf_disp = round(sum((cd if cd is not None else out['sm'][c]['conf']) * e for (cd, e), c in zip(_w, CODES)) / sum(e for _, e in _w))
zones = sum(1 for c in CODES if 'zone' in out['sm'][c]); hidden = sum(1 for c in CODES if out['sm'][c]['cd'] is None)
out['summary'] = {
    'conf_all': conf_all, 'conf_disp': conf_disp, 'zones': zones, 'hidden': hidden, 'conf_def': '계산 방식(두 연구 비중, 사람·AI 판정, 직업 연결 방식, 미국 고용 가중)을 바꿔 2,000번 다시 계산했을 때 물때 단계가 그대로인 비율. 사이트 전체는 취업자 가중 평균',
    'agree': {k: {'rho': v[0], 'n': v[1]} for k, v in agree.items()},
    'external': {k: {'rho': v[0], 'n': v[1]} for k, v in extc.items()},
    'grades': dict(grades), 'grades_emp_share': {k: round(v / tot, 3) for k, v in emp_by.items()},
    'median_band_pp': round(st.median(out['sm'][c]['hi'] - out['sm'][c]['lo'] for c in CODES), 1),
    'route_gap_pp': {'median_abs': round(st.median(abs(v) for v in gap.values()) * 100, 1),
                     'over10': sum(1 for v in gap.values() if abs(v) > .10), 'n': len(gap)},
    'review': rev,
    'rules': {'A': '연결된 미국 직업 3개 이상, 두 연구 차이 12%p 이하, 계산 방식을 바꿔도 순위가 15계단 안에서 움직임', 'C': '연결된 미국 직업 1개 이하, 또는 두 연구 차이 20%p 초과, 또는 순위가 30계단 넘게 흔들림', 'B': '그 밖'},
}
json.dump(out, open(os.path.join(ROOT, 'validation.json'), 'w'), ensure_ascii=False, separators=(',', ':'))

# 운영자용 보고서
L = ['# 숫자 신뢰도 점검 결과', '', f"기준 주: {out['at']} · 무작위 조합 {N}회 · 만든 도구: tools/validate.py", '', '## 출처 일치·경로 민감도 (소분류 순위 상관 ρ)', '']
lab = {'eloundou_vs_ilo': 'Eloundou 외 β vs ILO', 'model_vs_human': 'GPT-4 판정 vs 사람 판정(Eloundou 원자료)', 'our_map_vs_official': '우리 연결표 vs 공식 경로(KSCO→ISCO→O*NET)', 'repro_check': '재현 확인(공개값 vs 이 스크립트)'}
for k, v in agree.items(): L.append(f'- {lab[k]}: ρ={v[0]} (n={v[1]})')
L += ['', '## 외부 지표와 순위 상관', ''] + [f'- {k}: ρ={v[0]} (n={v[1]})' for k, v in extc.items()]
s = out['summary']
L += ['', f"## 신뢰도(단계 일치율) — 사이트 전체 {conf_all}%", '', out['summary']['conf_def'], '', '## 근거 등급', '', f"- A {grades['A']} · B {grades['B']} · C {grades['C']} (취업자 비중 A {s['grades_emp_share'].get('A',0):.0%} · B {s['grades_emp_share'].get('B',0):.0%} · C {s['grades_emp_share'].get('C',0):.0%})",
      f"- 범위 폭 중앙값 {s['median_band_pp']}%p · 연결 경로를 바꿨을 때 차이 중앙값 {s['route_gap_pp']['median_abs']}%p, 10%p 넘는 소분류 {s['route_gap_pp']['over10']}/{s['route_gap_pp']['n']}", '',
      '| 코드 | 직업 | 2026 | 범위 | 순위(범위) | 등급 | 신뢰도 | 이유 |', '| --- | --- | --- | --- | --- | --- | --- | --- |']
for c in sorted(CODES, key=lambda c: (out['sm'][c]['g'] != 'C', -(out['sm'][c]['hi'] - out['sm'][c]['lo']))):
    x = out['sm'][c]
    L.append(f"| {c} | {NAME.get(c, '')} | {round(occ(c, 2026) * 100)}% | {x['lo']}~{x['hi']}% | {x['r0']} ({x['rk'][0]}~{x['rk'][1]}) | {x['g']} | {x['conf']}% | {', '.join(x['why'])} |")
L += ['', '## 연결 경로 차이가 큰 소분류(공식 경로 − 우리 연결표, β)', '']
for c, v in sorted(gap.items(), key=lambda kv: -abs(kv[1]))[:15]: L.append(f'- {c} {NAME.get(c, "")}: {v * 100:+.0f}%p')
L += ['', '## 주간 소식 독립 검토', ''] + [f"- {r['week']} ({r['by']}): 확인 {r['ok']} · 수정 {r['fix']} · 보류 {r['hold']} → 그대로 통과 {r['pass']:.0%}" for r in rev]
os.makedirs(os.path.join(ROOT, 'reports'), exist_ok=True)
open(os.path.join(ROOT, 'reports', 'validation.md'), 'w').write('\n'.join(L) + '\n')
print(json.dumps(out['summary'], ensure_ascii=False, indent=1))
