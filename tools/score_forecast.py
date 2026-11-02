"""예측 채점: forecasts/criteria.json(채점 전에 고정한 기준)대로 예측 기록을 실제 자료와 비교한다 → forecasts/score-<기록>-<자료날짜>.json
사용:
  python3 tools/score_forecast.py --snap 2026-11-02-r2 --usage 새_job_exposure.csv --usage-date 2027-03-15 \
         [--usage-old pipeline/inputs/dl2/job_exposure.csv --usage-old-date 2026-03-15] \
         [--lfs-old pipeline/inputs/dl_lfs/occ_2025h2.json --lfs-new 새_occ.json] [--dry]
  --usage: Anthropic 경제지수 직업별 관측 노출(occ_code, observed_exposure 열). 미국 SOC → 한국 소분류는 사이트와 같은 연결표·미국 고용 가중.
  --dry: 결과를 화면에만 찍고 파일로 남기지 않는다(도구 점검용).
"""
import argparse, csv, json, os, sys, statistics as st, collections, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
for a in ('--snap', '--usage', '--usage-date', '--usage-old', '--usage-old-date', '--lfs-old', '--lfs-new'): ap.add_argument(a)
ap.add_argument('--dry', action='store_true'); A = ap.parse_args()
C = json.load(open(os.path.join(ROOT, 'forecasts', 'criteria.json')))
S = json.load(open(os.path.join(ROOT, 'forecasts', A.snap + '.json')))
B = json.load(open(os.path.join(ROOT, 'forecasts', A.snap + '.baseline.json')))['sm']
YEARS = S['years']; F = S['values']['sm']

ns = {}; exec(open(os.path.join(ROOT, 'pipeline', 'scripts', 'soc_map_small.py')).read(), ns); small_of = ns['small_of']
EMP = {}
for r in csv.DictReader(open(os.path.join(ROOT, 'pipeline/inputs/gpts/national_May2021_dl.csv'), encoding='utf-8-sig')):
    if r['O_GROUP'] == 'detailed':
        try: EMP[r['OCC_CODE']] = float(r['TOT_EMP'].replace(',', ''))
        except ValueError: pass
def emp(soc): return EMP.get(soc) or next((v for k, v in EMP.items() if k[:6] == soc[:6]), 1000.0)
def usage(fn):
    d = collections.defaultdict(lambda: [0, 0])
    for r in csv.DictReader(open(fn)):
        soc = r['occ_code'][:7]; k = small_of(soc)
        if k: d[k][0] += float(r['observed_exposure']) * emp(soc); d[k][1] += emp(soc)
    return {k: a / b for k, (a, b) in d.items() if b}
def yf(s): d = datetime.date.fromisoformat(s); return d.year + (d.timetuple().tm_yday - 1) / 365
def at(vals, y):  # 기록의 연도별 값 사이를 직선으로 잇는다
    if y <= YEARS[0]: return vals[0]
    for (y0, v0), (y1, v1) in zip(zip(YEARS, vals), zip(YEARS[1:], vals[1:])):
        if y <= y1: return v0 + (v1 - v0) * (y - y0) / (y1 - y0)
    return vals[-1]
def rank(d): s = sorted(d, key=lambda c: -d[c]); return {c: i + 1 for i, c in enumerate(s)}
def rho(a, b):
    ks = [k for k in a if k in b]; ra, rb = rank({k: a[k] for k in ks}), rank({k: b[k] for k in ks})
    m = (len(ks) + 1) / 2; num = sum((ra[k] - m) * (rb[k] - m) for k in ks)
    den = (sum((ra[k] - m) ** 2 for k in ks) * sum((rb[k] - m) ** 2 for k in ks)) ** .5
    return round(num / den, 3), len(ks)

act = usage(A.usage); y = yf(A.usage_date)
ours = {c: at(v, y) for c, v in F.items()}
r_ours, n = rho(ours, act); r_base, _ = rho(B, act)
TH = C['pass']['rho_min']; MG = C['pass'].get('margin', 0)
d = r_ours - r_base; cmp = '낫다' if d >= MG else '못하다' if d <= -MG else '차이 없음'
level = '불합격' if r_ours < TH or cmp == '못하다' else '합격' if cmp == '낫다' else '합격(추가 가치 없음)'
res = {'snap': A.snap, 'snap_sha256': S['sha256'], 'criteria_sha256': C.get('sha256'), 'usage': os.path.basename(A.usage), 'usage_date': A.usage_date,
       'scored_at': datetime.date.today().isoformat(), 'n': n,
       'rank_corr': {'ours': r_ours, 'baseline': r_base, 'threshold': TH, 'margin': MG, 'vs_baseline': cmp},
       'pass': level != '불합격', 'level': level,
       'verdict': f'{level} (순위 상관 {r_ours}, 기준 {TH} 이상 · 기준선 {r_base}와 비교해 {cmp})'}
# 방향 일치(평균 대비): 예측이 '평균보다 많이 오른다'고 한 직업이 실제로도 평균보다 많이 올랐나
if A.usage_old:
    old = usage(A.usage_old); y0 = yf(A.usage_old_date or S['date'][:10])
    ks = [c for c in ours if c in act and c in old]
    dp = {c: ours[c] - at(F[c], y0) for c in ks}; da = {c: act[c] - old[c] for c in ks}
    mp, ma = st.mean(dp.values()), st.mean(da.values())
    hit = sum(1 for c in ks if (dp[c] > mp) == (da[c] > ma))
    res['direction'] = {'hit': hit, 'n': len(ks), 'rate': round(hit / len(ks), 3), 'reference': 0.5,
                        'say': f'평균보다 많이 오른다고 본 직업과 실제로 평균보다 많이 오른 직업이 {len(ks)}개 중 {hit}개 일치'}
# 상·하위 20% 그룹 비교(관찰, 합격 판정에 쓰지 않음)
v26 = {c: v[0] for c, v in F.items()}; order = sorted(v26, key=lambda c: -v26[c]); k = len(order) // 5
top, bot = order[:k], order[-k:]
grp = {}
if A.usage_old:
    g = lambda L: st.mean(da[c] for c in L if c in da)
    grp['usage_change_pp'] = {'top20': round(g(top) * 100, 2), 'bottom20': round(g(bot) * 100, 2), 'gap': round((g(top) - g(bot)) * 100, 2)}
if A.lfs_old and A.lfs_new:
    L0 = {r['code']: r['k'] for r in json.load(open(A.lfs_old))['rows'] if r['lv'] == 3}
    L1 = {r['code']: r['k'] for r in json.load(open(A.lfs_new))['rows'] if r['lv'] == 3}
    def growth(L):
        a = sum(L0.get(c, 0) for c in L); b = sum(L1.get(c, 0) for c in L); return (b / a - 1) * 100 if a else None
    gt, gb = growth(top), growth(bot)
    grp['employment_growth_pct'] = {'top20': round(gt, 2), 'bottom20': round(gb, 2), 'gap': round(gt - gb, 2),
                                    'note': '관찰만. 경기·인구·표본 오차가 커서 AI 효과로 해석하지 않는다'}
res['groups'] = grp
print(json.dumps(res, ensure_ascii=False, indent=1))
if not A.dry:
    out = os.path.join(ROOT, 'forecasts', f'score-{A.snap}-{A.usage_date}.json')
    json.dump(res, open(out, 'w'), ensure_ascii=False, indent=1); print(out)
