# [복원] 2026-10-18 22:36경 대화 중 인라인으로 실행된 단계를 다시 쓴 것. 결과가 원본(bak21/jobs_v3.json, 저장소 첫 ksco_soc_map.json)과 바이트 단위로 같음을 확인함.
# 입력: samples/jobs_v3_synth.json(build_v3.py 결과), real_profiles2.json, real_R.json, soc_map.py
# 출력: bak21/jobs_v3.json(중분류별 41개 업무 구성 w41·보정값 cal·논문 노출도 paper 추가), ksco_soc_map.json(중분류 연결표 기본판)
import json,math,os
exec(open('soc_map.py').read())
R=json.load(open('real_R.json'));p=lambda r,y:R[r][2]/(1+math.exp(-R[r][1]*(y-R[r][0])))
v3=json.load(open('samples/jobs_v3_synth.json'));P=json.load(open('real_profiles2.json'))
for j in v3['jobs']:
    o=P[j['code']];w=o['w41']
    base=sum(x*p(r,2026) for r,x in w.items());cap=sum(x*R[r][2] for r,x in w.items())
    beta=o['paper']['beta'] if o['paper'] else None
    top=sorted(w.items(),key=lambda kv:-kv[1])[:8];z=sum(x for _,x in top)
    j['tasks']={r:round(x/z,4) for r,x in top}
    j['basis']=o['occ'][:3]
    j['w41']=w;j['cal']=round(min((beta or base)/base,.97/cap),4);j['paper']=o['paper'];j['nocc']=o['n']
os.makedirs('bak21',exist_ok=True)
json.dump(v3,open('bak21/jobs_v3.json','w'),ensure_ascii=False)
d={'note':'한국표준직업분류 8차 중분류 → 미국 SOC 2018 코드 접두어(가장 긴 접두어 우선). 대분류 기본값은 fallback. AI 점령지도 작성.',
   'map':{j['code']:{'name':j['full'],'soc_prefix':M[j['code']],'us_examples':P[j['code']]['occ'],'onet_occupations':P[j['code']]['n'],'paper_exposure':P[j['code']]['paper'],'calibration':j['cal']} for j in v3['jobs']},
   'fallback':FALLBACK}
json.dump(d,open('ksco_soc_map.json','w'),ensure_ascii=False,indent=1)
print('jobs',len(v3['jobs']))
