"""조직 리포트 한 번에 만들기. 저장소 루트에서: python3 tools/build_report.py reports/<회사>.json

하는 일(순서대로)
  1. 계산: org_report.run → reports/out/<id>/metrics.json
  2. 그림: build_lineup.py(직무 군상), report_charts.py(두 집단·업무·업종 구성·동종사)
  3. 초안: reports/out/<id>/report.md  — 숫자가 들어가는 표·문장·그림 설명·부록은 모두 계산 결과에서 바로 쓴다.
           해석이 필요한 자리(핵심 메시지, 시사점, 로드맵)는 <!-- 작성: … --> 표시와 함께 수치 근거만 깔아 둔다.
  4. 점검: reports/out/<id>/checks.json — 인원 합계, 동종사 시점, 같은 직업 분류로 묶인 직무, 급여 기준 등.

회사 설정 파일(reports/<id>.json)에 org_report 입력 외에 더 넣을 수 있는 것(모두 선택)
  "office": ["exec", ...]            두 집단 중 첫 집단(사무·기술 등)에 넣을 직무 id
  "groups": ["사무·기술", "현장"]      두 집단 이름
  "readers": "공동대표, 경영진, 인사 책임자"
  "payroll_note": "2025년 급여 총액(감사보고서)"   payroll_actual의 근거. 없으면 '추정'으로 적는다
  "op_profit": 13.5                   최근 영업이익(억 원) — 인건비 규모와 비교 문장에 쓴다
  "facts": {"finance": {"title", "head": [...], "rows": [[...]], "note"},
            "headcount": [["출처","인원","시점","범위"], ...], "headcount_note": "...",
            "bullets": ["**사업 구성**: ...", ...],
            "ai_moves": [["시기","내용","관련 직무"], ...], "ai_note": "..."}
  "sources": ["[제목](URL)", ...]
동종사 파일(reports/<id>_peers.json): {"industry", "metric"?, "peers": [{"name","rev"(백만 원),"op","n"?,"biz"?,"ai"?,"n_note"?,"self"?}], "note"?}
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from org_report import run

TIER = ['낮음', '보통', '상당', '높음', '매우 높음']
SHORT = {'정보 처리하기': '정보 처리', '창의적으로 생각하기': '창의적 사고', '결정·문제 풀기': '문제 해결', '정보 찾아 모으기': '정보 수집',
         '동료와 소통': '협업·소통', '지휘하기': '지휘·조율', '팔고 설득하기': '판매·설득', '수량·비용 가늠': '수량 산정', '컴퓨터로 일하기': '컴퓨터 작업',
         '남의 일 조율': '작업 조율', '장비·재료 점검': '장비 점검', '풀어 설명하기': '안내·설명', '대중 앞에서': '대외 응대'}
MJN = {'1': '관리자', '2': '전문가', '3': '사무', '4': '서비스', '5': '판매', '6': '농림어업', '7': '기능원', '8': '장치·기계 조작', '9': '단순노무'}
US_NAME = {'mgmt': '관리직', 'bizfin': '경영·재무직', 'cmp': '컴퓨터·수학직', 'eng': '엔지니어', 'sci': '과학직', 'legal': '법률직', 'arts': '예술·미디어직',
           'sales': '판매직', 'office': '사무직', 'prod': '생산직', 'trans': '운송직', 'inst': '설치·정비직', 'food': '음식 서비스직', 'cons': '건설직', 'svc': '서비스직'}


IND_NAME = {'C': '제조업', 'F': '건설업', 'G': '도소매업', 'H': '운수·창고업', 'I': '숙박·음식점업', 'J': '정보통신업', 'K': '금융·보험업', 'L': '부동산업',
            'M': '전문·과학·기술서비스업', 'N': '사업지원서비스업', 'P': '교육서비스업', 'Q': '보건·사회복지업', 'R': '예술·스포츠·여가업', 'S': '협회·기타 개인서비스업'}
import re
def _last(w):
    w = re.sub(r'\([^()]*\)$', '', str(w).strip()).strip()
    for ch in reversed(w):
        if '가' <= ch <= '힣': return (ord(ch) - 0xAC00) % 28 != 0
        if ch.isdigit(): return ch in '0136789'
        if ch == '%': return False
        if ch.isalpha(): return ch.lower() in 'lmnr'
    return False
def j(w, a, b):
    """받침에 맞는 조사: j('회사', '가', '이') → '회사가'"""
    return f'{w}{b if _last(w) else a}'
def nm(r): return r['name'] if '(' in r['name'] else r['name']

def p(x, d=1): return f'{x * 100:.{d}f}%'
def r0(x): return f'{x * 100:.0f}%'
def num(x): return f'{x:,.0f}' if abs(x) >= 100 else f'{x:,.1f}'
def tbl(head, rows): return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows])
def tk(t): return SHORT.get(t['name'], t['name'])
TODO = lambda s: f'<!-- 작성: {s} -->'

def main(path):
    C = json.load(open(path)); cid = C['id']; od = f'reports/out/{cid}'
    M = run(path); o = M['org']; R = M['roles']; name = C['name']; N = o['n']
    office = set(C.get('office') or []); GL = C.get('groups') or ['사무·기술', '현장']
    subprocess.run([sys.executable, 'tools/build_lineup.py', f'{od}/metrics.json'], check=True)
    cmd = [sys.executable, 'tools/report_charts.py', f'{od}/metrics.json']
    if office: cmd += [','.join(sorted(office)), ','.join(GL)]
    subprocess.run(cmd, check=True)
    IB = json.load(open('reports/industry_bench.json'))
    pp = f'reports/{cid}_peers.json'; P = json.load(open(pp)) if os.path.exists(pp) else None
    ind = IB['industry'][P['industry']] if P else None
    indn = IND_NAME.get(P['industry'][0], P['industry'].split('(')[0].split('. ')[-1].replace(' ', '')) if P else ''
    UK = json.load(open('us_kr.json')); PR = json.load(open('protect.json'))
    checks = []
    # ---------- 집계 ----------
    G = []
    if office:
        for nm, S in ((GL[0], [r for r in R if r['id'] in office]), (GL[1], [r for r in R if r['id'] not in office])):
            n = sum(r['n'] for r in S); f = sum(r['fte'] for r in S); f30 = sum(r['fte30'] for r in S)
            G.append(dict(name=nm, n=n, fte=f, fte30=f30, e=f / n if n else 0, e30=f30 / n if n else 0, ids=[r['name'] for r in S]))
    big = max(R, key=lambda r: r['fte'])
    same = {}
    for r in R: same.setdefault(r['code'], []).append(r['name'])
    same = [v for v in same.values() if len(v) > 1]
    if sum(r['n'] for r in R) != C.get('headcount', N): checks.append(f"직무 인원 합계 {sum(r['n'] for r in R)}명 ≠ headcount {C.get('headcount')}명")
    if same: checks.append('같은 직업 분류로 묶여 같은 값이 나오는 직무: ' + ' / '.join('·'.join(v) for v in same))
    paybasis = C.get('payroll_note') or ('실제 급여 총액' if C.get('payroll_actual') else '직종별 평균 임금으로 추정')
    if C.get('payroll_actual') and not C.get('payroll_note'): checks.append('payroll_note가 없어 인건비 근거를 일반 문구로 적었다. 실제/추정 여부를 확인할 것')
    hi = sorted(R, key=lambda r: -r['e26']); lo = hi[-1]
    out = []
    w = out.append
    # ---------- 표지 ----------
    w(f'# {name} AI 직무 노출도 진단 보고서\n')
    w('조직 진단 · 샘플 보고서 · 발행 AI 점령 지도(포스트오피스)\n')
    w(f"![{name.replace('(주)', '')} {len(R)}개 직무의 AI 노출도를 인물별 수위로 나타낸 그림. {hi[0]['name']} {r0(hi[0]['e26'])}가 가장 높고 {lo['name']} {r0(lo['e26'])}가 가장 낮다](lineup.png)\n")
    w('그림 1. 직무별 AI 노출도(2026). 인물별 음영 높이는 해당 직무 업무 중 AI가 수행 가능한 비중이다. 노출 수준: 낮음(20% 미만) · 보통(20~35%) · 상당(35~50%) · 높음(50~65%) · 매우 높음(65% 이상).\n')
    w(f"**진단 범위** · 대상: {name} 전 직무({N:,}명, {len(R)}개 직무, 추정 구성) · 기준일: {C.get('asof')} · 전망: 2030년 · 대상 독자: {C.get('readers', '경영진, 인사 책임자')}\n")
    # ---------- Executive Summary ----------
    w('## Executive Summary\n')
    cmp_ind = f"{indn} 평균({r0(ind['e26'])})" if ind else ''
    w(TODO(f"핵심 메시지 2~4문장. 근거: 노출도 {p(o['e26'])}" + (f" vs {cmp_ind}" if ind else '') + f", 보완형 {r0(1 - o['sub'])}, 결론의 축(이 회사에서 AI의 재무적 가치가 나오는 곳)") + '\n')
    w('표 1. 핵심 지표\n')
    rows = [['조직 AI 노출도(2026)', f"{p(o['e26'])} ({TIER[o['stage']]})", (f"{indn} {p(ind['e26'])}, " if ind else '') + f"국내 취업자 {p(o['kr26'])}"],
            ['조직 AI 노출도(2030)', f"{p(o['e30'])} ({TIER[o['stage30']]})", (f"{indn} {p(ind['e30'])}" if ind else f"국내 취업자 {p(o['kr30'])}")],
            ['AI 수행 가능 업무량', f"{o['fte']:,.0f} FTE (2030년 {o['fte30']:,.0f} FTE)" if o['fte'] >= 100 else f"{o['fte']:.1f} FTE (2030년 {o['fte30']:.1f} FTE)", f'총 {N:,}명'],
            ['해당 업무 인건비 규모', f"연 약 {num(o['cost'])}억 원", f"{paybasis} {num(o['payroll'])}억 원의 {r0(o['cost'] / o['payroll'])}"]]
    rows += C.get('kpi_rows', [])
    w(tbl(['지표', name.replace('(주)', ''), '비교 기준'], rows) + '\n')
    w('주: FTE는 AI가 수행 가능한 업무 시간을 정규 인력 수로 환산한 값이다. 인건비 규모는 절감 가능액이 아니라 해당 업무에 투입되는 비용이다.\n')
    w('**주요 발견(수치 초안 — 다듬어 쓸 것)**\n')
    fs = []
    if G: fs.append(f"{G[0]['name']} {G[0]['n']:,}명의 노출도는 {r0(G[0]['e'])}(2030년 {r0(G[0]['e30'])}), {G[1]['name']} {G[1]['n']:,}명은 {r0(G[1]['e'])}(2030년 {r0(G[1]['e30'])})다. 전체 {o['fte']:,.1f} FTE 중 {G[0]['fte']:,.1f} FTE({r0(G[0]['fte'] / o['fte'])})가 {G[0]['name']}에 있다.")
    fs.append(f"단일 직무로는 {big['name']} {big['n']:,}명에 {big['fte']:,.1f} FTE, 전체의 {r0(big['fte'] / o['fte'])}가 있고 그 {r0(1 - big['sub'])}가 보완형이다.")
    hs = sorted([r for r in R if r['sub'] >= .45], key=lambda r: -r['sub'])
    fs.append(f"노출 업무의 {r0(o['sub'])}가 대체형이다." + (' 대체형 비중이 높은 직무: ' + ', '.join(f"{r['name']}({r0(r['sub'])})" for r in hs[:5]) + '.' if hs else ''))
    t0 = o['tasks'][0]; fs.append(f"단일 업무로는 '{tk(t0)}'" + ('이' if _last(tk(t0)) else '가') + f" {t0['fte']:,.1f} FTE로 가장 크다({t0['type']}).")
    if C.get('op_profit'): fs.append(f"AI 수행 가능 업무의 인건비(연 약 {num(o['cost'])}억 원)는 최근 영업이익({num(C['op_profit'])}억 원)의 {o['cost'] / C['op_profit']:.1f}배다.")
    w('\n'.join(f'{i + 1}. {s}' for i, s in enumerate(fs)) + '\n')
    w('**의사결정 사항**\n'); w(TODO('경영진이 정할 질문 3개, 각각 해당 인원·FTE를 괄호로') + '\n')
    # ---------- 1. 회사 현황 ----------
    F = C.get('facts', {})
    w('## 1. 회사 현황\n'); w(TODO('한두 문장 요약: 회사의 현재 국면') + '\n')
    if F.get('finance'):
        f = F['finance']; w(f"표 2. {f.get('title', '재무 현황(단위: 억 원)')}\n"); w(tbl(f['head'], f['rows']) + '\n')
        if f.get('note'): w(f['note'] + '\n')
    else: checks.append('facts.finance 없음: 재무 표를 비워 둠')
    if F.get('bullets'): w('\n'.join('- ' + b for b in F['bullets']) + '\n')
    if F.get('headcount'):
        w('표 3. 인원 자료 교차 확인\n'); hc = F['headcount']; w(tbl(hc[0], hc[1:]) + '\n')
    w((F.get('headcount_note') or f"본 진단의 인원 기준: {C.get('basis', f'{N}명')}.") + '\n')
    if F.get('ai_moves'):
        w('표 4. AI·디지털 도입 공개 이력\n'); am = F['ai_moves']; w(tbl(am[0], am[1:]) + '\n')
    if F.get('ai_note'): w(F['ai_note'] + '\n')
    # ---------- 2. 직무별 ----------
    w('## 2. 직무별 AI 노출 현황\n')
    nhi = sum(1 for r in R if r['stage'] >= 3); nlo = sum(1 for r in R if r['stage'] == 0)
    w(f"{len(R)}개 직무 중 {nhi}개가 '높음' 이상" + (f", {nlo}개가 '낮음'" if nlo else '') + f"이다. 가장 높은 직무는 {hi[0]['name']}({r0(hi[0]['e26'])}), 가장 낮은 직무는 {lo['name']}({r0(lo['e26'])})이다. " + TODO('직무 간 차이의 해석 한 문장') + '\n')
    w('표 5. 직무별 AI 노출도와 주요 노출 업무\n')
    w(tbl(['직무', '인원', '2026', '2030', '노출 수준', '대체형 비중', '주요 노출 업무'],
          [[r['name'], f"{r['n']:,}", r0(r['e26']), r0(r['e30']), TIER[r['stage']], r0(r['sub']), ', '.join(tk(t) for t in r['tasks'][:2])] for r in R]) + '\n')
    note = '주: 인원은 추정치. 대체형 비중은 노출 업무 중 AI가 독자적으로 완결하기 쉬운 업무(문서화·정보 처리·행정 등)의 비중.'
    if same: note += ' ' + ', '.join(j(v[0], '와', '과') + ' ' + '·'.join(v[1:]) for v in same) + '는 대응 직업 분류가 같아 같은 값으로 산출됨.'
    w(note + '\n')
    if G:
        w(f"![{G[0]['name']} {G[0]['n']:,}명과 {G[1]['name']} {G[1]['n']:,}명의 인원 대비 AI 수행 가능 업무량(2026·2030, FTE)](chart_groups.png)\n")
        w(f"그림 2. 직무군별 인원과 AI 수행 가능 업무량. {G[0]['name']} {G[0]['fte']:,.1f} FTE(2030년 {G[0]['fte30']:,.1f} FTE), {G[1]['name']} {G[1]['fte']:,.1f} FTE(2030년 {G[1]['fte30']:,.1f} FTE).\n")
    w('**해석.** ' + TODO('대체형 비중이 높은 직무, 2030년에 크게 오르는 직무의 의미') + '\n')
    # ---------- 3. 동종업계 ----------
    w('## 3. 동종업계·업종 비교\n'); w(TODO('동종사 대비 이 회사의 위치 한두 문장') + '\n')
    if P:
        Q = P['peers']; w('표 6. 동종·유관 기업 비교(단위: 억 원)\n')
        w(tbl(['기업', '사업', '매출', '영업이익률', '인원', 'AI 동향'],
              [[q['name'], q.get('biz', '–'), f"{q['rev'] / 100:,.0f}", f"{q['op'] / q['rev'] * 100:+.1f}%".replace('+', '') if q['op'] >= 0 else f"−{abs(q['op'] / q['rev'] * 100):.1f}%",
                (f"{q['n']:,}" if q.get('n') else '확인 안 됨') + (f"({q['n_note']})" if q.get('n_note') else ''), q.get('ai', '확인 안 됨')] for q in Q]) + '\n')
        w((P.get('note') or '출처: 각 사 감사보고서·사업보고서.') + (' 인원과 매출의 시점·기준이 달라 1인당 매출은 계산하지 않았다.' if P.get('metric') == 'margin' else '') + '\n')
        self_ = next((q for q in Q if q.get('self')), None); others = [q for q in Q if not q.get('self')]
        w('![동종사의 매출 규모와 영업이익률](chart_peers.png)\n' if P.get('metric') == 'margin' else '![기준 시점이 같은 기업의 1인당 매출](chart_peers.png)\n')
        if self_ and P.get('metric') == 'margin':
            mg = sorted(Q, key=lambda q: -q['op'] / q['rev']); rank = mg.index(self_) + 1
            w(f"그림 3. 매출 규모와 영업이익률. {self_['name']}의 매출은 {self_['rev'] / 100:,.0f}억 원(나머지 {len(others)}개사 합계 {sum(q['rev'] for q in others) / 100:,.0f}억 원), 영업이익률은 {len(Q)}개사 중 {rank}위다.\n")
        else: w('그림 3. ' + TODO('그림 설명') + '\n')
        if ind:
            mix = o['mix']; im = ind['mix']
            diffs = sorted(set(mix) | {k for k, v in im.items() if v > .02}, key=lambda k: -abs(mix.get(k, 0) - im.get(k, 0)))[:2]
            dtxt = ', '.join(f"{MJN[k]} {r0(mix.get(k, 0))}(업종 {r0(im.get(k, 0))})" for k in diffs)
            rel = '높다' if o['e26'] > ind['e26'] + .01 else '낮다' if o['e26'] < ind['e26'] - .01 else '비슷하다'
            w(f"**업종 평균과의 비교.** {indn} 취업자의 직업 구성으로 계산한 업종 평균 노출도는 {p(ind['e26'])}(2030년 {p(ind['e30'])})로, {name.replace('(주)', '')}({p(o['e26'])}, 2030년 {p(o['e30'])})보다 {'낮다' if rel == '높다' else '높다' if rel == '낮다' else '비슷한 수준이다'}. 구성 차이가 가장 큰 대분류는 {dtxt}이다. " + TODO('구성 차이가 노출도 차이를 어떻게 설명하는지') + '\n')
            w(f"![직업 대분류별 인원 비중: {j(name.replace('(주)', ''), '와', '과')} {indn} 평균](chart_mix.png)\n")
            w(f'그림 4. 직업 구성 비교(인원 비중, %). 업종 평균은 국가데이터처 지역별고용조사 2025년 하반기.\n')
    else: checks.append('동종사 파일 없음: 3장 표·그림 3·4를 만들지 못함')
    w('**시사점**\n'); w(TODO('동종사 동향에서 나오는 시사점 3개') + '\n')
    # ---------- 4. 경영 ----------
    w('## 4. 경영 시사점\n')
    w(TODO('이 회사에서 AI의 재무적 가치가 어디서 나오는지 한 단락') + (f" (근거: 인건비 규모 {num(o['cost'])}억 원, 영업이익 {num(C['op_profit'])}억 원)" if C.get('op_profit') else '') + '\n')
    T = o['tasks'][:3]
    w('![업무별 AI 수행 가능 업무량(인원 가중, FTE)](chart_tasks.png)\n')
    w('그림 5. 업무별 AI 수행 가능 업무량(인원 가중, FTE). 진한 막대는 대체형, 옅은 막대는 보완형. ' + ', '.join(f"{tk(t)} {t['fte']:,.1f} FTE" for t in T) + ' 순.\n')
    lev = sorted(R, key=lambda r: -r['fte'])[:3]
    w(TODO('4.1~4.5 소제목+본문. 레버 후보(FTE 순): ' + ', '.join(f"{r['name']} {r['n']}명 {r['fte']:.1f} FTE(대체형 {r0(r['sub'])})" for r in lev)) + '\n')
    w('**유의 사항.** 본 수치는 직업 단위 경향이며 직무별 인원이 추정치이므로, 인원 감축 의사결정의 근거로 사용하지 않는다.\n')
    # ---------- 5. 인사 ----------
    w('## 5. 인적자원 시사점\n'); w(TODO('인사 과제의 성격 한 단락(감원이 아닌 무엇)') + '\n')
    w('**5.1 직무 재설계 대상**\n'); w('표 7. 재설계 우선 직무와 전환 방향\n')
    cand = sorted(R, key=lambda r: -(r['e26'] * r['sub']))[:4]
    w(tbl(['직무', '현황', '전환 방향', '근거'], [[f"{r['name']}({r['n']}명)", f"노출 {r0(r['e26'])}, 대체형 {r0(r['sub'])}", TODO('방향'), TODO('근거')] for r in cand]) + '\n')
    w(TODO('5.2~5.4 주니어 육성·유지·평가 등 회사 사정에 맞는 항목') + '\n')
    w('**5.5 노사·법적 환경: 한국과 미국**\n'); w('표 8. AI 도입 관련 노사·법적 요건 비교\n')
    mjs = [k for k, v in sorted(o['mix'].items(), key=lambda kv: -kv[1]) if v >= .05][:4]
    kru = ', '.join(f"{MJN[k]} {PR['union']['major'][k]['all']}%" for k in mjs if PR['union']['major'].get(k, {}).get('all') is not None)
    usg = []
    for r in sorted(R, key=lambda r: -r['n']):
        g = UK['map'].get(r['code'][:2])
        if g and g not in [x[0] for x in usg]: usg.append((g, UK['us'][g]['union']))
    usu = ', '.join(f"{US_NAME.get(g, g)} {u}%" for g, u in usg[:3])
    w(tbl(['항목', f"한국({name.replace('(주)', '')} 적용)", '미국(참고)'], [
        ['노사협의회', '상시 30명 이상 사업장 설치 의무(근로자참여법 제4조). 신기계·기술 도입, 기술상 사정에 따른 배치전환·재훈련, 근로자 감시 설비가 협의 사항(제20조)' if N >= 30 else '상시 30명 미만으로 설치 의무 없음(근로자참여법 제4조)', '해당 제도 없음'],
        ['노동조합', f'조합 유무 확인 필요. 직종별 가입률: {kru}(2025). 조합이 있는 경우 AI 도입에 따른 직무·인력 변경 계획은 교섭 대상(고용노동부 지침, 2026.9)', f'가입률 {usu}(2025)'],
        ['해고 규제', f"정당한 이유 필요, 경영상 해고 시 50일 전 협의(근로기준법 제23·24조). OECD 고용보호지표 {UK['epl']['kr']}", f"임의고용 원칙. {UK['epl']['us']}"],
        ['AI 규율', '채용 단계 AI 활용은 AI 기본법 고영향 영역. AI 단독 결정에 의한 해고·감봉 금지 근로기준법 개정안 발의(2026.6)', '연방법 없음, 주·도시별 규율']] + C.get('law_rows', [])) + '\n')
    w('AI 도입 계획을 노사협의회에 사전 상정하는 것은 법적 요건이자, 구성원 불안을 낮추는 가장 비용 효율적인 방법이다.\n')
    # ---------- 6. 로드맵 ----------
    w('## 6. 90일 실행 로드맵\n'); w(TODO('시범 범위 한 문장') + '\n'); w('표 9. 단계별 실행 과제\n')
    w(tbl(['시기', '경영진', '인사(HR)'], [['0~30일', TODO('기준선 측정·시범 선정'), '노사협의회에 AI 활용 계획 상정(인력 감축 목적 아님 명시). 실제 인원표 기준 재진단. 퇴사 사유 분석'],
                                         ['31~60일', TODO('시범 운영'), TODO('교육·직무 재설계 협의')], ['61~90일', TODO('평가 후 확대 결정'), TODO('육성·평가 체계 확정')]]) + '\n')
    w('성과 지표(KPI): ' + TODO('5~7개') + '\n')
    # ---------- 부록 ----------
    w('## 부록. 방법론과 한계\n')
    w('재무·인력 현황은 공개 자료로 교차 확인했고, 직무 구성은 공개 정보에 기반한 추정치다. 실제 인원표를 받으면 같은 방법으로 다시 산출한다.\n')
    ap = [f"**인원**: {C.get('basis', f'{N}명')}.",
          '**AI 노출도**: 직무별로 한국표준직업분류 소분류를 연결하고, 해당 직업의 41개 업무 활동 구성에 업무별 AI 수행 가능성을 곱해 산출. 업무 단위 수행 가능성은 Eloundou 외(2024, Science)와 국제노동기구 Gmyrek 외(2025)의 평균이며, 기준일 시점의 주간 AI 동향 보정을 반영.',
          '**대체형·보완형**: 41개 업무 중 문서화·정보 처리·행정 처리 등 11개를 대체형으로 분류.',
          f"**FTE·인건비**: 인원 × 노출도로 FTE를 산출하고, 직종 대분류별 임금 수준(고용형태별근로실태조사 2025)으로 가중한 뒤 {paybasis}({num(o['payroll'])}억 원)에 맞춰 환산." if o.get('payroll_basis') == 'actual' else f"**FTE·인건비**: 인원 × 노출도로 FTE를 산출하고, 직종 대분류별 월 임금총액(고용형태별근로실태조사 2025)을 곱해 추정.",
          (f"**업종 평균**: {indn} 취업자의 직업 대분류 구성(지역별고용조사 2025년 하반기) × 대분류별 전국 평균 노출도. 대분류 안의 구성 차이는 반영하지 못한 근사치." if ind else None),
          '**한계**: 업무 활동 구성은 미국 직업 기준(O*NET 31.0)이며 당사 실제 업무와 차이가 있을 수 있음.' + (' ' + ', '.join(j(v[0], '와', '과') + ' ' + '·'.join(v[1:]) for v in same) + '는 같은 직업 분류로 계산됨.' if same else '')]
    w('\n'.join('- ' + a for a in ap if a) + '\n')
    w('**확인 요청 사항**\n'); w('\n'.join('- ' + x for x in ['직무별 실제 인원(정규·계약·외부 인력 구분)과 급여 총액', '노동조합 유무 및 노사협의회 운영 현황', '현재 사용 중인 AI·자동화 도구'] + C.get('asks', [])) + '\n')
    w('**출처**\n')
    w('\n'.join('- ' + s for s in C.get('sources', []) + ['지역별고용조사 산업/직업별 취업자(KOSIS DT_1ES3B33J) · 직종별 임금(DT_118N_LCE306) · 직종별 노조가입률(DT_118N_LCE310)',
                                                    '근로자참여 및 협력증진에 관한 법률 · 근로기준법 · 미국 노동통계국 노조 가입률 2025 · OECD 고용보호법제 지표 · [AI 점령 지도](https://aijido.org)']) + '\n')
    md = '\n'.join(out)
    open(f'{od}/report.md', 'w').write(md)
    if P:
        for q in P['peers']:
            if q.get('n') and not q.get('self') and P.get('metric') != 'margin' and not q.get('nodate'): pass
    if not C.get('sources'): checks.append('sources 없음: 출처 목록이 통계 출처만으로 끝남')
    todo = md.count('<!-- 작성:')
    json.dump({'todo': todo, 'checks': checks, 'org': {k: o[k] for k in ('n', 'e26', 'e30', 'fte', 'fte30', 'cost', 'payroll', 'sub')}, 'groups': G},
              open(f'{od}/checks.json', 'w'), ensure_ascii=False, indent=1)
    print(f"{name}: report.md 작성 · 작성 필요 {todo}곳 · 점검 {len(checks)}건")
    for c in checks: print('  -', c)

if __name__ == '__main__':
    main(sys.argv[1])
