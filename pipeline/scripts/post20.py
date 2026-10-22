import json,math
m=json.load(open('web/city_meta.json'));R=json.load(open('real_R.json'));det=json.load(open('real_detail.json'))
m['R']=R
p=lambda r,y:R[r][2]/(1+math.exp(-R[r][1]*(y-R[r][0])))
D={}
for n,d in det.items():
    w=d['w41'];base=sum(x*p(r,2026) for r,x in w.items());cap=sum(x*R[r][2] for r,x in w.items())
    cal=min((d['beta'] or base)/base,.97/cap);D[n]={'w':w,'cal':round(cal,4)}
m['detail']=D
m['src']={'exposure':'Eloundou, Manning, Mishkin, Rock (2024) GPTs are GPTs, Science 384:1306. 공개 데이터 github.com/openai/GPTs-are-GPTs (MIT)','tasks':'O*NET 31.0 (미국 노동부, 2026.8), Task Statements·Task Ratings·Tasks to DWAs·Work Activities','weights':'미국 OEWS 2021.5 직업별 고용','workers':'국가데이터처 지역별고용조사 2025년 하반기'}
json.dump(m,open('web/city_meta.json','w'),ensure_ascii=False,separators=(',',':'))
tot=sum(j['ws']*j['cal']*sum(x*p(r,2026) for r,x in j['w41'].items()) for j in m['jobs'])/sum(j['ws'] for j in m['jobs'])
print('total 2026',round(tot*100,1),'jobs',len(m['jobs']),'tasks per job max',max(len(j['tasks']) for j in m['jobs']))
