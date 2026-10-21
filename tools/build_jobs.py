"""직업 페이지(j/)를 만든다: 중분류 56개(j/11 …)와 소분류 163개(j/111 …).
검색에 잡히는 실제 페이지다. 표준 라이브러리만 쓴다.
사용: python3 tools/build_jobs.py   (저장소 루트에서. build_pages.py가 끝에서 자동으로 부른다)"""
import json,math,os,html as H
from urllib.parse import quote
BASE='https://aijido.org'
m=json.load(open('city_meta.json'));idx=json.load(open('index.json'))
R=m['R'];RN=m['RN'];J=m['jobs'];SM=m.get('sm',{})
W=idx['weeks'][-1];ADJ=W.get('adj',{});ASOF=W.get('date','')
SUB={'A5','B2','B9','C1','C2','C3','C4','C5','C9','D15','D3'}
CAT={'A':'정보 받아들이기','B':'생각하고 판단하기','C':'작업 수행하기','D':'사람과 상호작용하기'}
GN={'g1':'관리자','g2':'전문가','g3':'사무','g4':'서비스','g5':'판매','g6':'농림어업','g7':'기능','g8':'기계 조작·조립','g9':'단순노무'}
def p(r,y,s=0):mm,k,K=R[r];return K/(1+math.exp(-k*(y-mm+ADJ.get(r,0)+s*1.5)))
def occw(w,cal,y,s=0):return min(.99,cal*sum(x*p(r,y,s) for r,x in w.items()))
def ptask(cal,r,y):return min(R[r][2],cal*p(r,y))
def reach(f,thr=.4):
    y=2020.0
    while y<=2045:
        if f(y)>=thr:return int(y)
        y+=.25
    return None
pc=lambda v:round(v*100)
fw=lambda w:f"{round(w):,}" if w>=10 else f"{w:.1f}"
short=lambda n:n.replace('‧','·')
def sim(a,b):
    ks=set(a)|set(b);d=sum(a.get(k,0)*b.get(k,0) for k in ks)
    na=math.sqrt(sum(v*v for v in a.values()));nb=math.sqrt(sum(v*v for v in b.values()))
    return d/(na*nb) if na and nb else 0
CSS='''*{box-sizing:border-box}:root{--bg:#f3f3f6;--ink:#1c1c1e;--ink2:rgba(60,60,67,.68);--hair:rgba(28,28,30,.16);--hot:#a3206f;--use:#1f6fd1;color-scheme:light}
@media (prefers-color-scheme:dark){:root{--bg:#0b0c10;--ink:#f5f5f7;--ink2:rgba(235,235,245,.62);--hair:rgba(245,245,247,.18);--hot:#ff8ccd;--use:#5aa2ff;color-scheme:dark}}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Pretendard Variable",Pretendard,Inter,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;font-size:14px;line-height:1.6;word-break:keep-all;letter-spacing:-.005em}
main{max-width:720px;margin:0 auto;padding:28px 20px 72px}a{color:inherit}
.top{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--ink);padding-bottom:10px;font-size:12px}
.brand{font-weight:700;text-decoration:none}.brand b{color:var(--hot)}
.crumb{font-size:12px;color:var(--ink2);margin:24px 0 6px}.crumb a{text-decoration:none}
h1{font-size:30px;line-height:1.2;letter-spacing:-.035em;margin:0 0 6px}.sub{color:var(--ink2);font-size:12px}
.lede{font-size:18px;font-weight:700;letter-spacing:-.025em;margin:28px 0 0}
.big{font-size:104px;font-weight:600;letter-spacing:-.065em;line-height:.85;margin:14px 0 6px}.big small{font-size:32px;font-weight:500;letter-spacing:0;vertical-align:top}
.grid{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--ink);border-bottom:1px solid var(--hair);margin-top:24px}
.grid div{padding:8px 10px 10px;border-left:1px solid var(--hair)}.grid div:nth-child(3n+1){border-left:0;padding-left:0}.grid div:nth-child(n+4){border-top:1px solid var(--hair)}
.grid small{display:block;font-size:11px;color:var(--ink2)}.grid b{font-size:22px;font-weight:600;letter-spacing:-.04em}.grid .u b{color:var(--use)}
h2{font-size:12px;font-weight:600;border-top:1px solid var(--ink);padding-top:8px;margin:48px 0 8px;display:grid;grid-template-columns:32px 1fr}
h2::before{content:counter(s,decimal-leading-zero);counter-increment:s;font-weight:500}body{counter-reset:s}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:8px 0;border-bottom:1px solid var(--hair);text-align:left;vertical-align:top}th{font-weight:500;font-size:11px;color:var(--ink2)}
td.n,th.n{text-align:right;font-feature-settings:"tnum";white-space:nowrap;padding-left:12px}
.bar{display:block;height:3px;background:var(--hair);margin-top:5px}.bar i{display:block;height:3px;background:var(--hot)}
.tag{font-size:10px;border:1px solid currentColor;padding:0 4px;margin-left:6px;color:var(--ink2)}
p{margin:8px 0}.note{font-size:12px;color:var(--ink2)}
.cta{display:flex;gap:8px;flex-wrap:wrap;margin-top:28px}.cta a{border:1px solid var(--ink);padding:8px 12px;font-size:13px;font-weight:600;text-decoration:none}.cta a.p{background:var(--ink);color:var(--bg)}
.cite{border:1px solid var(--hair);padding:10px 12px;font-size:12px;margin-top:8px}
dl{margin:0}dt{font-weight:600;margin-top:14px}dd{margin:2px 0 0;color:var(--ink2)}
.foot{margin-top:56px;border-top:1px solid var(--ink);padding-top:8px;font-size:11px;color:var(--ink2)}'''
def page(path,title,desc,img,body,ld):
    open(path,'w').write(f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{H.escape(title)} · AI 점령 지도</title><meta name="description" content="{H.escape(desc)}">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<meta property="og:type" content="article"><meta property="og:site_name" content="AI 점령 지도"><meta property="og:title" content="{H.escape(title)}"><meta property="og:description" content="{H.escape(desc)}">
<meta property="og:image" content="{BASE}/{img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:url" content="{BASE}/{path[:-5]}">
<meta name="twitter:card" content="summary_large_image"><link rel="canonical" href="{BASE}/{path[:-5]}">
<script type="application/ld+json">{json.dumps(ld,ensure_ascii=False)}</script>
<script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "8eb4d903bad84bb89dd088032173bafb"}}'></script>
<style>{CSS}</style></head><body><main>
<div class="top"><a class="brand" href="/"><b>AI</b> 점령 지도 — Occupied Map</a><a href="/w/">주간 지수 →</a></div>
{body}
<p class="foot">노출도: Eloundou 외(2024, Science, MIT)와 ILO Gmyrek 외(2025, CC BY 4.0)의 평균 · 실제 사용: Anthropic 경제지수(2026, CC BY) · 업무 구성: O*NET 30.0(미국 노동부, CC BY 4.0) · 취업자: 국가데이터처 지역별고용조사 2025년 하반기 · 연도별 경로는 AI 점령 지도의 추정 · 기준 {ASOF} · 직업 단위의 경향이며 개인 평가나 인원 감축의 근거로 쓸 수 없어요.</p>
</main></body></html>''')
def faq(name,v,u):
    qa=[(f'AI가 {name}을(를) 대체하나요?',f'이 지도의 숫자는 일자리가 사라지는 비율이 아니라, {name}이(가) 하는 일 가운데 생성형 AI가 사람 수준으로 해내거나 시간을 절반 넘게 줄일 수 있는 몫(노출도)이에요. 2026년 기준 {pc(v)}%예요. 도입 비용·규제·실제 도입 속도는 반영하지 않았어요.'),
        (f'{name} 일에 AI가 실제로 쓰이고 있나요?',f'AI 사용 기록(Anthropic 경제지수)에서 이미 쓰이는 게 확인된 몫은 {"자료가 없어요" if u is None else str(pc(u))+"%예요"}. 한 회사 이용자 기준이라 실제보다 낮게 잡혀요.' )]
    return qa
def faqhtml(qa):return '<dl>'+''.join(f'<dt>{H.escape(q)}</dt><dd>{H.escape(a)}</dd>' for q,a in qa)+'</dl>'
def ldof(title,desc,url,qa):
    return {"@context":"https://schema.org","@graph":[{"@type":"Article","headline":title,"description":desc,"dateModified":ASOF,"inLanguage":"ko","url":url,"publisher":{"@type":"Organization","name":"포스트오피스 · AI 점령 지도"},"isBasedOn":["https://doi.org/10.1126/science.adj0998","https://www.ilo.org/publications/generative-ai-and-jobs-refined-global-index-occupational-exposure","https://www.onetcenter.org/database.html"]},
        {"@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in qa]}]}
def tasksrows(w,cal):
    top=sorted(w.items(),key=lambda kv:-kv[1])[:8];z=sum(w.values()) or 1
    out=''
    for r,x in top:
        a=ptask(cal,r,2026);f=ptask(cal,r,2030)
        out+=f'<tr><td>{H.escape(RN[r][0])}<span class="tag">{"대신하는 쪽" if r in SUB else "돕는 쪽"}</span><div class="note">{CAT[r[0]]} · 일의 {pc(x/z)}%</div><span class="bar"><i style="width:{a*100:.0f}%"></i></span></td><td class="n">{pc(a)}% → {pc(f)}%</td></tr>'
    return '<table><tr><th>업무</th><th class="n">2026 → 2030</th></tr>'+out+'</table>'
def subaug(w,cal,y=2026):
    s=a=0
    for r,x in w.items():
        v=x*ptask(cal,r,y)
        if r in SUB:s+=v
        else:a+=v
    k=occw(w,cal,y)/max(s+a,1e-9);return s*k,a*k
def stats(w,cal,e,il,ob):
    v=occw(w,cal,2026);r40=reach(lambda y:occw(w,cal,y));sa,au=subaug(w,cal)
    u=None if ob is None else min(ob,v)
    cells=[('2030 예측',f'{pc(occw(w,cal,2030))}%'),('40% 도달','이미 도달' if v>=.4 else ('2045 이후' if r40 is None else ('올해 안' if r40<=2026 else f'{r40}년'))),('실제 사용 확인','자료 없음' if u is None else f'{pc(u)}%'),
           ('미국 연구',f'{pc(e)}%' if e is not None else '—'),('국제노동기구',f'{pc(il)}%' if il is not None else '—'),('대신 · 돕는 쪽',f'{pc(sa)} · {pc(au)}')]
    return v,u,'<div class="grid">'+''.join(f'<div{" class=u" if k=="실제 사용 확인" else ""}><small>{k}</small><b>{val}</b></div>' for k,val in cells)+'</div>'
def lede(v):
    return '이 일의 절반 이상을 AI가 해낼 수 있어요.' if v>=.5 else '이 일의 40% 이상을 AI가 해낼 수 있어요.' if v>=.4 else '아직 대부분 사람의 몫이에요.' if v<.2 else '이 일의 일부를 AI가 해낼 수 있어요.'
os.makedirs('j',exist_ok=True)
JV={j['code']:occw(j['w41'],j['cal'],2026) for j in J}
urls=[]
for j in J:
    c=j['code'];v,u,st=stats(j['w41'],j['cal'],j.get('e'),j.get('il'),j.get('ob'))
    name=j['name'];title=f"{name}, AI가 이미 {pc(v)}%를 해낼 수 있어요"
    desc=f"표준직업분류 {c} {short(j['full'])} · 취업자 {fw(j['ws'])}만 명 · 2030년 예측 {pc(occw(j['w41'],j['cal'],2030))}% · 실제 사용 확인 {'—' if u is None else str(pc(u))+'%'} · 세부 직업별 노출도와 주요 업무"
    smr=''
    if len(j['smalls'])>1:
        for sc,sn,k in j['smalls']:
            d=SM.get(sc);sv=occw(d['w'],d['cal'],2026) if d else v
            smr+=f'<tr><td><a href="/j/{sc}">{H.escape(short(sn))}</a><span class="bar"><i style="width:{sv*100:.0f}%"></i></span></td><td class="n">{pc(sv)}%</td><td class="n">{fw(k/10)}만</td></tr>'
        smr='<h2>이 지역의 세부 직업</h2><table><tr><th>소분류</th><th class="n">2026 노출도</th><th class="n">취업자</th></tr>'+smr+'</table>'
    near=sorted([o for o in J if o['code']!=c and JV[o['code']]<v-.03],key=lambda o:-sim(j['w41'],o['w41']))[:3]
    nr=''.join(f'<tr><td><a href="/j/{o["code"]}">{H.escape(o["name"])}</a><div class="note">업무 겹침 {pc(sim(j["w41"],o["w41"]))}%</div></td><td class="n">{pc(JV[o["code"]])}%</td></tr>' for o in near)
    qa=faq(name,v,u)
    body=f'''<div class="crumb"><a href="/">지도</a> › {GN[j["group"]]} 구역</div><h1>{H.escape(name)}</h1><div class="sub">표준직업분류 {c} {H.escape(short(j["full"]))} · 취업자 {fw(j["ws"])}만 명</div>
<p class="lede">{lede(v)}</p><div class="big">{pc(v)}<small>%</small></div><div class="sub">2026 현재 노출도 · 두 연구의 평균</div>{st}
<div class="cta"><a class="p" href="/#j={c}">지도에서 보기 →</a><a href="/">다른 직업 찾기</a></div>
{smr}<h2>주요 업무 8개</h2>{tasksrows(j["w41"],j["cal"])}<p class="note">대신하는 쪽: AI가 그 일을 대신하는 업무. 돕는 쪽: 사람이 AI와 함께 더 하게 되는 업무.</p>
{'<h2>업무가 비슷하고 노출도가 낮은 직업</h2><table><tr><th>직업</th><th class="n">2026 노출도</th></tr>'+nr+'</table><p class="note">옮겨갈 길을 찾는 출발점이에요. 교육 기간·비용과 실제 이직 사례는 반영하지 않았어요.</p>' if nr else ''}
<h2>자주 묻는 질문</h2>{faqhtml(qa)}
<h2>인용하기</h2><div class="cite">출처: AI 점령 지도(포스트오피스), {ASOF} 기준, {H.escape(name)} 노출도 {pc(v)}%. {BASE}/j/{c}</div>'''
    page(f'j/{c}.html',title,desc,f'og/{c}.png',body,ldof(title,desc,f'{BASE}/j/{c}',qa));urls.append(f'{BASE}/j/{c}')
    for sc,sn,k in j['smalls']:
        if len(j['smalls'])<2:continue
        d=SM.get(sc)
        w,cal=(d['w'],d['cal']) if d else (j['w41'],j['cal'])
        v,u,st=stats(w,cal,d.get('e') if d else j.get('e'),d.get('il') if d else j.get('il'),d.get('ob') if d else j.get('ob'))
        nm=short(sn);title=f"{nm}, AI가 이미 {pc(v)}%를 해낼 수 있어요"
        desc=f"표준직업분류 소분류 {sc} {nm} · {name} · 취업자 {fw(k/10)}만 명 · 2030년 예측 {pc(occw(w,cal,2030))}% · 주요 업무별 노출도"
        sib=''.join(f'<tr><td><a href="/j/{x}">{H.escape(short(y))}</a></td><td class="n">{pc(occw(SM[x]["w"],SM[x]["cal"],2026)) if x in SM else pc(JV[c])}%</td></tr>' for x,y,_ in j['smalls'] if x!=sc)
        thin=d and d.get('n',9)<=2
        qa=faq(nm,v,u)
        body=f'''<div class="crumb"><a href="/">지도</a> › {GN[j["group"]]} 구역 › <a href="/j/{c}">{H.escape(name)}</a></div><h1>{H.escape(nm)}</h1><div class="sub">표준직업분류 소분류 {sc} · 취업자 {fw(k/10)}만 명</div>
<p class="lede">{lede(v)}</p><div class="big">{pc(v)}<small>%</small></div><div class="sub">2026 현재 노출도 · 두 연구의 평균 · {H.escape(name)} 전체는 {pc(JV[c])}%</div>{st}
{'<p class="note">연결된 미국 직업이 1~2개라 오차가 클 수 있어요.</p>' if thin else ''}{'' if d and d.get('own') else '<p class="note">이 소분류에 딱 맞는 미국 직업이 없어 업무 구성은 '+H.escape(name)+' 전체 값을 썼어요.</p>'}
<div class="cta"><a class="p" href="/#j={c}&q={quote(nm)}">지도에서 보기 →</a><a href="/j/{c}">{H.escape(name)} 전체 →</a></div>
<h2>주요 업무 8개</h2>{tasksrows(w,cal)}
<h2>같은 지역의 다른 세부 직업</h2><table><tr><th>소분류</th><th class="n">2026 노출도</th></tr>{sib}</table>
<h2>자주 묻는 질문</h2>{faqhtml(qa)}
<h2>인용하기</h2><div class="cite">출처: AI 점령 지도(포스트오피스), {ASOF} 기준, {H.escape(nm)} 노출도 {pc(v)}%. {BASE}/j/{sc}</div>'''
        page(f'j/{sc}.html',title,desc,f'og/{c}.png',body,ldof(title,desc,f'{BASE}/j/{sc}',qa));urls.append(f'{BASE}/j/{sc}')
json.dump(urls,open('j/_urls.json','w'))
print('job pages',len(urls))
