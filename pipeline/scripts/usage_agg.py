# [복원] 미국 SOC 직업별 '실제 사용'(Anthropic 경제지수 observed_exposure)과 'AI 적용 가능성'(ai_applicability_score)을
# 한국 소분류(oS, mS)·중분류(oM, mM)로 미국 고용(OEWS 2021.5) 가중 평균. 원본 usage_agg.json과 같음을 확인함.
import csv,json,collections
exec(open('soc_map_small.py').read()); exec(open('soc_map.py').read())
G='gpts/'
EMP={}
for r in csv.DictReader(open(G+'national_May2021_dl.csv',encoding='utf-8-sig')):
    if r['O_GROUP']=='detailed':
        try: EMP[r['OCC_CODE']]=float(r['TOT_EMP'].replace(',',''))
        except: pass
def agg(fn,col,codecol):
    S_=collections.defaultdict(lambda:[0,0]);M_=collections.defaultdict(lambda:[0,0])
    for r in csv.DictReader(open(fn)):
        soc=r[codecol][:7]; v=float(r[col])
        e=EMP.get(soc) or next((x for k,x in EMP.items() if k[:6]==soc[:6]),1000.0)
        s=small_of(soc); m=ksco_of(soc)
        if s: S_[s][0]+=e*v;S_[s][1]+=e
        if m: M_[m][0]+=e*v;M_[m][1]+=e
    return {k:a/b for k,(a,b) in S_.items() if b},{k:a/b for k,(a,b) in M_.items() if b}
oS,oM=agg('dl2/job_exposure.csv','observed_exposure','occ_code')
import os
if os.path.exists('dl2/ai_applicability_scores.csv'):
    mS,mM=agg('dl2/ai_applicability_scores.csv','ai_applicability_score','SOC Code')
else:  # Microsoft 원자료는 재배포 조건이 확인되지 않아 저장소에 넣지 않았다. 집계 결과(사이트에 공개된 값과 같은 수준)만 고정본으로 쓴다.
    _f=json.load(open('frozen/usage_ms.json'));mS,mM=_f['mS'],_f['mM']
json.dump({'oS':oS,'oM':oM,'mS':mS,'mM':mM},open('usage_agg.json','w'));print('usage',len(oS),len(mS))
