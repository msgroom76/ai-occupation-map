import os, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import patheffects as pe
from matplotlib.colors import LinearSegmentedColormap
from scipy.ndimage import gaussian_filter

OUT = os.path.dirname(os.path.abspath(__file__))
SANS, SERIF = 'Noto Sans CJK KR', 'Noto Serif CJK KR'
plt.rcParams['font.family'] = SANS

# ---------- 데이터 (프로토타입과 동일한 가상 데이터) ----------
R = {}
for a in [
 ['A1',3.2,2026.0,.9],['A2',3.0,2029,.7],['A3',2.6,2028,.8],['A4',2.8,2029.5,.7],['A5',2.0,2026.8,.9],
 ['B1',2.4,2028,.7],['B2',3.6,2025.6,1.0],['B3',2.2,2027.5,.8],['B4',2.6,2025.8,1.0],['B5',3.0,2029,.6],['B6',2.4,2028.2,.7],['B7',2.6,2027,.8],['B8',2.0,2030,.6],['B9',1.8,2025.9,1.0],['B10',2.4,2027.2,.8],
 ['C1',5.0,2033,.55],['C2',4.6,2031,.6],['C3',3.2,2029.5,.7],['C4',3.8,2031.5,.6],['C5',5.2,2025.4,1.0],['C6',1.4,2027.8,.8],['C7',2.2,2033.5,.55],['C8',1.2,2032,.6],['C9',3.4,2025.2,1.1],
 ['D1',2.0,2027,.8],['D2',2.6,2030,.6],['D3',2.4,2028,.7],['D4',1.8,2034,.5],['D5',2.8,2035,.45],['D6',2.6,2028.5,.7],['D7',1.4,2033,.5],['D8',0.9,2032,.5],['D9',1.6,2030.5,.6],['D10',0.9,2034,.5],['D11',1.8,2029.5,.6],['D12',1.2,2034,.5],['D13',1.0,2032.5,.55],['D14',1.6,2029,.65],['D15',2.6,2025.5,1.0],['D16',0.8,2028.5,.7],['D17',1.2,2029.5,.6]]:
    R[a[0]] = dict(mid=a[2], k=a[3])
p = lambda r, y: .92 / (1 + np.exp(-R[r]['k'] * (y - R[r]['mid'])))

JOBS = [
 ('경영관련 사무원',250,{'C9':.2,'B2':.3,'C5':.15,'D15':.15,'B9':.1,'D2':.1}),
 ('매장 판매원',155,{'D6':.3,'D3':.25,'C2':.2,'A5':.15,'B2':.1}),
 ('작물재배 종사자',130,{'C1':.5,'C4':.15,'A2':.15,'A5':.1,'B9':.1}),
 ('운전 종사자',95,{'C4':.6,'A2':.15,'D3':.1,'B9':.1,'C9':.05}),
 ('건설 기능원',75,{'C1':.45,'C2':.2,'A4':.15,'C6':.1,'D2':.1}),
 ('음식 서비스원',70,{'D3':.45,'C2':.25,'C1':.15,'B2':.15}),
 ('회계·경리 사무원',70,{'B2':.35,'B4':.2,'C9':.2,'B3':.15,'C5':.1}),
 ('요양보호사',60,{'D5':.6,'C1':.2,'A2':.1,'C9':.1}),
 ('청소원',60,{'C1':.6,'C2':.2,'A4':.1,'D2':.1}),
 ('조리사',55,{'C1':.4,'C2':.2,'B1':.1,'A5':.1,'D2':.2}),
 ('교사',50,{'D11':.35,'D4':.2,'B7':.15,'B1':.1,'D15':.1,'D14':.1}),
 ('보안·경비원',45,{'A2':.5,'A3':.2,'D3':.15,'C1':.15}),
 ('소프트웨어 개발자',45,{'C5':.3,'B5':.25,'B6':.2,'B4':.1,'C9':.05,'D2':.1}),
 ('자동차 조립 노동자',40,{'C2':.35,'C3':.2,'A4':.2,'C1':.15,'C9':.05,'D2':.05}),
 ('금융 사무원',40,{'B2':.3,'B3':.2,'D3':.2,'C9':.15,'C5':.15}),
 ('행정 공무원',40,{'D15':.4,'B3':.2,'C9':.2,'D3':.2}),
 ('배달·택배원',40,{'C4':.4,'C2':.35,'D3':.15,'B9':.1}),
 ('영업원',35,{'D6':.45,'D3':.25,'D7':.1,'B8':.1,'C9':.1}),
 ('설비 정비 기술자',35,{'C7':.35,'A4':.2,'C8':.15,'B5':.1,'C9':.1,'C3':.1}),
 ('품질 검사원',30,{'A4':.45,'B3':.2,'A3':.2,'C9':.15}),
 ('경영·기획 관리자',30,{'B8':.3,'B5':.2,'D9':.2,'D12':.15,'B4':.15}),
 ('물류 창고 작업원',30,{'C2':.55,'A5':.15,'C3':.15,'C9':.15}),
 ('간호사',28,{'D5':.35,'A2':.2,'C1':.15,'C9':.15,'D1':.1,'B5':.05}),
 ('디자이너',25,{'B6':.45,'C6':.25,'D3':.15,'C5':.15}),
 ('고객센터 상담원',25,{'D3':.4,'B2':.2,'D14':.15,'C5':.15,'D7':.1}),
 ('보육교사',25,{'D5':.4,'D11':.25,'D4':.2,'C9':.15}),
 ('전기·전자 기술자',25,{'C8':.4,'A4':.2,'B5':.15,'C9':.15,'C6':.1}),
 ('사회복지사',15,{'D14':.35,'D5':.25,'D15':.2,'C9':.2}),
 ('의사',12,{'B5':.3,'A3':.2,'D14':.2,'D5':.15,'C9':.15}),
 ('법률 전문가',8,{'B3':.3,'B5':.2,'A1':.2,'D14':.15,'C9':.15}),
 ('기자',6,{'A1':.4,'B6':.2,'C9':.2,'D3':.2}),
]
N = len(JOBS)
names = [j[0] for j in JOBS]; ws = np.array([j[1] for j in JOBS], float)
occ = lambda i, y: sum(s * p(r, y) for r, s in JOBS[i][2].items())
cshare = []
for _, _, t in JOBS:
    c = {'A':0,'B':0,'C':0,'D':0}
    for r, s in t.items(): c[r[0]] += s
    cshare.append(c)
dom = [max(c, key=c.get) for c in cshare]

# 업무 유사도 → 배치 (비슷한 직업끼리 가깝게, 대륙별로 묶음)
S = np.zeros((N, N))
for i in range(N):
    for j in range(N):
        a, b = JOBS[i][2], JOBS[j][2]
        t = sum(min(a[r], b[r]) for r in a if r in b)
        c = sum(min(cshare[i][k], cshare[j][k]) for k in 'ABCD')
        S[i, j] = .6 * t + .4 * c
D = 1 - S
J = np.eye(N) - 1 / N
B = -.5 * J @ (D ** 2) @ J
w, v = np.linalg.eigh(B)
mds = v[:, -2:] * np.sqrt(np.maximum(w[-2:], 0))
mds = (mds - mds.min(0)) / (mds.max(0) - mds.min(0))
QC = {'A': (.27, .80), 'B': (.73, .74), 'C': (.27, .27), 'D': (.73, .24)}
pos = np.array([.62 * np.array(QC[dom[i]]) + .38 * mds[i] for i in range(N)])
rng = np.random.default_rng(7)
pos += rng.normal(0, .015, pos.shape)
for _ in range(400):
    for i in range(N):
        for j in range(i + 1, N):
            d = pos[i] - pos[j]; L = np.hypot(*d) + 1e-9
            if L < .105:
                m = (.105 - L) / 2 * d / L; pos[i] += m; pos[j] -= m
    pos = np.clip(pos, .1, .9)
pos = (pos - pos.min(0)) / (pos.max(0) - pos.min(0)) * [.8, .84] + [.1, .08]
W_, H_ = 1.0, 1.25
P = pos * [W_, H_]

nx, ny = 540, 675
X, Y = np.meshgrid(np.linspace(0, W_, nx), np.linspace(0, H_, ny))
dist = np.stack([np.hypot(X - x, Y - y) for x, y in P])
label = dist.argmin(0)
def edges(lbl):
    e = np.zeros(lbl.shape, bool)
    e[:, 1:] |= lbl[:, 1:] != lbl[:, :-1]; e[1:, :] |= lbl[1:, :] != lbl[:-1, :]
    return e
halo = lambda c, w=2.2: [pe.withStroke(linewidth=w, foreground=c)]
noise = gaussian_filter(rng.normal(size=(ny, nx)), 9); noise /= np.abs(noise).max()
sig = .045 + .075 * np.sqrt(ws / ws.max())
Hl = np.max([np.exp(-((X - P[i, 0]) ** 2 + (Y - P[i, 1]) ** 2) / (2 * (sig[i] * 1.55 + .02) ** 2)) for i in range(N)], 0)
Hl = Hl + .22 * noise
land = Hl > .42

def frame(bg):
    fig = plt.figure(figsize=(7.2, 9), dpi=150, facecolor=bg)
    ax = fig.add_axes([0.04, 0.03, 0.92, 0.80]); ax.set_xlim(0, W_); ax.set_ylim(0, H_); ax.axis('off')
    return fig, ax
def head(fig, kicker, title, sub, fg, acc, sub_c):
    fig.text(.05, .955, kicker, color=acc, fontsize=10, fontweight='bold')
    fig.text(.05, .915, title, color=fg, fontsize=21, fontfamily=SERIF, fontweight='bold', va='center')
    fig.text(.05, .872, sub, color=sub_c, fontsize=9.5)

# ---------- 1. 차오르는 물 ----------
Y1 = 2030; LVL = .36
A = np.array([1 - occ(i, Y1) for i in range(N)])
sig = .045 + .075 * np.sqrt(ws / ws.max())
Hf = np.max([A[i] * np.exp(-((X - P[i, 0]) ** 2 + (Y - P[i, 1]) ** 2) / (2 * sig[i] ** 2)) for i in range(N)], 0)
Hf = Hf + .07 * noise * np.clip(Hf * 3, 0, 1)
sea_c = LinearSegmentedColormap.from_list('s', ['#2E5560', '#173039', '#0D1C22'])
land_c = LinearSegmentedColormap.from_list('l', ['#E7EBDF', '#C9D3BE', '#94A88E', '#5F7660'])
img = np.zeros((ny, nx, 4))
sea = Hf < LVL
img[sea] = sea_c(np.clip((LVL - Hf[sea]) / LVL * 1.6, 0, 1))
img[~sea] = land_c(np.clip((Hf[~sea] - LVL) / (1 - LVL) * 1.4, 0, 1))
fig, ax = frame('#0D1C22')
ax.imshow(img, origin='lower', extent=(0, W_, 0, H_), interpolation='bilinear')
ax.contour(X, Y, Hf, levels=[LVL - .12, LVL - .07, LVL - .03], colors='#7FA3AB', linewidths=.5, alpha=.45)
ax.contour(X, Y, Hf, levels=np.arange(LVL + .08, 1, .08), colors='#3F5241', linewidths=.4, alpha=.55)
ax.contour(X, Y, Hf, levels=[LVL], colors='#F4F6F0', linewidths=1.3)
fog = gaussian_filter(rng.random((ny, nx)), 22); fog = (fog - fog.min()) / (fog.max() - fog.min())
fogimg = np.zeros((ny, nx, 4)); fogimg[..., :3] = 1; fogimg[..., 3] = np.clip(fog - .45, 0, 1) * .35
ax.imshow(fogimg, origin='lower', extent=(0, W_, 0, H_), interpolation='bilinear')
for i in range(N):
    x, y = P[i]
    if A[i] > LVL + .02:
        ax.text(x, y + .012, names[i], ha='center', va='bottom', fontsize=7.6, fontweight='bold', color='#16211B', path_effects=halo('#EEF2EA'))
        ax.text(x, y - .004, f'남은 땅 {A[i]*100:.0f}%', ha='center', va='top', fontsize=6.3, color='#2B3A30', path_effects=halo('#EEF2EA', 1.8))
    else:
        ax.text(x, y, names[i] + '\n잠김', ha='center', va='center', fontsize=6.6, color='#8FB0B8', fontstyle='italic', linespacing=1.1)
head(fig, '방향 1 · 차오르는 물', '2030년, 물이 여기까지 찼다', '섬의 높이 = 사람이 아직 필요한 정도 · 낮은 직업부터 잠김 · 안개 = 예측 구간 · 시연용 가상 데이터', '#F4F6F0', '#E8826B', '#9DB6BC')
fig.savefig(f'{OUT}/1_water.png', facecolor=fig.get_facecolor()); plt.close(fig)

# ---------- 2. 전선 지도 ----------
Y2 = 2026
o2 = np.array([occ(i, Y2) for i in range(N)])
hi, mid_ = np.quantile(o2, .68), np.quantile(o2, .42)
state = np.where(o2 >= hi, 2, np.where(o2 >= mid_, 1, 0))
st = np.where(land, state[label], -1)
img = np.ones((ny, nx, 3)); img[~land] = [.98, .98, .97]
img[st == 2] = [.08, .08, .08]
stripes = ((np.arange(nx)[None, :] + np.arange(ny)[:, None]) // 5) % 2 == 0
img[(st == 1) & stripes] = [.15, .15, .15]
img[edges(label) & land] = [.62, .62, .62]
img[edges(land.astype(int))] = [.1, .1, .1]
fig, ax = frame('#FAFAF8')
ax.imshow(img, origin='lower', extent=(0, W_, 0, H_), interpolation='nearest')
front = gaussian_filter((st == 2).astype(float), 2.2)
ax.contour(X, Y, front, levels=[.5], colors='#C4301C', linewidths=2.8)
occ_idx = np.where(state == 2)[0]
cont_idx = np.where(state == 1)[0]
dmin = [np.hypot(*(P[occ_idx] - P[i]).T).min() for i in cont_idx]
picks = cont_idx[np.argsort(dmin)[:3]]
for i, g in zip(picks, ['+4%p', '+3%p', '+5%p']):
    k = occ_idx[np.argmin(np.hypot(*(P[occ_idx] - P[i]).T))]
    s, e = P[k], P[i]; e2 = s + (e - s) * .78; s2 = s + (e - s) * .25
    ax.annotate('', xy=e2, xytext=s2, arrowprops=dict(arrowstyle='-|>,head_width=.5,head_length=.9', color='#C4301C', lw=3.2, shrinkA=0, shrinkB=0))
    ax.text(e2[0] + .035, e2[1] + .025, g, ha='left', va='bottom', fontsize=8, fontweight='bold', color='#C4301C', path_effects=halo('white'))
for i in range(N):
    x, y = P[i]; dark = state[i] == 2
    ax.text(x, y, names[i], ha='center', va='center', fontsize=7.4, fontweight='bold',
            color='white' if dark else '#111', path_effects=halo('#111' if dark else 'white'))
head(fig, '방향 2 · 전선', '이번 주, 전선은 세 곳에서 밀렸다', '검정 = 점령 · 빗금 = 물드는 중 · 흰색 = 사람의 땅 · 빨간 선 = 전선 · 화살표 = 이번 주 이동', '#111', '#C4301C', '#555')
fig.savefig(f'{OUT}/2_front.png', facecolor=fig.get_facecolor()); plt.close(fig)

# ---------- 3. 판타지 지도 ----------
o3 = np.array([occ(i, 2026) for i in range(N)])
Hl = np.max([np.exp(-((X - P[i, 0]) ** 2 + (Y - P[i, 1]) ** 2) / (2 * (sig[i] * 1.55 + .02) ** 2)) for i in range(N)], 0)
Hl = Hl + .22 * noise
land = Hl > .42
tint = {'A': [.86, .85, .78], 'B': [.83, .86, .80], 'C': [.88, .83, .76], 'D': [.85, .82, .84]}
red = np.array([.62, .18, .12])
img = np.zeros((ny, nx, 3)); img[:] = [.80, .86, .88]
for i in range(N):
    m = land & (label == i)
    f = min(o3[i] * .85, .8)
    img[m] = np.array(tint[dom[i]]) * (1 - f) + red * f
e = edges(np.where(land, label, -1)) & land
img[e & (((np.arange(nx)[None, :] + np.arange(ny)[:, None]) // 3) % 2 == 0)] = [.35, .3, .28]
fig, ax = frame('#CCDADE')
ax.imshow(img, origin='lower', extent=(0, W_, 0, H_), interpolation='bilinear')
lf = gaussian_filter(land.astype(float), 1.5)
ax.contour(X, Y, lf, levels=[.5], colors='#3B3430', linewidths=1.2)
for k, lv in enumerate([.32, .2, .11, .05]):
    ax.contour(X, Y, gaussian_filter(land.astype(float), 6 + k * 5), levels=[lv], colors='#6E8C96', linewidths=.55, alpha=.7 - k * .12)
for c, nm in [('A', '알아차림의 땅'), ('B', '판단의 대륙'), ('C', '손과 몸의 대륙'), ('D', '사람의 대륙')]:
    idx = [i for i in range(N) if dom[i] == c]
    cx, cy = np.average(P[idx], axis=0, weights=ws[idx])
    ax.text(cx, cy, ' '.join(nm), ha='center', va='center', fontsize=17, fontfamily=SERIF, fontweight='bold', color='#3B3430', alpha=.28, zorder=1)
nick = {'경영관련 사무원': '반복 사무 저지대', '요양보호사': '돌봄 고원', '소프트웨어 개발자': '코드 해안', '매장 판매원': '판매 항구', '운전 종사자': '운전 평원'}
for i in range(N):
    x, y = P[i]
    ax.text(x, y, names[i], ha='center', va='center', fontsize=6.6, fontfamily=SERIF, color='#2A2420', path_effects=halo('#EFEAE0', 1.8))
    if names[i] in nick:
        ax.text(x, y - .028, nick[names[i]], ha='center', va='top', fontsize=8.4, fontfamily=SERIF, fontstyle='italic', fontweight='bold', color='#8E2A1C', path_effects=halo('#EFEAE0', 2.2))
seaY, seaX = np.unravel_index(np.argmax(gaussian_filter((~land).astype(float), 25)), land.shape)
ax.text(X[0, seaX], Y[seaY, 0], '자 동 화 의  바 다', ha='center', fontsize=11, fontfamily=SERIF, fontstyle='italic', color='#4E6F79', rotation=8)
cx, cy, r = .08, .07, .045
for ang in range(0, 360, 45):
    a = np.deg2rad(ang); rr = r if ang % 90 == 0 else r * .5
    ax.plot([cx, cx + rr * np.sin(a)], [cy, cy + rr * np.cos(a)], color='#3B3430', lw=1.4 if ang % 90 == 0 else .7)
ax.text(cx, cy + r + .012, 'N', ha='center', fontsize=7.5, fontfamily=SERIF, color='#3B3430')
head(fig, '방향 3 · 판타지 지도', '일의 대륙, 2026년 10월', '나라 = 직업 · 크기 = 종사자 수 · 붉게 물든 땅 = AI 점령 · 지형 이름으로 성격을 전달', '#2A2420', '#8E2A1C', '#4E5A5E')
fig.savefig(f'{OUT}/3_fantasy.png', facecolor=fig.get_facecolor()); plt.close(fig)

# ---------- 4. 연결망 + 탈출 경로 ----------
fig, ax = frame('#10171A')
cm = LinearSegmentedColormap.from_list('o', ['#DCE6E1', '#E9A48F', '#C2412B', '#7E1F14'])
for i in range(N):
    for j in range(i + 1, N):
        t = sum(min(JOBS[i][2][r], JOBS[j][2][r]) for r in JOBS[i][2] if r in JOBS[j][2])
        if t >= .2:
            ax.plot(*zip(P[i], P[j]), color='#5D7378', lw=.4 + t * 3, alpha=.35 + t * .5, zorder=1)
a, b = names.index('자동차 조립 노동자'), names.index('설비 정비 기술자')
ax.annotate('', xy=P[b], xytext=P[a], arrowprops=dict(arrowstyle='-|>,head_width=.6,head_length=1.1', color='#7DDBB5', lw=3.4, shrinkA=16, shrinkB=18, connectionstyle='arc3,rad=-.3'), zorder=4)
ov = sum(min(JOBS[a][2][r], JOBS[b][2][r]) for r in JOBS[a][2] if r in JOBS[b][2])
mx = (P[a] + P[b]) / 2
ax.text(P[b][0] + .05, P[b][1] - .09, f'탈출 경로\n겹치는 업무 {ov*100:.0f}%\n2030년 점령 {occ(a,2030)*100:.0f}% → {occ(b,2030)*100:.0f}%', fontsize=8, color='#7DDBB5', fontweight='bold', va='center', linespacing=1.3, path_effects=halo('#10171A', 3), zorder=5)
for i in range(N):
    o = occ(i, 2030)
    ax.scatter(*P[i], s=40 + ws[i] * 5.5, color=cm(float(min(o / .8, 1.0))), edgecolor='#10171A', lw=1.5, zorder=3)
    ax.text(P[i, 0], P[i, 1] - .022 - np.sqrt(ws[i]) * .0035, names[i], ha='center', va='top', fontsize=6.8, color='#E6EEEA', path_effects=halo('#10171A', 2.4), zorder=4)
head(fig, '방향 4 · 연결망', '비슷한 일은 가까이, 길은 선으로', '점 = 직업 · 크기 = 종사자 수 · 색 = 2030년 예상 점령률 · 선 굵기 = 겹치는 업무 · 초록 화살표 = 탈출 경로', '#E6EEEA', '#7DDBB5', '#8FA3A8')
fig.savefig(f'{OUT}/4_network.png', facecolor=fig.get_facecolor()); plt.close(fig)
print('done', np.round(A, 2).min(), (A > LVL).sum(), state.sum())
