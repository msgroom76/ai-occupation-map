import json,collections
exec(open('samples/jobs_v2.py').read())
OLD={n:d for n,w,d in JOBS2}; OLDN=[n for n,_,_ in JOBS2]
occ=json.load(open('dl_lfs/occ_2025h2.json'))['rows']
K={r['code']:r for r in occ}
KS=json.load(open('web/ksco_titles.json'))
SHORT={'11':'고위 공무원·기업 임원','12':'경영지원·마케팅 관리자','13':'전문서비스 관리자','14':'건설·생산 관리자','15':'판매·서비스 관리자',
'21':'과학 연구직','22':'IT·정보통신 전문가','23':'공학 기술자','24':'의료·보건 전문가','25':'사회복지·상담·종교','26':'교육 전문가','27':'법률·행정 전문가','28':'경영·금융·마케팅 전문가','29':'문화·예술·디자인·언론',
'31':'기획·영업·인사 사무','32':'생산·물류 사무','33':'회계·경리 사무','34':'금융 사무','35':'공공행정 사무','36':'상담·안내 접수','37':'일반 사무 지원',
'41':'경찰·소방·보안','42':'돌봄·보건 서비스','43':'미용·생활 서비스','44':'운송·여가 서비스','45':'조리·음식 서비스',
'51':'영업직','52':'매장 판매','53':'통신·방문 판매',
'61':'농축산업','62':'임업','63':'어업',
'71':'식품 가공 기능','72':'의복·섬유 기능','73':'목재·가구·간판 기능','74':'금속 성형 기능','75':'자동차·기계 정비','76':'전기·전자 기능','77':'통신·방송장비 기능','78':'건설 기능','79':'기타 기능',
'81':'식품 기계 조작','82':'섬유 기계 조작','83':'화학 기계 조작','84':'금속 기계 조작','85':'기계 조립','86':'전기·전자 조립','87':'운전·운송','88':'상하수도·재활용','89':'목재·인쇄 기계 조작',
'91':'건설 단순노무','92':'운송·택배 단순노무','93':'제조 단순노무','94':'청소·경비','95':'가사·음식·판매 보조','99':'농림어업·기타 단순노무'}
GNAME={'1':'관리자','2':'전문가','3':'사무','4':'서비스','5':'판매','6':'농림어업','7':'기능','8':'기계 조작·조립','9':'단순노무'}
mids=[r for r in occ if r['lv']==2]
# 세분류 → 소분류 가중치
bysmall=collections.defaultdict(list)
for c,(n,j,e) in KS['codes'].items():
    if c[0].isdigit(): bysmall[c[:3]].append(j)
jobs=[];midOf={}
for r in mids:
    m=r['code']; prof=collections.Counter(); oldw=collections.Counter()
    smalls=[s for s in occ if s['lv']==3 and s['code'][:2]==m]
    for s in smalls:
        js=bysmall.get(s['code']) or [j for c,(n,j,e) in KS['codes'].items() if c[:2]==m]
        for j in js:
            w=(s['k'] or 0)/len(js); d=OLD[OLDN[j]]; t=sum(d.values())
            oldw[OLDN[j]]+=w
            for rid,v in d.items(): prof[rid]+=w*v/t
    top=dict(prof.most_common(6)); z=sum(top.values()); top={k:round(v/z,3) for k,v in top.items()}
    jobs.append({'code':m,'name':SHORT[m],'full':r['name'],'k':r['k'],'group':'g'+m[0],'tasks':top,
      'smalls':[[s['code'],s['name'],s['k']] for s in sorted(smalls,key=lambda s:-(s['k'] or 0))],'basis':[n for n,_ in oldw.most_common(3)]})
for i,j in enumerate(jobs): midOf[j['code']]=i
# 옛 직업 → 중분류 (정확 매핑 세분류 중 다수결)
o2m={}
for oi,on in enumerate(OLDN):
    c=collections.Counter(code[:2] for code,(n,j,e) in KS['codes'].items() if j==oi and e and code[0].isdigit()) or collections.Counter(code[:2] for code,(n,j,e) in KS['codes'].items() if j==oi and code[0].isdigit())
    o2m[on]=c.most_common(1)[0][0] if c else None
FIX={'경영·기획 관리자':'12','전기·전자 기술자':'23','경영관련 사무원':'31','인사·노무 사무원':'31','보육교사':'25','배달·택배원':'92','품질 검사원':'23','마케팅 전문가':'28','부동산 중개인':'28','비서':'37','고객센터 상담원':'36','보험·금융 상담원':'51','온라인 판매 운영자':'53','물류 창고 작업원':'92','청소원':'94','보안·경비원':'94','데이터 분석가':'22','작물재배 종사자':'61'}
o2m.update(FIX)
for k,v in o2m.items(): print(k,'→',v,SHORT.get(v))
json.dump({'jobs':jobs,'gname':GNAME,'o2m':o2m,'old':{n:d for n,d in OLD.items()},'titles':TITLES},open('samples/jobs_v3.json','w'),ensure_ascii=False)
for j in jobs: print(j['code'],j['name'],j['k'],j['tasks'],j['basis'])
