# 예비 경로: 국가데이터처 연계표 없이 ILO 점수를 한국 소분류에 붙인다
# 국가데이터처 연계표(공공누리 제3유형) 이용 범위 확인이 안 될 때 쓸 예비 경로. 사용: python3 tools/alt_ilo_route.py (2026-11-03 비교: 사이트 값 순위상관 0.984, 차이 중앙값 1.5%p, 10%p 넘는 직업 없음)
# 한국 소분류 → (우리 연결표) 미국 SOC → O*NET → (O*NET 센터 ESCO 대응표, CC BY) ISCO-08 → ILO 점수
import csv, json, math, collections, statistics as st, openpyxl, os
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'; P=R+'pipeline/inputs/'; SC=R+'pipeline/scripts/'
ns={}; exec(open(SC+'soc_map_small.py').read(),ns); small_of=ns['small_of']
nm={}; exec(open(SC+'soc_map.py').read(),nm); ksco_of=nm['ksco_of']
M=json.load(open(R+'city_meta.json')); SM=M['sm']
IL={r['ISCO_08']:float(r['m']) for r in csv.DictReader(open(R+'pipeline/out/intermediate/isco_occ.csv'))}
EMP={}
for r in csv.DictReader(open(P+'gpts/national_May2021_dl.csv',encoding='utf-8-sig')):
    if r['O_GROUP']=='detailed':
        try: EMP[r['OCC_CODE']]=float(r['TOT_EMP'].replace(',',''))
        except: pass
emp=lambda s: EMP.get(s) or next((v for k,v in EMP.items() if k[:6]==s[:6]),1000.0)
xw=openpyxl.load_workbook(P+'onet_xw/ESCO_to_ONET-SOC.xlsx',read_only=True)
ON2IS=collections.defaultdict(set)
for r in xw[xw.sheetnames[0]].iter_rows(values_only=True):
    if r[0] and r[2] and str(r[0])[:4].isdigit(): ON2IS[str(r[2])].add(str(r[0])[:4])
def ilo_of_onet(o):
    v=[IL[x] for x in ON2IS.get(o,()) if x in IL]; return st.mean(v) if v else None
# O*NET 전체 목록(점수 붙는 것만)
ONETS=[o for o in ON2IS if ilo_of_onet(o) is not None]
def alt(code, small=True):
    acc=[0,0]; n=0
    for o in ONETS:
        soc=o[:7]; k=small_of(soc) if small else ksco_of(soc)
        if k!=code: continue
        w=emp(soc); acc[0]+=w*ilo_of_onet(o); acc[1]+=w; n+=1
    return (acc[0]/acc[1], n) if acc[1] else (None,0)
MID={c:j for j in M['jobs'] for c,_,_ in j['smalls']}
p=lambda r,y: M['R'][r][2]/(1+math.exp(-M['R'][r][1]*(y-M['R'][r][0])))
out={}
for c,s in SM.items():
    a,n=alt(c,True) if s.get('own') else (None,0)
    src='소분류'
    if a is None: a,n=alt(MID[c]['code'],False); src='중분류'
    if a is None: continue
    base=sum(x*p(r,2026) for r,x in s['w'].items()); cap=sum(x*M['R'][r][2] for r,x in s['w'].items())
    v0=min(.99,s['cal']*base)
    t_new=(s['e']+a)/2; t_old=(s['e']+s['il'])/2
    cal2=min(t_new/base,.97/cap); v1=min(.99,cal2*base)
    out[c]=dict(il0=s['il'],il1=a,n=n,src=src,v0=v0,v1=v1)
def rank(d): s=sorted(d,key=lambda k:-d[k]); return {k:i for i,k in enumerate(s)}
def rho(a,b):
    ks=[k for k in a if k in b]; ra,rb=rank({k:a[k] for k in ks}),rank({k:b[k] for k in ks}); m=(len(ks)-1)/2
    return sum((ra[k]-m)*(rb[k]-m) for k in ks)/math.sqrt(sum((ra[k]-m)**2 for k in ks)*sum((rb[k]-m)**2 for k in ks))
E={c:e for j in M['jobs'] for c,_,e in j['smalls']}; tot=sum(E[c] for c in out)
d=[(out[c]['v1']-out[c]['v0'])*100 for c in out]
print('소분류',len(out),'/',len(SM),' 중분류값으로 대신',sum(1 for x in out.values() if x['src']=='중분류'))
print('ILO 값 순위상관',round(rho({c:x['il0'] for c,x in out.items()},{c:x['il1'] for c,x in out.items()}),3))
print('사이트 2026값 순위상관',round(rho({c:x['v0'] for c,x in out.items()},{c:x['v1'] for c,x in out.items()}),3))
print('값 차이 중앙값 %p',round(st.median(abs(x) for x in d),1),' 5%p 넘는 직업',sum(1 for x in d if abs(x)>5),' 10%p 넘는',sum(1 for x in d if abs(x)>10))
print('전체(취업자 가중) 2026:',round(sum(out[c]['v0']*E[c] for c in out)/tot*100,2),'→',round(sum(out[c]['v1']*E[c] for c in out)/tot*100,2))
N={c:n for j in M['jobs'] for c,n,_ in j['smalls']}
for c in sorted(out,key=lambda c:-abs(out[c]['v1']-out[c]['v0']))[:12]:
    x=out[c]; print(f" {c} {N[c]}: {x['v0']*100:.0f}% → {x['v1']*100:.0f}%  (ILO {x['il0']:.2f}→{x['il1']:.2f}, {x['src']} {x['n']}개)")
json.dump(out,open(R+'reports/alt_ilo_route.json','w'))
