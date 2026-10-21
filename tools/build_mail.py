"""주간 메일(뉴스레터) 원고를 주마다 만들어 쌓아둔다. 표준 라이브러리만 쓴다.
사용: build_pages.py 끝에서 자동 실행. 단독 실행도 가능(저장소 루트에서 python3 tools/build_mail.py).

브리핑 원고: mail/brief/<주>.json 이 있으면 그 글로 '브리핑형' 메일을 만든다(주간 작업이 매주 씀).
  {"headline": 이번 주를 한 문장으로(제목에도 씀),
   "intro": 2~4문장 도입,
   "tldr": [30초 요약 3줄],
   "points": [{"tag": "숫자에 반영|한국 고용|다음 주 예고 …", "title": 소제목,
               "what": 무슨 일이 있었나, "why": 왜 중요한가, "who": 누구에게 어떤 영향인가,
               "jobs": [중분류 코드…], "sources": [{"name","url"}]}],   ← 3~4개
   "closing": 맺음 한두 문장}
  숫자(점령률·변화·직업별 노출도·다음 주 전망)는 여기서 계산해 넣는다. 원고에는 숫자를 지어 넣지 않는다.
  '다음 주 예고' 포인트에도 전망 숫자는 붙이지 않는다(대기 소식은 주간 반영 규칙 v2로 줄어들거나 빠질 수 있음).
원고가 없으면 소식 목록 위주의 기본형으로 만든다.

결과: mail/<주>.html(메일용 HTML, 인라인 스타일) · mail/<주>.txt(텍스트판) · mail/<주>.json(제목·미리보기 문구)
      mail/index.json(전체 목록). 발송은 아직 안 함. 발송 도구를 붙이면 {{unsubscribe_url}}만 바꿔 넣으면 된다."""
import json,math,os,html as H
from datetime import date,timedelta
BASE='https://aijido.org'
cm=json.load(open('city_meta.json'));idx=json.load(open('index.json'));feed=json.load(open('feed.json'))
R=cm['R'];J=cm['jobs'];WS=sum(j['ws'] for j in J);JC={j['code']:j for j in J}
def p(r,y,a):m,k,K=R[r];return K/(1+math.exp(-k*(y-m+a.get(r,0))))
def occ(j,a):return min(.99,j['cal']*sum(x*p(r,2026,a) for r,x in j['w41'].items()))
def tot(a):return sum(j['ws']*occ(j,a) for j in J)/WS
items={n['id']:n for n in feed['items']}
SHIFT={'1차 출처':.25,'신뢰 매체':1/12,'확인 필요':0}
os.makedirs('mail',exist_ok=True)
INK='#16161a';MUT='#6b6b76';LINE='#e6e6ea';PINK='#8a085a';SOFT='#fbf1f7';BG='#f6f6f8'
F="-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif"
e=H.escape
def a(u,t,c=PINK,w=400):return f'<a href="{e(u)}" style="color:{c};font-weight:{w};text-decoration:underline">{e(t)}</a>'
def row(inner,pad='0'):return f'<tr><td style="padding:{pad}">{inner}</td></tr>'
def para(t,c=INK,s=15,pad='4px 0'):return f'<tr><td style="padding:{pad};font:{s}px/1.7 {F};color:{c}">{t}</td></tr>'
def kicker(t):return f'<tr><td style="padding:36px 0 6px;font:700 12px/1.4 {F};letter-spacing:.08em;color:{PINK}">{t}</td></tr>'
def table(head,rows):
    th=''.join(f'<td style="padding:8px 0;border-bottom:1px solid {INK};font:600 12px {F};color:{MUT};text-align:{"right" if i else "left"}">{h}</td>' for i,h in enumerate(head))
    tr=''.join('<tr>'+''.join(f'<td style="padding:9px 0;border-bottom:1px solid {LINE};font:15px/1.4 {F};color:{INK};text-align:{"right" if i else "left"}">{c}</td>' for i,c in enumerate(r))+'</tr>' for r in rows)
    return f'<tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{th}</tr>{tr}</table></td></tr>'
def chips(codes,a_now,a_ref,label):
    out=[]
    for c in codes:
        j=JC.get(c)
        if not j:continue
        v=occ(j,a_now)*100;d=(occ(j,a_ref)-occ(j,a_now))*100 if label=='전망' else (occ(j,a_now)-occ(j,a_ref))*100
        dd=f' <span style="color:{PINK}">{"전망 " if label=="전망" else ""}{d:+.1f}%p</span>' if abs(d)>=0.05 else ''
        out.append(f'<a href="{BASE}/j/{c}" style="display:inline-block;margin:0 6px 6px 0;padding:5px 10px;border:1px solid {LINE};font:13px/1.3 {F};color:{INK};text-decoration:none">{e(j["name"])} <b>{v:.0f}%</b>{dd}</a>')
    return ''.join(out)
def labeled(lbl,txt):
    return f'<tr><td style="padding:6px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td valign="top" width="78" style="font:700 13px/1.7 {F};color:{MUT};white-space:nowrap">{lbl}</td><td valign="top" style="font:15px/1.7 {F};color:{INK}">{e(txt)}</td></tr></table></td></tr>'
weeks=[w for w in idx['weeks'] if w.get('total') is not None];lst=[]
for i,w in enumerate(weeks):
    prev=weeks[i-1] if i else None;wk=w['week'];num=int(wk.split('-W')[1]);last=(i==len(weeks)-1)
    if not last and os.path.exists(f'mail/{wk}.json'):  # 지난 호는 발행 당시 그대로 둔다
        lst.append(json.load(open(f'mail/{wk}.json')));continue
    A=w['adj'];P=prev['adj'] if prev else A
    t=tot(A);dt=(t-tot(P))*100 if prev else None
    mv=sorted((((occ(j,A)-occ(j,P))*100,j) for j in J),key=lambda x:x[0]) if prev else []
    mv=[x for x in reversed(mv) if x[0]>=0.005][:5]
    ap=[items[x] for x in w.get('applied',[]) if x in items]
    end=date.fromisoformat(w['date']);start=date.fromisoformat(prev['date']) if prev else end-timedelta(days=7)
    # 다음 주 전망 숫자는 내지 않는다(2026-10-21 검증: 반영 규칙상 대기 소식이 그대로 반영되지 않고, 예측처럼 읽혀 오해를 부름)
    NA=dict(A);pend=[];nt=None
    dtxt=('첫 주간 지수예요' if dt is None else f'지난주보다 {dt:+.2f}%p' if abs(dt)<0.1 else f'지난주보다 {dt:+.1f}%p')
    bp=f'mail/brief/{wk}.json';B=json.load(open(bp)) if os.path.exists(bp) else None
    url=f'{BASE}/w/{wk}'
    md=date.fromisoformat(w['date'])
    mast=(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
          f'<tr><td colspan="2" style="padding:0 0 10px;font:600 12px/1.4 {F};color:{INK}">AI 점령 지도 <span style="color:{MUT};font-weight:400">— 사람의 일, AI가 어디까지 장악했나?</span></td></tr>'
          f'<tr><td valign="bottom"><a href="{BASE}/" style="text-decoration:none"><img src="{BASE}/mail/img/logo.png" width="150" height="47" alt="AI 점령 지도 · AI Occupied Map" style="display:block;border:0;width:150px;height:auto;color:{PINK};font:700 20px {F}"></a></td>'
          f'<td valign="bottom" align="right" style="font:12px/1.5 {F};color:{MUT};white-space:nowrap"><b style="color:{INK};letter-spacing:.06em">WEEKLY BRIEFING</b><br>{wk[:4]} · {num}주차 · {md.month}월 {md.day}일</td></tr>'
          f'<tr><td colspan="2" style="padding:14px 0 0;border-bottom:2px solid {INK}"></td></tr></table>')
    rows=[row(mast,'0 0 24px')]
    if B:
        subject=f'[AI 점령 지도] {B["headline"]} · {num}주차 {t*100:.1f}%'
        pre=B['tldr'][0][:90] if B.get('tldr') else B['intro'][:90]
        rows.append(para(e(B['headline']),INK,26,'0 0 14px').replace('font:26px/1.7','font:800 26px/1.35'))
    else:
        subject=f'[AI 점령 지도] {num}주차 {t*100:.1f}% · {dtxt}'
        pre=(f'이번 주 숫자를 움직인 소식: {ap[0]["hd"]}' if ap else '이번 주에는 숫자를 움직인 확인된 소식이 없었어요.')[:90]
    # 숫자 상자
    nxt=f'<br><span style="font:13px/1.5 {F};color:{MUT}">대기 중인 소식 {len(pend)}건이 그대로 반영되면 다음 주 약 {nt*100:.1f}% ({(nt-t)*100:+.1f}%p)</span>' if nt is not None and abs(nt-t)>=0.0005 else ''
    rows.append(row(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{SOFT}"><tr><td style="padding:18px 20px"><div style="font:600 13px {F};color:{MUT}">이번 주 AI 점령률</div><div style="font:800 52px/1.1 {F};letter-spacing:-.03em;color:{PINK}">{t*100:.1f}%</div><div style="font:15px/1.6 {F};color:{INK}">{dtxt} · 한국 취업자 2,904만 명이 하는 일 가운데 AI가 이미 해낼 수 있는 몫{nxt}</div></td></tr></table>'))
    txt=[subject,'']
    if B:
        rows.append(para(e(B['intro']),INK,16,'20px 0 0'))
        if B.get('tldr'):
            rows.append(kicker('30초 요약'))
            li=''.join(f'<tr><td valign="top" width="22" style="font:700 15px/1.7 {F};color:{PINK}">{k+1}</td><td style="padding:0 0 6px;font:15px/1.7 {F};color:{INK}">{e(s)}</td></tr>' for k,s in enumerate(B['tldr']))
            rows.append(row(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid {INK};border-bottom:1px solid {INK}"><tr><td style="padding:12px 0 6px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{li}</table></td></tr></table>'))
        txt+=[B['headline'],'',f'이번 주 AI 점령률 {t*100:.1f}% ({dtxt})'+(f' · 다음 주 전망 약 {nt*100:.1f}%' if nxt else ''),'',B['intro'],'','■ 30초 요약']+[f'{k+1}. {s}' for k,s in enumerate(B.get('tldr',[]))]
        for k,pt in enumerate(B['points']):
            fut=pt.get('tag')=='다음 주 예고'
            rows.append(kicker(f'{k+1:02d} — {e(pt.get("tag",""))}'))
            rows.append(para(e(pt['title']),INK,19,'0 0 6px').replace('font:19px/1.7','font:700 19px/1.4'))
            for lbl,key in (('무슨 일','what'),('왜 중요','why'),('누구에게','who')):
                if pt.get(key):rows.append(labeled(lbl,pt[key]))
            if pt.get('jobs'):
                c=chips(pt['jobs'],A,NA if fut else P,'전망' if fut else '변화')
                if c:rows.append(row(c,'8px 0 0'))
            if pt.get('sources'):rows.append(para('출처 · '+' · '.join(a(s['url'],s['name'],MUT) for s in pt['sources']),MUT,12,'2px 0 0'))
            txt+=['',f'■ {k+1:02d} {pt.get("tag","")} — {pt["title"]}']+[f'{l}: {pt[key]}' for l,key in (('무슨 일','what'),('왜 중요','why'),('누구에게','who')) if pt.get(key)]
            if pt.get('jobs'):txt.append('관련 직업: '+', '.join(f'{JC[c]["name"]} {occ(JC[c],A)*100:.0f}%' for c in pt['jobs'] if c in JC))
            txt+=[f'출처: {s["name"]} {s["url"]}' for s in pt.get('sources',[])]
        k=len(B['points'])+1
    else:
        txt+=[f'이번 주 AI 점령률 {t*100:.1f}% ({dtxt})','','■ 이번 주 숫자를 움직인 소식']+([f'- {n["hd"]} ({n["src"]}) {n["url"]}' for n in ap] or ['- 없음'])
        rows.append(kicker('01 — 이번 주 숫자를 움직인 소식'))
        if ap:
            for n in ap:rows.append(para(f'{a(n["url"],n["hd"],INK)}<br><span style="color:{MUT};font-size:13px">{e(n["src"])} · {e(n["tier"])}</span>'))
        else:rows.append(para('숫자를 움직인 확인된 소식이 없었어요. 발표나 실제 도입이 확인된 소식만 반영해요.',MUT))
        k=2
    # 숫자로 보는 이번 주
    rows.append(kicker(f'{k:02d} — 숫자로 보는 이번 주'))
    if mv:
        rows.append(para('이번 주 가장 많이 오른 직업',MUT,13,'4px 0 0'))
        rows.append(table(['직업','노출도','변화'],[[a(f'{BASE}/j/{j["code"]}',j['name'],INK),f'{occ(j,A)*100:.0f}%',f'+{d:.2f}%p'] for d,j in mv]))
    top=sorted(J,key=lambda j:-occ(j,A))[:5]
    rows.append(para('지금 가장 많이 노출된 직업',MUT,13,'16px 0 0'))
    rows.append(table(['직업','노출도','취업자'],[[a(f'{BASE}/j/{j["code"]}',j['name'],INK),f'{occ(j,A)*100:.0f}%',f'{j["ws"]:.0f}만 명'] for j in top]))
    txt+=['','■ 숫자로 보는 이번 주']+[f'- 오름: {j["name"]} {occ(j,A)*100:.0f}% (+{d:.2f}%p)' for d,j in mv]+[f'- 노출 상위: {j["name"]} {occ(j,A)*100:.0f}% · {j["ws"]:.0f}만 명' for j in top]
    if B and B.get('closing'):
        rows.append(para(e(B['closing']),INK,16,'32px 0 0'));txt+=['',B['closing']]
    rows.append(row(f'<a href="{BASE}/" style="display:inline-block;background:{INK};color:#fff;font:700 15px {F};padding:13px 22px;text-decoration:none">내 직업 찾아보기 →</a>','24px 0 0'))
    rows.append(row('',f'40px 0 0;border-bottom:1px solid {INK}'))
    rows.append(para('읽는 법 · 노출도는 그 직업이 하는 일 가운데 AI가 해낼 수 있는 몫이에요. 일자리가 그만큼 사라진다는 뜻은 아니에요. 소식은 1차 출처의 발표·도입이면 도달 시점을 3개월, 신뢰 매체 보도면 1개월 앞당기고, 미국 발표는 절반만 반영해요.',MUT,12,'12px 0 0'))
    rows.append(para(f'노출도: Eloundou 외(2024, Science)·ILO Gmyrek 외(2025) 평균 · 업무: O*NET 30.0 · 취업자: 국가데이터처 지역별고용조사 2025년 하반기. 직업 단위의 경향이며 개인 평가나 인원 감축의 근거로 쓸 수 없어요.',MUT,12))
    rows.append(para(f'{a(url,"웹에서 보기",MUT)} · {a("{{unsubscribe_url}}","수신 거부",MUT)}<br>이 메일은 AI 점령 지도에서 주간 지수 받기를 신청한 분께 보내요.',MUT,12))
    txt+=['',f'내 직업 찾아보기: {BASE}/',f'웹에서 보기: {url}','','노출도는 AI가 해낼 수 있는 몫이며, 일자리가 그만큼 사라진다는 뜻은 아니에요. 직업 단위의 경향이며 개인 평가나 인원 감축의 근거로 쓸 수 없어요.','수신 거부: {{unsubscribe_url}}']
    html_=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta name="robots" content="noindex"><title>{e(subject)}</title></head>
<body style="margin:0;padding:0;background:{BG}"><div style="display:none;max-height:0;overflow:hidden;opacity:0">{e(pre)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG}"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fff;border-top:6px solid {PINK}"><tr><td style="padding:32px 28px 36px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{''.join(rows)}</table></td></tr></table></td></tr></table></body></html>'''
    open(f'mail/{wk}.html','w').write(html_);open(f'mail/{wk}.txt','w').write('\n'.join(txt)+'\n')
    meta={'week':wk,'date':w['date'],'subject':subject,'preheader':pre,'web':url,'total':round(t*100,1),'delta':None if dt is None else round(dt,2),'briefing':bool(B),'html':f'/mail/{wk}.html','text':f'/mail/{wk}.txt','sent':False}
    json.dump(meta,open(f'mail/{wk}.json','w'),ensure_ascii=False,indent=1);lst.append(meta)
json.dump({'updated':weeks[-1]['date'] if weeks else None,'issues':list(reversed(lst))},open('mail/index.json','w'),ensure_ascii=False,indent=1)
print('mail issues',len(lst),'briefing',sum(m['briefing'] for m in lst))
