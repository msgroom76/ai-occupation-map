"""소식 보관: feed.json에서 오래된 소식을 지우지 않고 archive/news.json으로 옮긴다(소식 페이지가 둘을 합쳐 보여준다).
사용: python3 tools/archive_feed.py            (소식 갱신 워크플로가 Claude 작업 뒤에 돌린다)
      python3 tools/archive_feed.py --history  (처음 한 번: git 기록에서 예전에 지워진 소식을 되살려 보관함에 넣는다)
옮기는 기준(지도·주간 지수가 쓰는 것은 feed.json에 남긴다):
- items: 기준 발표(base)가 아니고, 대기(pending)가 아니며, 날짜(ts)가 91일(13주)보다 오래된 것
- front: 날짜(ts)가 1년보다 오래된 것
보관함의 항목은 고치거나 지우지 않는다. 같은 id가 다시 들어오면 새 것으로 바꾼다."""
import json, os, sys, subprocess, datetime as dt
KST = dt.timezone(dt.timedelta(hours=9))
P = 'archive/news.json'
now = dt.datetime.now(KST)
feed = json.load(open('feed.json'))
arc = json.load(open(P)) if os.path.exists(P) else {'about': '오래된 AI 소식 보관함. 형식은 feed.json과 같다(PIPELINE.md). tools/archive_feed.py가 관리한다.', 'items': [], 'front': []}
def old(n, days):
    try: return (now - dt.datetime.fromisoformat(n['ts'])).days > days
    except Exception: return False
def put(kind, n):
    lst = arc[kind]; ids = [x['id'] for x in lst]
    if n['id'] in ids: lst[ids.index(n['id'])] = n
    else: lst.append(n)
moved = {'items': 0, 'front': 0}
keep = []
for n in feed['items']:
    if not n.get('base') and n.get('st') != 'pending' and old(n, 91): put('items', n); moved['items'] += 1
    else: keep.append(n)
feed['items'] = keep
keepf = []
for n in feed.get('front', []):
    if old(n, 365): put('front', n); moved['front'] += 1
    else: keepf.append(n)
feed['front'] = keepf
rescued = 0
if '--history' in sys.argv:  # 예전 정리 규칙(최근 60건)으로 지워진 소식 되살리기
    live = {n['id'] for k in ('items', 'front') for n in feed[k]} | {n['id'] for k in ('items', 'front') for n in arc[k]}
    for h in subprocess.run(['git', 'log', '--format=%h', '--', 'feed.json'], capture_output=True, text=True).stdout.split():
        try: f = json.loads(subprocess.run(['git', 'show', f'{h}:feed.json'], capture_output=True, text=True).stdout)
        except Exception: continue
        for n in f.get('items', []) if isinstance(f, dict) else []:  # 쟁점은 독립 검토에서 보류돼 빠진 것이라 되살리지 않는다
            if n.get('id') and n['id'] not in live and not n.get('base'): put('items', n); live.add(n['id']); rescued += 1
for k in ('items', 'front'): arc[k].sort(key=lambda n: n.get('ts', ''), reverse=True)
os.makedirs('archive', exist_ok=True)
json.dump(arc, open(P + '.tmp', 'w'), ensure_ascii=False, indent=1)
json.dump(feed, open('feed.json.tmp', 'w'), ensure_ascii=False, indent=1)
os.replace(P + '.tmp', P); os.replace('feed.json.tmp', 'feed.json')
print(f"보관함으로 옮김: 진격 {moved['items']}건, 쟁점 {moved['front']}건" + (f", 기록에서 되살림 {rescued}건" if rescued else '') + f" · 보관함 진격 {len(arc['items'])} · 쟁점 {len(arc['front'])}")
