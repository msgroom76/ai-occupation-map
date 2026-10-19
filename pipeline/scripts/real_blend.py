import json,math,pandas as pd,numpy as np
exec(open('ksco_isco_manual.py').read());I0=dict(I)
exec(open('ksco_isco.py').read())
for _c in I0:
    I.setdefault(_c,I0[_c])
g=pd.read_csv('isco_occ.csv');IL={int(r.ISCO_08):float(r.m) for _,r in g.iterrows()}
R=json.load(open('real_R.json'));p=lambda r,y:R[r][2]/(1+math.exp(-R[r][1]*(y-R[r][0])))
v3=json.load(open('bak21/jobs_v3.json'));SM=json.load(open('real_small.json'));U=json.load(open('usage_agg.json'))
out={}
for j in v3['jobs']:
    for c,n,k in j['smalls']:
        s=SM[c]
        w,cal=(s['w'],s['cal']) if 'w' in s else (j['w41'],j['cal'])
        base=sum(x*p(r,2026) for r,x in w.items());cap=sum(x*R[r][2] for r,x in w.items())
        e=min(.99,cal*base);il=(sum(IL[x]*v for x,v in IW[c].items() if x in IL)/sum(v for x,v in IW[c].items() if x in IL)) if 'IW' in globals() and c in IW and any(x in IL for x in IW[c]) else float(np.mean([IL[x] for x in I0[c] if x in IL]));t=(e+il)/2
        cal2=min(t/base,.97/cap)
        ob=U['oS'].get(c,U['oM'].get(j['code']));ms=U['mS'].get(c,U['mM'].get(j['code']))
        out[c]={'w':w,'cal':round(cal2,4),'n':s.get('n',0),'own':'w' in s,'e':round(e,4),'il':round(il,4),'ob':None if ob is None else round(ob,4),'ms':None if ms is None else round(ms,4),'isco':I[c]}
json.dump(out,open('real_small2.json','w'),ensure_ascii=False)
print(len(out))
