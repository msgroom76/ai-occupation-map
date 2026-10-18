"""주간 지수 발표: feed.json의 st=pending 소식을 반영해 index.json에 새 주를 추가한다.
사용: python3 tools/weekly.py 2026-10-19   (발표일, 월요일)"""
import json,math,sys,datetime as dt
D=sys.argv[1] if len(sys.argv)>1 else dt.date.today().isoformat()
feed=json.load(open('feed.json'));idx=json.load(open('index.json'));cm=json.load(open('city_meta.json'))
SHIFT={'1차 출처':.25,'신뢰 매체':1/12,'확인 필요':0}
last=idx['weeks'][-1];adj=dict(last['adj']);applied=[]
y,w,_=dt.date.fromisoformat(D).isocalendar();wk=f'{y}-W{w:02d}'
if last['week']==wk: sys.exit(f'{wk} 이미 발표됨')
for n in feed['items']:
    if n.get('st')!='pending' or not n.get('r'):continue
    sh=SHIFT[n['tier']]*(.5 if n.get('us') else 1)
    if sh<=0:continue
    for r in n['r']:adj[r]=round(adj.get(r,0)+sh,4)
    n['st']='applied';n['wk']=wk;applied.append(n['id'])
R=cm['R']
def p(r,yr):m,k=R[r];return .92/(1+math.exp(-k*(yr-m+adj.get(r,0))))
def occ(j,yr):t=j['tasks'];return sum(x[2]*p(x[1],yr) for x in t)/sum(x[2] for x in t)
tot=sum(j['ws']*occ(j,2026) for j in cm['jobs'])/sum(j['ws'] for j in cm['jobs'])
if last.get('total') is None and len(idx['weeks'])==1:
    adj0={};
    def p0(r,yr):m,k=R[r];return .92/(1+math.exp(-k*(yr-m)))
    last['total']=round(sum(j['ws']*sum(x[2]*p0(x[1],2026) for x in j['tasks'])/sum(x[2] for x in j['tasks']) for j in cm['jobs'])/sum(j['ws'] for j in cm['jobs']),5)
idx['weeks'].append({'week':wk,'date':D,'adj':adj,'total':round(tot,5),'applied':applied})
json.dump(idx,open('index.json','w'),ensure_ascii=False,indent=1);json.dump(feed,open('feed.json','w'),ensure_ascii=False,indent=1)
print(wk,'total',round(tot*100,2),'applied',len(applied),'prev',last['total'])
