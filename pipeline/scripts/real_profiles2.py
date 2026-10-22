import csv,json,collections,math
exec(open('soc_map.py').read())
D='dl_onet/db_text/';G='gpts/'  # 원래 /home/claude/openai/gpts-are-gpts/data/ (파이프라인: inputs/gpts)
RN=json.load(open('bak18/city_meta.json'))['RN']
E2R={r['Element ID']:[k for k,v in RN.items() if v[1].lower()==r['Element Name'].lower()][0] for r in csv.DictReader(open(D+'Work Activities.txt'),delimiter='\t')}
dwa2g={r['DWA ID']:E2R[r['Element ID']] for r in csv.DictReader(open(D+'DWA Reference.txt'),delimiter='\t')}
t2g=collections.defaultdict(set)
for r in csv.DictReader(open(D+'Tasks to DWAs.txt'),delimiter='\t'): t2g[r['Task ID']].add(dwa2g[r['DWA ID']])
# 업무 중요도(IM)
tim={}
for r in csv.DictReader(open(D+'Task Ratings.txt'),delimiter='\t'):
    if r['Scale ID']=='IM': tim[r['Task ID']]=float(r['Data Value'])
tocc={}
for r in csv.DictReader(open(D+'Task Statements.txt'),delimiter='\t'): tocc[r['Task ID']]=r['O*NET-SOC Code']
# 직업별 업무 → 41개 활동 분포
occw=collections.defaultdict(collections.Counter)
for tid,c in tocc.items():
    gs=t2g.get(tid)
    if not gs: continue
    w=max(tim.get(tid,3.0)-1,0.2)/len(gs)
    for g in gs: occw[c][g]+=w
# 논문 직업 단위 노출도
OL={}
for r in csv.DictReader(open(G+'occ_level.csv')):
    OL[r['O*NET-SOC Code']]={k:float(r['dv_rating_'+k]) for k in ('alpha','beta','gamma')}
EMP={}
for r in csv.DictReader(open(G+'national_May2021_dl.csv',encoding='utf-8-sig')):
    if r['O_GROUP']=='detailed':
        try: EMP[r['OCC_CODE']]=float(r['TOT_EMP'].replace(',',''))
        except: pass
TITLE={r['O*NET-SOC Code']:r['Title'] for r in csv.DictReader(open(D+'Occupation Data.txt'),delimiter='\t')}
bysoc=collections.defaultdict(list)
for c in set(occw)|set(OL): bysoc[c[:7]].append(c)
reg=collections.defaultdict(collections.Counter);regw=collections.Counter();regE=collections.defaultdict(lambda:[0,0,0,0]);regocc=collections.defaultdict(list)
for soc,cs in bysoc.items():
    m=ksco_of(soc)
    if not m: continue
    e=EMP.get(soc) or next((v for k,v in EMP.items() if k[:6]==soc[:6]),1000.0)
    for c in cs:
        w=e/len(cs)
        if c in occw:
            z=sum(occw[c].values())
            for g,v in occw[c].items(): reg[m][g]+=w*v/z
            regw[m]+=w; regocc[m].append((w,TITLE.get(c,c)))
        if c in OL:
            for i,k in enumerate(('alpha','beta','gamma')): regE[m][i]+=w*OL[c][k]
            regE[m][3]+=w
out={}
for m in reg:
    z=sum(reg[m].values())
    E=regE[m];out[m]={'w41':{g:round(v/z,4) for g,v in reg[m].items()},'paper':{k:round(E[i]/E[3],3) for i,k in enumerate(('alpha','beta','gamma'))} if E[3] else None,'occ':[t for _,t in sorted(regocc[m],reverse=True)[:5]],'n':len(regocc[m])}
json.dump(out,open('real_profiles2.json','w'),ensure_ascii=False)
R=json.load(open('real_R.json'));p=lambda r,y:R[r][2]/(1+math.exp(-R[r][1]*(y-R[r][0])))
v3=json.load(open('samples/jobs_v3.json'));rows=[]
for j in v3['jobs']:
    o=out[j['code']];full=sum(x*p(r,2026) for r,x in o['w41'].items())
    top=sorted(o['w41'].items(),key=lambda kv:-kv[1])[:8];z=sum(x for _,x in top);t8=sum(x/z*p(r,2026) for r,x in top)
    rows.append((j['code'],j['name'],round(full*100),round(t8*100),round(o['paper']['beta']*100) if o['paper'] else None,round(sum(x for _,x in top)*100),[r for r,_ in top]))
for r in sorted(rows,key=lambda x:-x[2]):print(r)
# 일상 직업(57개) 업무 구성
exec(open('old2soc.py').read())
det={}
for on,socs in O2S.items():
    acc=collections.Counter();be=[];n=0
    for c in set(occw)|set(OL):
        if any(c.startswith(s) for s in socs):
            if c in occw:
                z=sum(occw[c].values())
                for g,v in occw[c].items(): acc[g]+=v/z
                n+=1
            if c in OL: be.append(OL[c]['beta'])
    if not n: print('NO SOC',on,socs);continue
    z=sum(acc.values());det[on]={'w41':{g:round(v/z,4) for g,v in acc.items()},'beta':round(sum(be)/len(be),3) if be else None}
json.dump(det,open('real_detail.json','w'),ensure_ascii=False)
print('detail',len(det))
