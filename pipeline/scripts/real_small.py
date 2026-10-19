import csv,json,collections,math
src=open('real_profiles2.py').read().split("out={}")[0]
src=src.replace("exec(open('soc_map.py').read())","exec(open('soc_map.py').read());exec(open('soc_map_small.py').read())")
exec(src)  # occw, OL, EMP, TITLE, bysoc
sm=collections.defaultdict(collections.Counter);smw=collections.Counter();smE=collections.defaultdict(lambda:[0,0]);smocc=collections.defaultdict(list)
for soc,cs in bysoc.items():
    k=small_of(soc)
    if not k: continue
    e=EMP.get(soc) or next((v for kk,v in EMP.items() if kk[:6]==soc[:6]),1000.0)
    for c in cs:
        w=e/len(cs)
        if c in occw:
            z=sum(occw[c].values())
            for g,v in occw[c].items(): sm[k][g]+=w*v/z
            smw[k]+=w; smocc[k].append((w,TITLE.get(c,c)))
        if c in OL: smE[k][0]+=w*OL[c]['beta'];smE[k][1]+=w
R=json.load(open('real_R.json'));p=lambda r,y:R[r][2]/(1+math.exp(-R[r][1]*(y-R[r][0])))
meta=json.load(open('bak21/jobs_v3.json'))  # 원래 web/city_meta.json. 당시 jobs의 w41·cal·smalls·code는 bak21/jobs_v3.json과 같다
out={};rows=[]
for j in meta['jobs']:
    par={'w':j['w41'],'cal':j['cal']}
    parv=min(.99,j['cal']*sum(x*p(r,2026) for r,x in j['w41'].items()))
    for code,name,emp in j['smalls']:
        if code in sm and len(j['smalls'])>1:
            z=sum(sm[code].values());w={g:round(v/z,4) for g,v in sm[code].items()}
            base=sum(x*p(r,2026) for r,x in w.items());cap=sum(x*R[r][2] for r,x in w.items())
            beta=smE[code][0]/smE[code][1] if smE[code][1] else None
            cal=min((beta or base)/base,.97/cap)
            occ=min(.99,cal*base)
            occs=sorted(smocc[code],reverse=True)
            out[code]={'w':w,'cal':round(cal,4),'n':len(occs),'basis':[t for _,t in occs[:3]]}
            rows.append((j['code'],code,name,emp,round(occ*100),round(parv*100),len(occs)))
        else:
            out[code]={'same':1}
            rows.append((j['code'],code,name,emp,None,round(parv*100),0))
json.dump(out,open('real_small.json','w'),ensure_ascii=False)
for r in rows: print(*r)
print('computed',sum(1 for v in out.values() if 'w' in v),'inherit',sum(1 for v in out.values() if 'same' in v))
# 가중 평균 검증: 소분류 가중 평균 vs 중분류 값
