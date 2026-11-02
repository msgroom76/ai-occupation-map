"""예측 사전 공개: 지금 사이트가 내놓는 직업별 값(2026·2027·2028·2030)을 날짜와 함께 고정한다 → forecasts/<날짜>.json, forecasts/index.json
나중에 실제 자료(Anthropic 경제지수 갱신, 지역별고용조사, 채용공고)가 나오면 이 파일과 비교해 채점한다(tools/score_forecast.py, 다음 단계).
한 번 만든 스냅샷은 고치지 않는다. 내용의 SHA-256을 index.json에 남기고, git 커밋 시각이 공개 시각의 증거가 된다.
분기마다 한 번(1·4·7·10월 첫 주 지수 발표 뒤) 실행. 사용: python3 tools/snapshot_forecast.py [YYYY-MM-DD[-rN]] ["모델을 고친 이유"]
같은 날 모델(연결표 등)을 고쳤으면 -r2처럼 새 이름으로 하나 더 남긴다. 앞 기록은 그대로 둔다.
"""
import json, math, os, sys, hashlib, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = json.load(open(os.path.join(ROOT, 'city_meta.json')))
IDX = json.load(open(os.path.join(ROOT, 'index.json')))
wk = IDX['weeks'][-1]; ADJ = wk.get('adj', {})
if isinstance(ADJ, str): ADJ = eval(ADJ)
RP = M['R']; YEARS = [2026, 2027, 2028, 2030]
def pv(r, y): return RP[r][2] / (1 + math.exp(-RP[r][1] * (y - RP[r][0] + ADJ.get(r, 0))))
def occ(w, cal, y): return min(.99, cal * sum(x * pv(r, y) for r, x in w.items()))
date = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
D = os.path.join(ROOT, 'forecasts'); os.makedirs(D, exist_ok=True)
f = os.path.join(D, date + '.json')
if os.path.exists(f): sys.exit(f'{f} 이미 있음 — 스냅샷은 고치지 않는다')
V = json.load(open(os.path.join(ROOT, 'validation.json'))) if os.path.exists(os.path.join(ROOT, 'validation.json')) else {'sm': {}}
vals = {'mid': {j['code']: [round(occ(j['w41'], j['cal'], y) * 100, 1) for y in YEARS] for j in M['jobs']},
        'sm': {c: [round(occ(s['w'], s['cal'], y) * 100, 1) for y in YEARS] for c, s in M['sm'].items()},
        'band2026': {c: [v['lo'], v['hi']] for c, v in V['sm'].items()}}
body = json.dumps(vals, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
sha = hashlib.sha256(body.encode()).hexdigest()
note = sys.argv[2] if len(sys.argv) > 2 else ''
snap = {'date': date, 'note': note, 'week': wk['week'], 'years': YEARS, 'unit': '% (AI 노출도)', 'sha256': sha,
        'how': '사이트와 같은 계산(city_meta.json 곡선 + 그 주 주간 조정). band2026은 validation.json의 10~90% 범위.',
        'score_plan': '방향(오름/내림)과 순위 상관(스피어만)을 함께 채점. 비교 대상: Anthropic 경제지수 갱신(실제 사용), 지역별고용조사 직업별 취업자·임금, 채용공고 수.',
        'values': vals}
json.dump(snap, open(f, 'w'), ensure_ascii=False, separators=(',', ':'))
ix = os.path.join(D, 'index.json'); L = json.load(open(ix)) if os.path.exists(ix) else []
L.append({'date': date, 'note': note, 'week': wk['week'], 'file': f'/forecasts/{date}.json', 'sha256': sha, 'n': len(vals['sm']) + len(vals['mid'])})
json.dump(L, open(ix, 'w'), ensure_ascii=False, indent=1)
print(f, sha)
