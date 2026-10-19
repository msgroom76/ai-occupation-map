import json,math
R=json.load(open('real_R.json'));p=lambda r,y:R[r][2]/(1+math.exp(-R[r][1]*(y-R[r][0])))
v3=json.load(open('bak21/jobs_v3.json'));SM=json.load(open('real_small2.json'))
occ=lambda w,c,y=2026:min(.99,c*sum(x*p(r,y) for r,x in w.items()))
for j in v3['jobs']:
    old=occ(j['w41'],j['cal'])
    parts=[(k or 0.01,SM[c]) for c,n,k in j['smalls']]
    C=sum(k*s['cal'] for k,s in parts);K=sum(k for k,_ in parts)
    acc={}
    for k,s in parts:
        for r,x in s['w'].items(): acc[r]=acc.get(r,0)+k*s['cal']*x/C
    j['w41']={r:round(x,4) for r,x in acc.items()};j['cal']=round(C/K,4)
    for f in ('e','il','ob','ms'):
        vs=[(k,s[f]) for k,s in parts if s[f] is not None]
        j[f]=round(sum(k*v for k,v in vs)/sum(k for k,_ in vs),4) if vs else None
    top=sorted(acc.items(),key=lambda kv:-kv[1])[:8];z=sum(x for _,x in top)
    j['tasks']={r:round(x/z,4) for r,x in top}
    print(j['code'],j['name'],'old',round(old*100),'eloundou',round(j['e']*100),'ilo',round(j['il']*100),'→ new',round(occ(j['w41'],j['cal'])*100),'| used',None if j['ob'] is None else round(j['ob']*100))
json.dump(v3,open('samples/jobs_v3.json','w'),ensure_ascii=False)
