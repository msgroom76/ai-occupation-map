import json
m=json.load(open('web/city_meta.json')); old=json.load(open('bak18/city_meta.json')); v3=json.load(open('samples/jobs_v3.json'))
oks=json.load(open('bak18/ksco_titles.json'))
m['RN']=old['RN']
RI={j['code']:i for i,j in enumerate(m['jobs'])}
OLDN=[j['name'] for j in old['jobs']]
RN=old['RN']
m['detail']={n:[[RN[r][0],r,w] for r,w in d.items()] for n,d in v3['old'].items()}
# 일상 직업명: 지역 이름 → [[이름, 세부직업]]
T={}
for on,code in v3['o2m'].items():
    rn=m['jobs'][RI[code]]['name']
    T.setdefault(rn,[]).append([on,on])
    for t in v3['titles'].get(on,[]): T[rn].append([t,on])
m['titles']=T
json.dump(m,open('web/city_meta.json','w'),ensure_ascii=False,separators=(',',':'))
codes={}
for c,(n,j,e) in oks['codes'].items():
    mid=c[:2]
    if mid not in RI: print('skip',c,n); continue
    codes[c]=[n,RI[mid],OLDN[j] if e else None]
titles=[t for t in oks['titles'] if t[1] in codes]
json.dump({'src':oks['src'],'codes':codes,'titles':titles},open('web/ksco_titles.json','w'),ensure_ascii=False,separators=(',',':'))
print(len(codes),len(titles),sum(len(v) for v in T.values()))
import numpy as np
from PIL import Image
from scipy import ndimage as nd
idx=np.array(Image.open('web/city_index.png'))[...,0]
m=json.load(open('web/city_meta.json'))
for i,j in enumerate(m['jobs']):
    if j['label'] is None:
        mk=idx==i; e=nd.distance_transform_edt(mk); y,x=np.unravel_index(e.argmax(),e.shape)
        j['label']=[float(x),float(y),12.0]; print('label fallback',j['name'],x,y,int(mk.sum()))
json.dump(m,open('web/city_meta.json','w'),ensure_ascii=False,separators=(',',':'))
