"""조직 리포트 도표(그림체와 같은 잉크 한 색). python3 tools/report_charts.py reports/out/<회사>/metrics.json <사무 직무 id,...>"""
import json, os, sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
fp = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'; fb = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
for f in (fp, fb): fm.fontManager.addfont(f)
plt.rcParams['font.family'] = 'Noto Sans CJK JP'
INK = '#8a085a'; SOFT = '#e2b3cd'; TXT = '#16161a'; MUT = '#6b6b76'; BG = '#f6f6f8'; HAIR = '#d9d9de'
M = json.load(open(sys.argv[1])); od = os.path.dirname(sys.argv[1]); R = M['roles']; o = M['org']
off = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else set()
def style(ax):
    for s in ('top', 'right', 'left'): ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color(HAIR); ax.tick_params(colors=MUT, length=0); ax.set_facecolor(BG)
# 1. 두 집단: 인원 vs AI가 해낼 수 있는 업무량(명분), 2026·2030
G = [('사무·기술', [r for r in R if r['id'] in off]), ('현장', [r for r in R if r['id'] not in off])] if off else []
if G:
    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=200); fig.patch.set_facecolor(BG); style(ax)
    y = [1, 0]
    for i, (nm, S) in enumerate(G):
        n = sum(r['n'] for r in S); f = sum(r['fte'] for r in S); f30 = sum(r['fte30'] for r in S)
        ax.barh(y[i], n, color='none', edgecolor=MUT, height=.55, linewidth=1)
        ax.barh(y[i], f30, color=SOFT, height=.55); ax.barh(y[i], f, color=INK, height=.55)
        ax.text(n + .6, y[i], f'{n}명', va='center', color=TXT, fontsize=11)
        ax.text(f / 2, y[i], f'{f:.1f}', va='center', ha='center', color='white', fontsize=11, fontweight='bold')
        ax.text(f + (f30 - f) / 2, y[i], f'{f30:.1f}', va='center', ha='center', color=INK, fontsize=10)
    ax.set_yticks(y); ax.set_yticklabels([g[0] for g in G], fontsize=12, color=TXT); ax.set_xlim(0, max(sum(r['n'] for r in S) for _, S in G) * 1.15)
    ax.set_xlabel('테두리: 인원(명) · 진한 막대: AI 수행 가능 업무량 2026(FTE) · 옅은 막대: 2030(FTE)', color=MUT, fontsize=9)
    fig.tight_layout(); fig.savefig(f'{od}/chart_groups.png', facecolor=BG); plt.close(fig)
# 2. 조직 전체에서 AI가 해낼 업무 상위(명분), 대체형 진하게·보완형 옅게
T = o['tasks'][::-1]
fig, ax = plt.subplots(figsize=(8, 3.8), dpi=200); fig.patch.set_facecolor(BG); style(ax)
ax.barh(range(len(T)), [t['fte'] for t in T], color=[INK if t['type'] == '대체형' else SOFT for t in T], height=.62)
for i, t in enumerate(T): ax.text(t['fte'] + .05, i, f"{t['fte']:.1f} FTE · {t['type']}", va='center', fontsize=9, color=TXT if t['type'] == '대체형' else MUT)
ax.set_yticks(range(len(T))); ax.set_yticklabels([t['name'] for t in T], fontsize=11, color=TXT); ax.set_xticks([])
ax.set_xlim(0, max(t['fte'] for t in T) * 1.45)
fig.tight_layout(); fig.savefig(f'{od}/chart_tasks.png', facecolor=BG); plt.close(fig)
print('charts ok')
# 3. 직업 대분류 구성: 회사 vs 업종(지역별고용조사)
MJN = {'1': '관리자', '2': '전문가', '3': '사무', '4': '서비스', '5': '판매', '6': '농림어업', '7': '기능원', '8': '장치·조립', '9': '단순노무'}
peers_path = os.path.join('reports', M['company']['id'] + '_peers.json')
if os.path.exists(peers_path):
    P = json.load(open(peers_path)); IB = json.load(open('reports/industry_bench.json'))
    ind = IB['industry'][P['industry']]; mix = o['mix']
    ks = [k for k in MJN if mix.get(k, 0) > 0 or ind['mix'].get(k, 0) > .02]
    fig, ax = plt.subplots(figsize=(8, 3.4), dpi=200); fig.patch.set_facecolor(BG); style(ax)
    import numpy as np
    x = np.arange(len(ks)); w = .38
    ax.bar(x - w/2, [mix.get(k, 0) * 100 for k in ks], w, color=INK, label=M['company']['name'])
    ax.bar(x + w/2, [ind['mix'].get(k, 0) * 100 for k in ks], w, color=SOFT, label=P['industry'].split('(')[0].replace(' ', '').split('.')[-1] + ' 평균')
    for i, k in enumerate(ks):
        ax.text(i - w/2, mix.get(k, 0) * 100 + .8, f"{mix.get(k,0)*100:.0f}", ha='center', fontsize=8, color=TXT)
        ax.text(i + w/2, ind['mix'].get(k, 0) * 100 + .8, f"{ind['mix'].get(k,0)*100:.0f}", ha='center', fontsize=8, color=MUT)
    ax.set_xticks(x); ax.set_xticklabels([MJN[k] for k in ks], fontsize=10, color=TXT); ax.set_yticks([])
    ax.legend(frameon=False, fontsize=9, loc='upper left'); ax.set_ylabel('인원 비중(%)', color=MUT, fontsize=9)
    fig.tight_layout(); fig.savefig(f'{od}/chart_mix.png', facecolor=BG); plt.close(fig)
    # 4-b. 인원과 매출 시점이 달라 1인당 매출을 낼 수 없을 때: 매출 규모 + 영업이익률
    if P.get('metric') == 'margin':
        Q = sorted(P['peers'], key=lambda p: p['rev'])
        fig, ax = plt.subplots(figsize=(8, 2.8), dpi=200); fig.patch.set_facecolor(BG); style(ax)
        v = [p['rev'] / 100 for p in Q]
        ax.barh(range(len(Q)), v, color=[INK if p.get('self') else SOFT for p in Q], height=.6)
        for i, p in enumerate(Q):
            mg = p['op'] / p['rev'] * 100
            ax.text(v[i] + max(v) * .01, i, f"{v[i]:,.0f}억 원 · 영업이익률 {mg:+.1f}%", va='center', fontsize=9, color=TXT)
        ax.set_yticks(range(len(Q))); ax.set_yticklabels([p['name'] for p in Q], fontsize=11, color=TXT); ax.set_xticks([]); ax.set_xlim(0, max(v) * 1.55)
        fig.tight_layout(); fig.savefig(f'{od}/chart_peers.png', facecolor=BG); plt.close(fig)
        print('peer charts ok (margin)'); sys.exit(0)
    # 4. 1인당 매출(같은 해 인원만)
    Q = [p for p in P['peers'] if p.get('n') and not p.get('nodate')]
    Q.sort(key=lambda p: p['rev'] / p['n'])
    fig, ax = plt.subplots(figsize=(8, 2.6), dpi=200); fig.patch.set_facecolor(BG); style(ax)
    v = [p['rev'] / p['n'] / 100 for p in Q]
    ax.barh(range(len(Q)), v, color=[INK if p.get('self') else SOFT for p in Q], height=.6)
    for i, p in enumerate(Q): ax.text(v[i] + .1, i, f"{v[i]:.1f}억 원 · {p['n']:,}명", va='center', fontsize=9, color=TXT)
    ax.set_yticks(range(len(Q))); ax.set_yticklabels([p['name'] for p in Q], fontsize=11, color=TXT); ax.set_xticks([]); ax.set_xlim(0, max(v) * 1.35)
    fig.tight_layout(); fig.savefig(f'{od}/chart_peers.png', facecolor=BG); plt.close(fig)
    print('peer charts ok')
