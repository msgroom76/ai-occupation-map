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
    ax.set_xlabel('사람 수(명) · 진한 칸: 2026년 AI가 해낼 수 있는 업무량(명분) · 옅은 칸: 2030년', color=MUT, fontsize=9)
    fig.tight_layout(); fig.savefig(f'{od}/chart_groups.png', facecolor=BG); plt.close(fig)
# 2. 조직 전체에서 AI가 해낼 업무 상위(명분), 대체형 진하게·보완형 옅게
T = o['tasks'][::-1]
fig, ax = plt.subplots(figsize=(8, 3.8), dpi=200); fig.patch.set_facecolor(BG); style(ax)
ax.barh(range(len(T)), [t['fte'] for t in T], color=[INK if t['type'] == '대체형' else SOFT for t in T], height=.62)
for i, t in enumerate(T): ax.text(t['fte'] + .05, i, f"{t['fte']:.1f}명분 · {t['type']}", va='center', fontsize=9, color=TXT if t['type'] == '대체형' else MUT)
ax.set_yticks(range(len(T))); ax.set_yticklabels([t['name'] for t in T], fontsize=11, color=TXT); ax.set_xticks([])
ax.set_xlim(0, max(t['fte'] for t in T) * 1.45)
fig.tight_layout(); fig.savefig(f'{od}/chart_tasks.png', facecolor=BG); plt.close(fig)
print('charts ok')
