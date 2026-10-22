import csv,json,collections,math
D='dl_onet/db_text/';G='gpts/'  # 원래 /home/claude/openai/gpts-are-gpts/data/ (파이프라인: inputs/gpts)
gwa=json.load(open('dl_gpts_gwa.json'))
lab={}
for r in csv.DictReader(open(G+'full_labelset.tsv'),delimiter='\t'):
    try: lab[str(int(float(r['Task ID'])))]=(r['O*NET-SOC Code'],float(r['alpha']),float(r['beta']),float(r['gamma']))
    except: pass
TITLE={r['O*NET-SOC Code']:r['Title'] for r in csv.DictReader(open(D+'Occupation Data.txt'),delimiter='\t')}
def occmean(pred):
    L=[v for v in lab.values() if pred(v[0])]
    return {'n':len(L),'alpha':round(sum(x[1] for x in L)/len(L),3),'beta':round(sum(x[2] for x in L)/len(L),3),'gamma':round(sum(x[3] for x in L)/len(L),3)}
gwa['C6']=occmean(lambda c:c.startswith('17-301'))|{'proxy':'제도사(SOC 17-301x) 업무 평균'}
gwa['C8']=occmean(lambda c:c.startswith('49-2'))|{'proxy':'전자장비 수리원(SOC 49-2xxx) 업무 평균'}
gwa['D9']=occmean(lambda c:TITLE.get(c,'').startswith('First-Line Supervisors'))|{'proxy':'현장 감독자(First-Line Supervisors) 업무 평균'}
d10={k:round((gwa['D12'][k]+gwa['D13'][k]+gwa['D16'][k])/3,3) for k in ['alpha','beta','gamma']}
gwa['D10']=d10|{'n':0,'proxy':'지휘하기·코칭·채용 평균'}
for k in ['C6','C8','D9','D10']: print(k,gwa[k])
# 곡선: 상한 K=γ, 2023년=α(언어모델 단독), 2026년=β(언어모델+도구)
R={}
for r,v in gwa.items():
    a,b,g=v['alpha'],v['beta'],v['gamma']
    K=max(g,b+.02,.03); a=min(max(a,.004),b*.8 if b>0.005 else .004); b=max(b,a*1.25,.006)
    x1=math.log(a/(K-a)); x2=math.log(b/(K-b)); k=(x2-x1)/3; m=2023-x1/k
    R[r]=[round(m,3),round(k,4),round(K,3)]
    v['curve']=R[r]
json.dump(gwa,open('real_gwa_final.json','w'),ensure_ascii=False,indent=1)
json.dump(R,open('real_R.json','w'))
p=lambda r,y:R[r][2]/(1+math.exp(-R[r][1]*(y-R[r][0])))
for r in sorted(R,key=lambda x:(x[0],int(x[1:]))): print(r,R[r],[round(p(r,y),2) for y in (2023,2026,2030)])
