import json
exec(open('soc_map_small.py').read())
m=json.load(open('web/city_meta.json'));SM=json.load(open('real_small2.json'));v3=json.load(open('samples/jobs_v3.json'))
V={j['code']:j for j in v3['jobs']}
for j in m['jobs']:
    for f in ('e','il','ob','ms'): j[f]=V[j['code']][f]
m['sm']={c:{'w':{r:round(x,3) for r,x in s['w'].items() if x>=.0005},'cal':s['cal'],'n':s['n'],'own':int(s['own']),'e':s['e'],'il':s['il'],'ob':s['ob']} for c,s in SM.items()}
json.dump(m,open('web/city_meta.json','w'),ensure_ascii=False,separators=(',',':'))
names={x[0]:x[1] for j in m['jobs'] for x in j['smalls']}
# 원래 K는 저장소 파일 경로였고 그 파일을 직접 고쳤다. 파이프라인은 apply_profiles.py가 만든 기본판을 고친다.
K='ksco_soc_map.json';d=json.load(open(K))
d['note']='한국표준직업분류 8차 → 미국 SOC 2018 / ISCO-08. map은 중분류, small은 소분류. 소분류 노출도(2026) = Eloundou 외(2024) 값과 ILO(Gmyrek 외 2025) 값의 평균. 중분류 값은 소분류 값을 한국 취업자 수(지역별고용조사 2025년 하반기)로 가중 평균. soc_prefix가 비어 있는 소분류는 미국 업무 구성에 중분류 것을 쓴다. ISCO 연결은 AI 점령지도 임시 작성(국가데이터처 공식 연계표로 교체 예정). AI 점령지도 작성.'
d['small']={c:{'name':names.get(c,''),'soc_prefix':S.get(c,[]),'isco08':SM[c]['isco'],'us_examples':json.load(open('real_small.json'))[c].get('basis',[]),'onet_occupations':SM[c]['n'],'exposure_2026':{'eloundou':SM[c]['e'],'ilo':SM[c]['il']},'observed_use_anthropic':SM[c]['ob'],'calibration':SM[c]['cal']} for c in sorted(SM)}
d.pop('small_inherit',None)
for j in m['jobs']:
    if j['code'] in d['map']: d['map'][j['code']]['calibration']=j['cal']
json.dump(d,open(K,'w'),ensure_ascii=False,indent=1)
import os;print(len(m['sm']),os.path.getsize('web/city_meta.json'))
