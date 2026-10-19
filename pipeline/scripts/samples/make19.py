import os, json, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'make.py')).read()
exec(src.split('# ---------- 1. 차오르는 물')[0])
from scipy.spatial import cKDTree, Voronoi
from scipy.ndimage import gaussian_filter
from PIL import Image, ImageDraw, ImageFont

FD = '/usr/share/fonts/opentype/noto/'
def font(w, size):
    for i in range(10):
        try: f = ImageFont.truetype(FD + f'NotoSansCJK-{w}.ttc', size, index=i)
        except Exception: break
        if f.getname()[0] == 'Noto Sans CJK KR': return f
    return ImageFont.truetype(FD + f'NotoSansCJK-{w}.ttc', size, index=1)

W, H, S = 1800, 2400, 2
WW, HH = W * S, H * S
BG = (14, 16, 22)
rng = np.random.default_rng(11)
CX, CY = 880, 1230

def smooth_noise(sig, seed, scale=4):
    r = np.random.default_rng(seed)
    small = gaussian_filter(r.normal(size=(H // scale + 2, W // scale + 2)), sig / scale)
    small /= np.abs(small).max()
    return np.kron(small, np.ones((scale, scale), np.float32))[:H, :W]

def walk(x, y, h, step, n, turn, revert):
    pts = [(x, y)]; hb = h; dh = 0
    for _ in range(n):
        dh = dh * .9 + rng.normal(0, turn); h = h + dh - revert * (h - hb)
        x += step * np.cos(h); y += step * np.sin(h); pts.append((x, y))
        if x < -60 or x > W + 60 or y < -60 or y > H + 60: break
    return pts
def spline(P, n=40):
    P = np.array(P, float); P = np.vstack([P[0], P, P[-1]]); out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2]); return [tuple(q) for q in out]

# ---------- 간선도로 (도시보다 먼저: 시가지가 길을 따라 번지도록) ----------
ART = []
for k in range(9):
    a = 2 * np.pi * k / 9 + rng.normal(0, .2); r0 = rng.uniform(60, 190)
    ART.append(walk(CX + r0 * np.cos(a), CY + r0 * np.sin(a), a + rng.normal(0, .35), 6, 420, .012, .006))
for _ in range(4):
    a = rng.uniform(0, 2 * np.pi); r0 = rng.uniform(250, 450)
    ART.append(walk(CX + r0 * np.cos(a), CY + r0 * np.sin(a), a + np.pi / 2 * rng.choice([-1, 1]) + rng.normal(0, .3), 6, 150, .015, .008))
ring = []
for t in np.linspace(-2.7, 1.2, 160):
    rr = 540 * (1 + .09 * np.sin(3 * t + 1) + .04 * np.sin(7 * t))
    ring.append((CX + rr * np.cos(t), CY + rr * 1.06 * np.sin(t)))
HW = [spline([(390, -40), (410, 330), (330, 700), (360, 1050), (560, 1420), (900, 1800), (1180, 2150), (1290, 2440)]),
      spline([(-40, 1640), (420, 1560), (860, 1500), (1260, 1560), (1600, 1700), (1840, 1760)]),
      spline([(1840, 470), (1500, 560), (1150, 720), (1000, 900)])]

# ---------- 도시 밀도 ----------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
D = np.exp(-(np.hypot(xx - CX, (yy - CY) / 1.12) / 600) ** 2)
SAT = [(250, 1560, 190, .75), (1480, 640, 170, .7), (1380, 1960, 150, .65), (470, 600, 130, .6), (1580, 1320, 140, .6)]
for sx, sy, sr, sa in SAT:
    D = np.maximum(D, sa * np.exp(-(np.hypot(xx - sx, yy - sy) / sr) ** 2))
from scipy.ndimage import distance_transform_edt
rm = Image.new('L', (W, H), 0); rd = ImageDraw.Draw(rm)
for R_ in ART + HW + [ring]: rd.line(R_, fill=255, width=3)
droad = distance_transform_edt(np.array(rm) == 0)
dc = np.hypot(xx - CX, yy - CY)
Dn = np.maximum(D, .62 * np.exp(-(droad / 34) ** 2) * np.exp(-(dc / 1050) ** 2)) + .2 * smooth_noise(40, 1) + .12 * smooth_noise(12, 2) + .05 * smooth_noise(4, 3)
urban = Dn > .32

# ---------- 동네(보로노이) ----------
cand = np.column_stack([rng.uniform(0, W, 60000), rng.uniform(0, H, 60000)])
ci = cand.astype(int)
dv = Dn[ci[:, 1].clip(0, H - 1), ci[:, 0].clip(0, W - 1)]
keep = (dv > .32) & (rng.random(len(cand)) < np.clip(dv, 0, 1) ** 1.6 * .30)
seeds = cand[keep]
NS = len(seeds)
uy, ux = np.nonzero(urban)
_, lab = cKDTree(seeds).query(np.column_stack([ux, uy]))
label = np.full((H, W), -1, np.int32); label[uy, ux] = lab
area = np.bincount(lab, minlength=NS).astype(float)
cx_ = np.bincount(lab, ux, minlength=NS) / np.maximum(area, 1)
cy_ = np.bincount(lab, uy, minlength=NS) / np.maximum(area, 1)
dist_c = np.hypot(cx_ - CX, cy_ - CY)
park = (rng.random(NS) < .03) & (area > 150) & (dist_c > 150)

# ---------- 직업 → 동네 배정 (면적 = 종사자 수) ----------
def pol(a, r): return (CX + r * np.cos(np.radians(a)), CY + r * np.sin(np.radians(a)))
JP = {'경영관련 사무원': pol(0, 90), '회계·경리 사무원': pol(120, 80), '금융 사무원': pol(240, 90), '행정 공무원': pol(300, 170),
      '법률 전문가': pol(60, 200), '기자': pol(170, 190), '경영·기획 관리자': pol(10, 230), '소프트웨어 개발자': pol(330, 300), '디자이너': pol(90, 310),
      '매장 판매원': pol(150, 380), '음식 서비스원': pol(210, 380), '영업원': pol(270, 330), '고객센터 상담원': pol(40, 380), '조리사': pol(250, 470),
      '요양보호사': pol(170, 560), '보육교사': pol(205, 600), '사회복지사': pol(235, 560), '간호사': pol(120, 520), '의사': pol(95, 450), '교사': pol(70, 520),
      '자동차 조립 노동자': pol(320, 600), '품질 검사원': pol(345, 560), '설비 정비 기술자': pol(300, 700), '전기·전자 기술자': pol(355, 700),
      '물류 창고 작업원': pol(20, 650), '운전 종사자': pol(280, 820), '배달·택배원': pol(40, 560),
      '건설 기능원': pol(195, 750), '청소원': pol(140, 700), '보안·경비원': pol(260, 600), '작물재배 종사자': (240, 1580)}
GRP = {}
for n in ['경영관련 사무원', '회계·경리 사무원', '금융 사무원', '행정 공무원', '법률 전문가', '기자', '경영·기획 관리자', '소프트웨어 개발자', '디자이너']: GRP[n] = 'office'
for n in ['매장 판매원', '음식 서비스원', '영업원', '고객센터 상담원', '조리사']: GRP[n] = 'service'
for n in ['요양보호사', '보육교사', '사회복지사', '간호사', '의사', '교사']: GRP[n] = 'care'
for n in ['자동차 조립 노동자', '품질 검사원', '설비 정비 기술자', '전기·전자 기술자', '물류 창고 작업원', '운전 종사자', '배달·택배원']: GRP[n] = 'industry'
for n in ['건설 기능원', '청소원', '보안·경비원']: GRP[n] = 'outer'
GRP['작물재배 종사자'] = 'agri'
_V3 = json.load(open(os.path.join(HERE, 'jobs_v3.json')))
JOBS2 = [(j['name'], j['k'] / 10, j['tasks']) for j in _V3['jobs']]; GRP2 = {j['name']: j['group'] for j in _V3['jobs']}
_old = {}; JOBS = JOBS2; N = len(JOBS); names = [j[0] for j in JOBS]; ws = np.array([j[1] for j in JOBS], float); GRP = GRP2
_GC = {'g3': (CX, CY), 'g1': pol(300, 150), 'g2': pol(60, 380), 'g4': pol(170, 400), 'g5': pol(230, 420), 'g7': pol(330, 560), 'g8': pol(10, 640), 'g9': pol(250, 650), 'g6': (240, 1580)}
for _g in _GC:
    _js = [n for n in names if GRP[n] == _g]
    for _i, _n in enumerate(_js):
        if _old.get(_n) == _g and _n in JP: continue
        _a = 2 * np.pi * _i / max(len(_js), 1); _r = 90 + 50 * (_i % 2)
        JP[_n] = (_GC[_g][0] + _r * np.cos(_a), _GC[_g][1] + _r * np.sin(_a))
_rk=lambda r:(r[0],int(r[1:]))
JOBS=[(n_,w_,dict(sorted(d_.items(),key=lambda kv:_rk(kv[0])))) for n_,w_,d_ in JOBS]
JS = np.array([JP[n] for n in names])
TASKMODE = os.environ.get('MODE') == 'task'
if TASKMODE:
    RNAME = {'A1':'정보 찾아 모으기','A2':'상황 지켜보기','A3':'사물·사건 알아보기','A4':'장비·재료 점검','A5':'수량·비용 가늠',
    'B1':'질 판단하기','B2':'정보 처리하기','B3':'기준 충족 평가','B4':'데이터 분석','B5':'결정·문제 풀기','B6':'창의적으로 생각하기','B7':'지식 활용','B8':'목표·전략 세우기','B9':'일정 짜기','B10':'우선순위 정하기',
    'C1':'몸 쓰는 반복 작업','C2':'물건 옮기기','C3':'기계·공정 제어','C4':'차량·장비 운전','C5':'컴퓨터로 일하기','C6':'설계·도면','C7':'기계 수리·정비','C8':'전자 장비 정비','C9':'기록·문서화',
    'D1':'풀어 설명하기','D2':'동료와 소통','D3':'고객 응대','D4':'관계 맺기','D5':'돌보기','D6':'팔고 설득하기','D7':'갈등 조정','D8':'대중 앞에서','D9':'남의 일 조율','D10':'팀 만들기','D11':'가르치기','D12':'지휘하기','D13':'코칭','D14':'상담·조언','D15':'행정 처리','D16':'채용·배치','D17':'자원 관리'}
    TWd = {}
    for jn, jw, jt in JOBS:
        tw_ = sum(jt.values())
        for r_, w_ in jt.items(): TWd[r_] = TWd.get(r_, 0) + jw * w_ / tw_
    order = sorted(TWd, key=lambda r: (r[0], int(r[1:])))
    JOBS = [(RNAME[r], TWd[r], {r: 1.0}) for r in order]
    N = len(JOBS); names = [j[0] for j in JOBS]; ws = np.array([j[1] for j in JOBS], float)
    GRP = {RNAME[r]: r[0] for r in order}
    GCEN = {'B': (CX, CY - 40), 'A': pol(325, 560), 'C': pol(140, 560), 'D': pol(220, 520)}
    JS = []
    for g in 'ABCD':
        rs = [r for r in order if r[0] == g]
        for i_, r in enumerate(rs):
            ang = 2 * np.pi * i_ / len(rs); rad = 120 + 60 * (i_ % 2)
            JS.append((GCEN[g][0] + rad * np.cos(ang), GCEN[g][1] + rad * np.sin(ang)))
    JS = np.array(JS)
# ---------- 직업 → 동네: 한 덩어리로 자라나게 ----------
import heapq
from collections import deque
def adjacency(lbl):
    pr = []
    for a_, b_ in ((lbl[:, 1:], lbl[:, :-1]), (lbl[1:, :], lbl[:-1, :])):
        m_ = (a_ != b_) & (a_ >= 0) & (b_ >= 0); pr.append(np.stack([a_[m_], b_[m_]], 1))
    pr = np.unique(np.concatenate(pr), axis=0)
    adj = [set() for _ in range(NS)]
    for a_, b_ in pr: adj[a_].add(b_); adj[b_].add(a_)
    return adj
from scipy.ndimage import label as cc_label, find_objects, distance_transform_edt as edt
for n_, sl_ in enumerate(find_objects(label + 1)):
    if sl_ is None or n_ == 0: continue
    c_ = n_ - 1
    sub = label[sl_] == c_
    lab_, k_ = cc_label(sub)
    if k_ > 1:
        sizes = np.bincount(lab_.ravel())[1:]; keepk = 1 + int(np.argmax(sizes))
        blk = label[sl_]; blk[sub & (lab_ != keepk)] = -1
uy, ux = np.nonzero(label >= 0); lab = label[uy, ux]
area = np.bincount(lab, minlength=NS).astype(float)
cx_ = np.bincount(lab, ux, minlength=NS) / np.maximum(area, 1)
cy_ = np.bincount(lab, uy, minlength=NS) / np.maximum(area, 1)
ADJ = adjacency(label)
ok = (area > 0) & ~park
# 가장 큰 연결 덩어리만 도시로 남김
seen = np.zeros(NS, bool); comps = []
for c0 in np.where(ok)[0]:
    if seen[c0]: continue
    q = deque([c0]); seen[c0] = True; comp = [c0]
    while q:
        c1 = q.popleft()
        for c2 in ADJ[c1]:
            if ok[c2] and not seen[c2]: seen[c2] = True; q.append(c2); comp.append(c2)
    comps.append(comp)
main = np.zeros(NS, bool); main[max(comps, key=lambda c: area[c].sum())] = True
keep_park = park & np.array([any(main[n2] for n2 in ADJ[c]) for c in range(NS)])
drop = ~(main | keep_park)
label[np.isin(label, np.where(drop)[0])] = -1
area[drop] = 0; park = keep_park
urban = label >= 0
mainc = np.where(main)[0]
def partition(cells, S, tgt):
    """cells를 k개 덩어리로 나눔: 파워 다이어그램 → 덩어리 정리 → 넓이 맞추기. 덩어리마다 한 조각."""
    k = len(S); cells = np.asarray(cells); inset = np.zeros(NS, bool); inset[cells] = True
    tgt = tgt / tgt.sum() * area[cells].sum()
    Pc = np.column_stack([cx_[cells], cy_[cells]]); Ac = area[cells]; w_ = np.zeros(k)
    for it in range(900):
        asg = (((Pc[:, None, :] - S[None, :, :]) ** 2).sum(-1) - w_[None, :]).argmin(1)
        w_ += 4000 * (tgt - np.bincount(asg, weights=Ac, minlength=k)) / tgt
    own = np.full(NS, -1); own[cells] = asg
    nbr = lambda x: [y for y in ADJ[x] if inset[y]]
    for j in range(k):
        cs = set(np.where(own == j)[0]); comps_ = []
        while cs:
            c0 = cs.pop(); comp = [c0]; q = deque([c0])
            while q:
                x = q.popleft()
                for y in nbr(x):
                    if y in cs: cs.remove(y); comp.append(y); q.append(y)
            comps_.append(comp)
        comps_.sort(key=lambda c: -area[c].sum())
        for comp in comps_[1:]: own[comp] = -1
    got = np.bincount(own[own >= 0], weights=area[own >= 0], minlength=k).astype(float)
    while (own[cells] < 0).any():
        changed = False
        for c in cells[own[cells] < 0]:
            nb = [own[y] for y in nbr(c) if own[y] >= 0]
            if nb:
                j = min(set(nb), key=lambda j: got[j] / tgt[j]); own[c] = j; got[j] += area[c]; changed = True
        if not changed: break
    def conn_wo(j, c):
        cs = [x for x in np.where(own == j)[0] if x != c]
        if not cs: return False
        st = {cs[0]}; q = deque([cs[0]]); cs = set(cs)
        while q:
            x = q.popleft()
            for y in nbr(x):
                if y in cs and y not in st: st.add(y); q.append(y)
        return len(st) == len(cs)
    for j in range(k):
        if got[j] > 0: continue
        dd = np.hypot(cx_[cells] - S[j, 0], cy_[cells] - S[j, 1])
        for ci in np.argsort(dd):
            c = cells[ci]; d_ = own[c]
            if d_ >= 0 and (own == d_).sum() > 1 and conn_wo(d_, c):
                own[c] = j; got[d_] -= area[c]; got[j] += area[c]; break
    t2 = tgt.copy()
    for it in range(4000):
        ratio = got / t2; d_ = int(np.argmax(ratio))
        if ratio[d_] < 1.04: break
        cands = [(ratio[own[c2]], c, own[c2]) for c in np.where(own == d_)[0] for c2 in nbr(c) if own[c2] >= 0 and own[c2] != d_ and ratio[own[c2]] < ratio[d_] - .05]
        moved = False
        for _, c, r_ in sorted(cands):
            if area[c] > (got[d_] - t2[d_]) * 1.6 + 1: continue
            if conn_wo(d_, c): own[c] = r_; got[d_] -= area[c]; got[r_] += area[c]; moved = True; break
        if not moved: t2[d_] = got[d_]
    t2 = tgt.copy()
    for it in range(4000):
        ratio = got / t2; r_ = int(np.argmin(ratio))
        if ratio[r_] > .9: break
        cands = [(-ratio[own[c2]], c2, own[c2]) for c in np.where(own == r_)[0] for c2 in nbr(c) if own[c2] >= 0 and own[c2] != r_ and ratio[own[c2]] > ratio[r_] + .08]
        moved = False
        for _, c, d_ in sorted(cands):
            if conn_wo(d_, c): own[c] = r_; got[d_] -= area[c]; got[r_] += area[c]; moved = True; break
        if not moved: t2[r_] = got[r_] / .91
    return own
# 1단계: 구(카테고리)를 먼저 한 덩어리씩 나누고, 2단계: 구 안에서 직업을 나눔
GL = list(_GC); GS = np.array([_GC[g] for g in GL], float)
if TASKMODE: GL = list('BACD'); GS = np.array([GCEN[g] for g in GL], float)
gws = np.array([sum(ws[j] for j in range(N) if GRP[names[j]] == g) for g in GL])
gown = partition(mainc, GS, gws)
owner = np.full(NS, -1)
for gi, g in enumerate(GL):
    js = [j for j in range(N) if GRP[names[j]] == g]; cells = np.where(gown == gi)[0]
    if len(js) == 1: owner[cells] = js[0]; continue
    sub = partition(cells, JS[js].astype(float), ws[js].astype(float))
    owner[cells] = np.array(js)[sub[cells]]
got = np.bincount(owner[owner >= 0], weights=area[owner >= 0], minlength=N).astype(float)
jobOf = owner.copy()
bad = []
for j in range(N):
    cs = set(np.where(jobOf == j)[0]); c0 = next(iter(cs)); st = {c0}; q = deque([c0])
    while q:
        x = q.popleft()
        for y in ADJ[x]:
            if y in cs and y not in st: st.add(y); q.append(y)
    if len(st) != len(cs): bad.append(names[j])
print('pieces split:', bad)
_rt = got / (ws / ws.sum() * area[main].sum()); print('NS', NS, 'off:', [(names[j], round(float(_rt[j]), 2)) for j in range(N) if not .8 < _rt[j] < 1.25])
print('area ratio min/max', round(float((got / (ws / ws.sum() * area[main].sum())).min()), 2), round(float((got / (ws / ws.sum() * area[main].sum())).max()), 2))
# ---------- 필지 규칙 ----------
LOTS = {'g1': (7, 5.5), 'g2': (8, 6), 'g3': (7, 5.5), 'g4': (9, 7), 'g5': (9, 7), 'g6': (30, 19), 'g7': (14, 9.5), 'g8': (17, 11), 'g9': (11, 8), 'office': (7, 5.5), 'service': (9, 7), 'care': (10, 7.5), 'industry': (17, 11), 'outer': (11, 8), 'agri': (30, 19), 'creative': (8, 6), 'A': (9, 7), 'B': (7, 5.5), 'C': (15, 10), 'D': (10, 7.5)}
theta = np.zeros(NS); lotw = np.ones(NS) * 10; loth = np.ones(NS) * 8
radial = np.arctan2(cy_ - CY, cx_ - CX)
for n_ in range(NS):
    j = jobOf[n_]
    g = GRP[names[j]] if j >= 0 else ('D' if TASKMODE else 'g2')
    f = .85 + .5 * min(dist_c[n_] / 900, 1)
    lotw[n_], loth[n_] = LOTS[g][0] * f * S, LOTS[g][1] * f * S
    theta[n_] = radial[n_] + rng.choice([0, np.pi / 2]) + rng.normal(0, .2) if rng.random() < .75 else rng.uniform(0, np.pi)
offu = rng.uniform(0, 100, NS); offv = rng.uniform(0, 100, NS)
MAXT = 8
CUM = np.ones((N, MAXT), np.float32) * 2
for j in range(N):
    w_ = np.array(list(JOBS[j][2].values()), float); c = np.cumsum(w_) / w_.sum()
    CUM[j, :len(c)] = c
def PV(year):
    out = np.zeros((N, MAXT + 1), np.float32)
    for j in range(N):
        t = list(JOBS[j][2].keys())
        for k, r_ in enumerate(t): out[j, k] = p(r_, year)
        out[j, len(t):] = out[j, len(t) - 1]
    return out
THR = np.array([.20, .30, .40, .50, .62])
PAL = np.array([(0, 235, 235), (60, 165, 255), (55, 95, 255), (85, 40, 255), (155, 30, 245), (255, 0, 225)], np.uint8)
def hsh(a, b, c):
    h = (a.astype(np.int64) * 73856093) ^ (b.astype(np.int64) * 19349663) ^ (c.astype(np.int64) * 83492791)
    h = (h * 1274126177) & 0xffffffffffff; h ^= h >> 16
    return (h & 0xffffff).astype(np.float32) / 0xffffff

# 직업 영역 안에서 업무가 한 덩어리씩 모이도록: 직업 중심 기준 각도의 넓이 누적 분포로 업무 배정
_uy, _ux = np.nonzero(label >= 0); _j = jobOf[label[_uy, _ux]]; _ok = _j >= 0; _uy, _ux, _j = _uy[_ok], _ux[_ok], _j[_ok]
CXJ = np.bincount(_j, _ux, minlength=N) / np.maximum(np.bincount(_j, minlength=N), 1)
CYJ = np.bincount(_j, _uy, minlength=N) / np.maximum(np.bincount(_j, minlength=N), 1)
ROT = rng.uniform(0, 2 * np.pi, N); NB = 720
_ang = np.mod(np.arctan2(_uy - CYJ[_j], _ux - CXJ[_j]) + ROT[_j], 2 * np.pi)
HIST = np.zeros((N, NB)); np.add.at(HIST, (_j, np.minimum((_ang / (2 * np.pi) * NB).astype(int), NB - 1)), 1)
CDF = np.cumsum(HIST, 1) / np.maximum(HIST.sum(1, keepdims=True), 1)
J0 = np.zeros((HH, WW), np.int8); TIDX = np.zeros((HH, WW), np.int8)
NOISE = np.zeros((HH, WW), np.float16); FILL = np.zeros((HH, WW), np.uint8); VJ = np.zeros((HH, WW), bool); PK = np.zeros((HH, WW), bool)  # 0 바탕, 1 필지, 2 공원
X = np.arange(WW)[None, :]
for y0 in range(0, HH, 300):
    Y = np.arange(y0, min(y0 + 300, HH))[:, None]; sl = slice(y0, y0 + Y.shape[0])
    n_ = label[Y // S, X // S]
    valid = n_ >= 0; n0 = np.where(valid, n_, 0)
    j = jobOf[n0]; ispark = valid & park[n0]
    valid &= j >= 0; j0 = np.where(j >= 0, j, 0)
    th = theta[n0]; c, s_ = np.cos(th), np.sin(th)
    u = X * c + Y * s_ + offu[n0] * S; v = -X * s_ + Y * c + offv[n0] * S
    lw, lh = lotw[n0], loth[n0]
    iu, iv = np.floor(u / lw), np.floor(v / lh)
    alley = ((u - iu * lw) < 2) | ((v - iv * lh) < 2)
    h2 = hsh(iv, iu, n0 + 7)
    du, dv = (iu + .5) * lw - offu[n0] * S, (iv + .5) * lh - offv[n0] * S
    xc, yc = (du * c - dv * s_) / S, (du * s_ + dv * c) / S
    ang = np.mod(np.arctan2(yc - CYJ[j0], xc - CXJ[j0]) + ROT[j0], 2 * np.pi)
    h1 = CDF[j0, np.minimum((ang / (2 * np.pi) * NB).astype(int), NB - 1)]
    J0[sl] = j0; TIDX[sl] = (h1[..., None] > CUM[j0]).sum(-1)
    NOISE[sl] = (h2 - .5) * .14
    f = np.zeros(valid.shape, np.uint8); f[valid & ~alley] = 1; f[ispark & ~alley] = 2; FILL[sl] = f; VJ[sl] = valid; PK[sl] = ispark
def fabric(year):
    pv = PV(year)
    fab = np.empty((HH, WW, 3), np.uint8); fab[:] = BG
    for y0 in range(0, HH, 600):
        sl = slice(y0, y0 + 600)
        val = pv[J0[sl], TIDX[sl]] + NOISE[sl].astype(np.float32)
        col = PAL[np.searchsorted(THR, val)]
        blk = fab[sl]; f = FILL[sl]
        blk[f == 1] = col[f == 1]; blk[f == 2] = (22, 52, 44)
    return fab

# ---------- 도로·강 ----------
road = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); dr = ImageDraw.Draw(road)
sc = lambda pts: [(x * S, y * S) for x, y in pts]
def line(pts, col, w): dr.line(sc(pts), fill=col, width=w, joint='curve')

# 강: 좁고 구불구불한 본류 + 지류
def river_main():
    pts = []; x, y = -30, 1170; h = -.05; k = 0; base = -.05
    while x < W + 30 and len(pts) < 4000:
        if rng.random() < .03: k += rng.choice([-1, 1]) * rng.uniform(.05, .12)
        k = np.clip(k * .93 + rng.normal(0, .005), -.09, .09)
        h += k - .03 * (h - base)
        x += 3 * np.cos(h); y += 3 * np.sin(h); pts.append((x, y))
    return pts
RIV = river_main()
RA = np.array(RIV)
def river_trib(x, y, tx, ty):
    # 목표를 강 위의 가장 가까운 점으로 잡고, 방향을 충분히 당겨 맴돌지 않게 한다
    i_ = int(np.argmin(np.hypot(RA[:, 0] - tx, RA[:, 1] - ty))); tx, ty = RA[i_]
    pts = [(x, y)]; k = 0; h = np.arctan2(ty - y, tx - x)
    for _ in range(1500):
        if rng.random() < .03: k += rng.choice([-1, 1]) * rng.uniform(.05, .12)
        k = np.clip(k * .93 + rng.normal(0, .005), -.06, .06)
        h += k - .12 * (((h - np.arctan2(ty - y, tx - x)) + np.pi) % (2 * np.pi) - np.pi)
        x += 3 * np.cos(h); y += 3 * np.sin(h); pts.append((x, y))
        if np.hypot(*(RA - (x, y)).T).min() < 5 or np.hypot(tx - x, ty - y) < 6: break
    return pts
TRIB = river_trib(W + 20, 760, 1240, 1110)
for R_ in (RIV, TRIB):
    line(R_, BG, 26); line(R_, (64, 136, 255), 9)
# 연못
for _ in range(40):
    x, y = rng.uniform(0, W), rng.uniform(0, H)
    if Dn[int(y), int(x)] > .26: continue
    r = rng.uniform(3, 11); k = rng.uniform(1, 2.2); a0 = rng.uniform(0, np.pi)
    ang = np.linspace(0, 2 * np.pi, 16, endpoint=False); rr = r * (1 + .3 * rng.normal(size=16))
    dr.polygon([((x + rr[i] * k * np.cos(ang[i]) * np.cos(a0) - rr[i] * np.sin(ang[i]) * np.sin(a0)) * S,
                 (y + rr[i] * k * np.cos(ang[i]) * np.sin(a0) + rr[i] * np.sin(ang[i]) * np.cos(a0)) * S) for i in range(16)], fill=(46, 108, 230))
# 바깥 자잘한 길 조각
for _ in range(900):
    x, y = rng.uniform(0, W), rng.uniform(0, H)
    if Dn[int(y), int(x)] > .3 or rng.random() > (.25 + Dn[int(y), int(x)] * 2): continue
    a = rng.uniform(0, np.pi); L = rng.uniform(5, 26)
    p2 = (x + L * np.cos(a), y + L * np.sin(a)); line([(x, y), p2], (165, 170, 182, 220), 2)
    if rng.random() < .35:
        b = a + np.pi / 2 * rng.choice([-1, 1]); L2 = rng.uniform(4, 12)
        line([p2, (p2[0] + L2 * np.cos(b), p2[1] + L2 * np.sin(b))], (165, 170, 182, 220), 2)
# 시골길
for _ in range(34):
    a = rng.uniform(0, 2 * np.pi); r0 = rng.uniform(450, 900)
    x, y = CX + r0 * np.cos(a), CY + r0 * 1.1 * np.sin(a)
    line(walk(x, y, a + rng.normal(0, .8), 6, int(rng.uniform(40, 140)), .02, .03), (190, 195, 206, 235), 3)
# 동네 사이 길(보로노이 모서리)
vor = Voronoi(seeds)
for (a, b), rv in zip(vor.ridge_points, vor.ridge_vertices):
    if -1 in rv or area[a] == 0 or area[b] == 0: continue
    p1, p2 = vor.vertices[rv[0]], vor.vertices[rv[1]]
    if np.hypot(*(p1 - p2)) > 160: continue
    mx, my = (p1 + p2) / 2
    if not (0 <= mx < W and 0 <= my < H) or not urban[int(my), int(mx)]: continue
    border = jobOf[a] != jobOf[b]
    if not border and rng.random() < .3: continue
    L = np.hypot(*(p2 - p1)); nrm = np.array([-(p2 - p1)[1], (p2 - p1)[0]]) / max(L, 1e-6)
    cpt = (p1 + p2) / 2 + nrm * rng.normal(0, L * .12)
    bz = [tuple((1 - t) ** 2 * p1 + 2 * (1 - t) * t * cpt + t ** 2 * p2) for t in np.linspace(0, 1, 9)]
    line(bz, (238, 240, 246, 255) if border else (190, 195, 208, 215), 3 if border else 2)
for R_ in ART + [ring]:
    line(R_, BG, 11)
for R_ in ART + [ring]:
    line(R_, (248, 249, 252), 5)
# 고속도로: 도심을 비껴 지나감
for R_ in HW:
    line(R_, BG, 19)
for R_ in HW:
    line(R_, (178, 184, 196), 11); line(R_, BG, 1)

# ---------- 고정 레이어: 직업 이름, 범례, 출처 ----------
over = Image.new('RGBA', (WW, HH), (0, 0, 0, 0)); od = ImageDraw.Draw(over)
BLOCKED = [(0, 0, 820 * S, 230 * S), (0, (H - 380) * S, 420 * S, HH), ((W - 900) * S, (H - 90) * S, WW, HH)]
def hit(b):
    return any(not (b[2] < q[0] or b[0] > q[2] or b[3] < q[1] or b[1] > q[3]) for q in BLOCKED)
LABELS = {}
def interior_order(j):
    cs = set(np.where(jobOf == j)[0]); depth = {}
    q = deque()
    for c in cs:
        if any(n2 not in cs for n2 in ADJ[c]) or len(ADJ[c]) < 3: depth[c] = 0; q.append(c)
    while q:
        c = q.popleft()
        for n2 in ADJ[c]:
            if n2 in cs and n2 not in depth: depth[n2] = depth[c] + 1; q.append(n2)
    for c in cs: depth.setdefault(c, 0)
    A = area[list(cs)]; gx = (cx_[list(cs)] * A).sum() / A.sum(); gy = (cy_[list(cs)] * A).sum() / A.sum()
    return sorted(cs, key=lambda c: np.hypot(cx_[c] - gx, cy_[c] - gy) - 22 * min(depth[c], 3))
JOBPIX = np.where(label >= 0, jobOf[np.maximum(label, 0)], -1)
for j in sorted(range(N), key=lambda j: -ws[j]):
    mask = JOBPIX == j
    if not mask.any(): continue
    ys, xs = np.nonzero(mask); y0_, y1_, x0_, x1_ = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    dt = edt(np.pad(mask[y0_:y1_, x0_:x1_], 1))[1:-1, 1:-1]
    gx, gy = xs.mean(), ys.mean()
    cy2, cx2 = np.nonzero(dt >= dt.max() * .45)
    sc_ = np.hypot(cx2 + x0_ - gx, cy2 + y0_ - gy) - 1.5 * dt[cy2, cx2]
    cand = np.argsort(sc_)[:4000:40]
    placed = False
    for scale in (1, .82, .68):
        fs = int((14 + 13 * np.sqrt(ws[j] / ws.max())) * S * scale); f_ = font('Bold', fs)
        for k_ in cand:
            x, y = (cx2[k_] + x0_) * S, (cy2[k_] + y0_) * S
            l, t, r_, b_ = od.textbbox((x, y), names[j], font=f_, anchor='mm')
            box = (l - 6 * S, t - 4 * S, r_ + 6 * S, b_ + 4 * S)
            if hit(box): continue
            od.text((x, y), names[j], font=f_, fill=(255, 255, 255), anchor='mm', stroke_width=3 * S, stroke_fill=BG)
            BLOCKED.append(box); LABELS[j] = (float(x / S), float(y / S), fs / S); placed = True; break
        if placed: break
lx, ly = 60 * S, (H - 330) * S
od.rectangle([lx - 24 * S, ly - 30 * S, lx + 330 * S, ly + 330 * S], fill=BG + (235,))
od.text((lx, ly), 'AI가 수행 가능한 비율', font=font('Bold', 21 * S), fill=(255, 255, 255))
for k, lab_ in enumerate(['20% 미만', '20–30%', '30–40%', '40–50%', '50–62%', '62% 이상']):
    y0 = ly + (44 + k * 38) * S
    od.rectangle([lx, y0, lx + 44 * S, y0 + 26 * S], fill=tuple(int(c) for c in PAL[k]))
    od.text((lx + 60 * S, y0 + 13 * S), lab_, font=font('Regular', 19 * S), fill=(225, 228, 236), anchor='lm')
od.text((lx, ly + 286 * S), '필지 = 1,000명이 맡은 업무 하나\n동네 = 직업 · 넓이 = 종사자 수', font=font('Regular', 16 * S), fill=(160, 165, 178), spacing=4 * S)
od.text(((W - 60) * S, (H - 50) * S), 'AI 점령지도 v0.1 · 가상의 도시, 시연용 가상 데이터', font=font('Regular', 17 * S), fill=(160, 165, 178), anchor='rm', stroke_width=3 * S, stroke_fill=BG)
base_static = None

RNAME = {'A1':'정보 찾아 모으기','A2':'상황 지켜보기','A3':'사물·사건 알아보기','A4':'장비·재료 점검','A5':'수량·비용 가늠',
'B1':'질 판단하기','B2':'정보 처리하기','B3':'기준 충족 평가','B4':'데이터 분석','B5':'결정·문제 풀기','B6':'창의적으로 생각하기','B7':'지식 활용','B8':'목표·전략 세우기','B9':'일정 짜기','B10':'우선순위 정하기',
'C1':'몸 쓰는 반복 작업','C2':'물건 옮기기','C3':'기계·공정 제어','C4':'차량·장비 운전','C5':'컴퓨터로 일하기','C6':'설계·도면','C7':'기계 수리·정비','C8':'전자 장비 정비','C9':'기록·문서화',
'D1':'풀어 설명하기','D2':'동료와 소통','D3':'고객 응대','D4':'관계 맺기','D5':'돌보기','D6':'팔고 설득하기','D7':'갈등 조정','D8':'대중 앞에서','D9':'남의 일 조율','D10':'팀 만들기','D11':'가르치기','D12':'지휘하기','D13':'코칭','D14':'상담·조언','D15':'행정 처리','D16':'채용·배치','D17':'자원 관리'}
def frame(year, size):
    base = Image.fromarray(fabric(year)).convert('RGBA'); base.alpha_composite(road); base.alpha_composite(over)
    d = ImageDraw.Draw(base)
    tot = sum(ws[i] * occ(i, year) for i in range(N)) / ws.sum(); yi = int(np.floor(year + 1e-6))
    tag = '기록' if yi < 2026 else ('현재' if yi == 2026 else '예측')
    d.text((60 * S, 54 * S), '일의 도시', font=font('Bold', 52 * S), fill=(255, 255, 255), stroke_width=4 * S, stroke_fill=BG)
    d.text((60 * S, 128 * S), 'AI가 할 수 있는 일로 칠한 가상의 도시', font=font('Regular', 26 * S), fill=(205, 208, 218), stroke_width=4 * S, stroke_fill=BG)
    d.text((60 * S, 168 * S), f'{yi}  {tag}', font=font('Bold', 30 * S), fill=(255, 255, 255), stroke_width=4 * S, stroke_fill=BG)
    d.text((300 * S, 168 * S), f'전체 {tot*100:.0f}%', font=font('Bold', 30 * S), fill=(255, 0, 225), stroke_width=4 * S, stroke_fill=BG)
    # 연도 막대
    bx0, bx1, by = 60 * S, 760 * S, 222 * S
    d.line([bx0, by, bx1, by], fill=(80, 85, 98), width=2 * S)
    fx = bx0 + (bx1 - bx0) * (year - 2023) / (2032 - 2023)
    d.line([bx0, by, fx, by], fill=(255, 0, 225), width=4 * S)
    for yy_ in range(2023, 2033):
        tx = bx0 + (bx1 - bx0) * (yy_ - 2023) / 9
        d.line([tx, by - 6 * S, tx, by + 6 * S], fill=(120, 125, 140), width=S)
    nx = bx0 + (bx1 - bx0) * 3 / 9
    d.text((nx, by + 12 * S), '현재', font=font('Regular', 14 * S), fill=(160, 165, 178), anchor='mt')
    return base.convert('RGB').resize(size, Image.LANCZOS)

# ---------- 웹용 자료 ----------
import json
WEB = os.path.join(HERE, '..', 'web'); os.makedirs(WEB, exist_ok=True)
Jd, Fd, Td, Nd = J0[::S, ::S], FILL[::S, ::S], TIDX[::S, ::S], NOISE[::S, ::S].astype(np.float32)
idx = np.zeros((H, W, 3), np.uint8)
Vd, Pd = VJ[::S, ::S], PK[::S, ::S]
idx[..., 0] = np.where(Vd, Jd, np.where(Pd, 250, 255))
idx[..., 1] = Td + np.where((Fd == 0) & (Vd | Pd), 16, 0); idx[..., 2] = np.clip(np.round((Nd / .14 + .5) * 15), 0, 15)
Image.fromarray(idx).save(os.path.join(WEB, ('task_' if TASKMODE else 'city_')+'index.png'), optimize=True)
road.resize((W, H), Image.LANCZOS).save(os.path.join(WEB, ('task_' if TASKMODE else 'city_')+'roads.png'), optimize=True)
meta = {'W': W, 'H': H, 'jobs': [{'name': names[j], 'ws': float(ws[j]), 'group': GRP[names[j]],
         'tasks': [[RNAME.get(r_, r_), r_, float(w_)] for r_, w_ in JOBS[j][2].items()],
         'label': LABELS.get(j), 'code': _V3['jobs'][j]['code'], 'full': _V3['jobs'][j]['full'], 'k': _V3['jobs'][j]['k'], 'smalls': _V3['jobs'][j]['smalls'], 'basis': _V3['jobs'][j]['basis'], 'w41': _V3['jobs'][j].get('w41'), 'cal': _V3['jobs'][j].get('cal'), 'paper': _V3['jobs'][j].get('paper'), 'nocc': _V3['jobs'][j].get('nocc')} for j in range(N)],
        'R': {k: [R[k]['mid'], R[k]['k']] for k in R}}
json.dump(meta, open(os.path.join(WEB, ('task_' if TASKMODE else 'city_')+'meta.json'), 'w'), ensure_ascii=False)
if not TASKMODE:
    pass
    pass
os.makedirs(os.path.join(HERE, 'frames'), exist_ok=True)
years = list(np.arange(2023, 2032.001, .25))
for k, y in enumerate(years if os.environ.get('FRAMES') else []):
    frame(float(y), (900, 1200)).save(os.path.join(HERE, 'frames', f'f{k:03d}.png'))
print('ok', len(years))
