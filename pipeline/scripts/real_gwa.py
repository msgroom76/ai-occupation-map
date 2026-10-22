import csv,json,collections
D='dl_onet/db_text/';G='gpts/'  # 원래 /home/claude/openai/gpts-are-gpts/data/ (파이프라인: inputs/gpts)
RN=json.load(open('bak18/city_meta.json'))['RN']
E2R={}
for r in csv.DictReader(open(D+'Work Activities.txt'),delimiter='\t'):
    E2R[r['Element ID']]=[k for k,v in RN.items() if v[1].lower()==r['Element Name'].lower()][0]
dwa2g={r['DWA ID']:E2R[r['Element ID']] for r in csv.DictReader(open(D+'DWA Reference.txt'),delimiter='\t')}
t2g=collections.defaultdict(set)
for r in csv.DictReader(open(D+'Tasks to DWAs.txt'),delimiter='\t'):
    t2g[r['Task ID']].add(dwa2g[r['DWA ID']])
lab={}
for r in csv.DictReader(open(G+'full_labelset.tsv'),delimiter='\t'):
    try: tid=str(int(float(r['Task ID'])))
    except: continue
    lab[tid]={'beta':float(r['beta']),'alpha':float(r['alpha']),'gamma':float(r['gamma']),'h':r['human_exposure_agg'],'g4':r['gpt4_exposure']}
print('labeled tasks',len(lab),'tasks with dwa',len(t2g),'overlap',len(set(lab)&set(t2g)))
acc=collections.defaultdict(list)
for tid,gs in t2g.items():
    if tid in lab:
        for g in gs: acc[g].append(lab[tid])
# human beta: E0=0,E1=1,E2=.5
hb={'E0':0,'E1':1,'E2':.5}
out={}
for r in sorted(RN,key=lambda x:(x[0],int(x[1:]))):
    L=acc.get(r,[])
    if not L: print(r,'no data');continue
    b=sum(x['beta'] for x in L)/len(L); h=sum(hb.get(x['h'],0) for x in L if x['h'] in hb)/max(1,sum(1 for x in L if x['h'] in hb))
    a=sum(x['alpha'] for x in L)/len(L); g=sum(x['gamma'] for x in L)/len(L)
    out[r]={'n':len(L),'alpha':round(a,3),'beta':round(b,3),'gamma':round(g,3),'human_beta':round(h,3)}
    print(r,RN[r][0],len(L),'α',round(a,2),'β',round(b,2),'γ',round(g,2),'human β',round(h,2))
json.dump(out,open('dl_gpts_gwa.json','w'),ensure_ascii=False,indent=1)
