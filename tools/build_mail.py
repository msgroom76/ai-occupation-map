"""주간 메일(뉴스레터) 원고를 주마다 만들어 쌓아둔다. 표준 라이브러리만 쓴다.
사용: build_pages.py 끝에서 자동 실행. 단독 실행도 가능(저장소 루트에서 python3 tools/build_mail.py).
결과: mail/<주>.html(메일용 HTML, 인라인 스타일) · mail/<주>.txt(텍스트판) · mail/<주>.json(제목·미리보기 문구)
      mail/index.json(전체 목록). 발송은 아직 안 함. 발송 도구를 붙이면 {{unsubscribe_url}}만 바꿔 넣으면 된다."""
import json,math,os,html as H
from datetime import date,timedelta
BASE='https://ai-occupation-map.pages.dev'
cm=json.load(open('city_meta.json'));idx=json.load(open('index.json'));feed=json.load(open('feed.json'))
R=cm['R'];J=cm['jobs'];WS=sum(j['ws'] for j in J)
def p(r,y,a):m,k,K=R[r];return K/(1+math.exp(-k*(y-m+a.get(r,0))))
def occ(j,y,a):return min(.99,j['cal']*sum(x*p(r,y,a) for r,x in j['w41'].items()))
def tot(a):return sum(j['ws']*occ(j,2026,a) for j in J)/WS
items={n['id']:n for n in feed['items']}
os.makedirs('mail',exist_ok=True)
INK='#16161a';MUT='#6b6b76';LINE='#e6e6ea';PINK='#8a085a';BG='#f6f6f8'
F='-apple-system,BlinkMacSystemFont,\'Apple SD Gothic Neo\',\'Malgun Gothic\',\'Noto Sans KR\',sans-serif'
def a(u,t,c=PINK):return f'<a href="{H.escape(u)}" style="color:{c};text-decoration:underline">{H.escape(t)}</a>'
def h2(t):return f'<tr><td style="padding:32px 0 8px;font:700 13px/1.4 {F};letter-spacing:.06em;color:{PINK}">{t}</td></tr>'
def table(head,rows):
    th=''.join(f'<td style="padding:8px 0;border-bottom:1px solid {INK};font:600 12px {F};color:{MUT};text-align:{"right" if i else "left"}">{h}</td>' for i,h in enumerate(head))
    tr=''.join('<tr>'+''.join(f'<td style="padding:9px 0;border-bottom:1px solid {LINE};font:15px/1.4 {F};color:{INK};text-align:{"right" if i else "left"}">{c}</td>' for i,c in enumerate(r))+'</tr>' for r in rows)
    return f'<tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{th}</tr>{tr}</table></td></tr>'
def para(t,c=INK,s=15):return f'<tr><td style="padding:4px 0;font:{s}px/1.65 {F};color:{c}">{t}</td></tr>'
weeks=[w for w in idx['weeks'] if w.get('total') is not None];lst=[]
for i,w in enumerate(weeks):
    prev=weeks[i-1] if i else None;wk=w['week'];num=int(wk.split('-W')[1])
    t=tot(w['adj']);dt=(t-tot(prev['adj']))*100 if prev else None
    mv=[]
    if prev:
        for j in J:
            d=(occ(j,2026,w['adj'])-occ(j,2026,prev['adj']))*100
            if d>=0.05:mv.append((d,j))
        mv.sort(key=lambda x:-x[0])
    ap=[items[x] for x in w.get('applied',[]) if x in items]
    end=date.fromisoformat(w['date']);start=date.fromisoformat(prev['date']) if prev else end-timedelta(days=7)
    seen=[n for n in feed['items'] if start.isoformat()<n['ts'][:10]<=end.isoformat() and n['id'] not in w.get('applied',[])]
    seen.sort(key=lambda n:(not n.get('kr'),n['ts']),reverse=False);seen=seen[:5]
    top=sorted(J,key=lambda j:-occ(j,2026,w['adj']))[:5]
    dtxt=('첫 주간 지수예요' if dt is None else f'지난주보다 {dt:+.2f}%p' if abs(dt)<0.1 else f'지난주보다 {dt:+.1f}%p')
    subject=f'[AI 점령 지도] {num}주차 {t*100:.1f}% · {dtxt}'
    pre=(f'이번 주 숫자를 움직인 소식: {ap[0]["hd"]}' if ap else '이번 주에는 숫자를 움직인 확인된 소식이 없었어요.')[:90]
    url=f'{BASE}/w/{wk}'
    rows=[]
    rows.append(f'<tr><td style="padding:0 0 4px;font:600 13px {F};color:{MUT}">AI 점령 지도 · {wk[:4]}년 {num}주차 · {w["date"]} 발표</td></tr>')
    rows.append(f'<tr><td style="padding:20px 0 0;font:600 15px {F};color:{INK}">이번 주 AI 점령률</td></tr>')
    rows.append(f'<tr><td style="padding:0;font:800 64px/1.05 {F};letter-spacing:-.03em;color:{PINK}">{t*100:.1f}%</td></tr>')
    rows.append(para(f'{dtxt}. 한국 취업자 2,904만 명이 하는 일 가운데 AI가 이미 해낼 수 있는 몫이에요.'))
    rows.append(h2('01 — 이번 주 숫자를 움직인 소식'))
    if ap:
        for n in ap:rows.append(para(f'{a(n["url"],n["hd"],INK)}<br><span style="color:{MUT};font-size:13px">{H.escape(n["src"])} · {H.escape(n["tier"])}</span>'))
    else:rows.append(para('숫자를 움직인 확인된 소식이 없었어요. 발표나 실제 도입이 확인된 소식만 반영해요.',MUT))
    if seen:
        rows.append(h2('02 — 지켜보는 소식'))
        rows.append(para('아직 숫자에는 넣지 않았지만, 확인되면 다음 주에 반영할 수 있는 소식이에요.',MUT,13))
        for n in seen:rows.append(para(f'{a(n["url"],n["hd"],INK)}<br><span style="color:{MUT};font-size:13px">{H.escape(n["src"])} · {H.escape(n["sig"])}</span>'))
    k=3 if seen else 2
    if mv:
        rows.append(h2(f'0{k} — 이번 주 많이 오른 직업'));k+=1
        rows.append(table(['직업','노출도','변화'],[[a(f'{BASE}/j/{j["code"]}',j['name'],INK),f'{occ(j,2026,w["adj"])*100:.0f}%',f'+{d:.1f}%p'] for d,j in mv[:6]]))
    rows.append(h2(f'0{k} — 가장 많이 노출된 직업'))
    rows.append(table(['직업','노출도','취업자'],[[a(f'{BASE}/j/{j["code"]}',j['name'],INK),f'{occ(j,2026,w["adj"])*100:.0f}%',f'{j["ws"]:.0f}만 명'] for j in top]))
    rows.append(f'<tr><td style="padding:32px 0 0"><a href="{BASE}/" style="display:inline-block;background:{INK};color:#fff;font:700 15px {F};padding:13px 22px;text-decoration:none">내 직업 찾아보기 →</a></td></tr>')
    rows.append(f'<tr><td style="padding:40px 0 0;border-bottom:1px solid {INK}"></td></tr>')
    rows.append(para(f'노출도: Eloundou 외(2024, Science)·ILO Gmyrek 외(2025) 평균 · 업무: O*NET 30.0 · 취업자: 국가데이터처 지역별고용조사 2025년 하반기. 연도별 경로와 소식 반영은 AI 점령 지도의 추정이에요. 직업 단위의 경향이며 개인 평가나 인원 감축의 근거로 쓸 수 없어요.',MUT,12))
    rows.append(para(f'{a(url,"웹에서 보기",MUT)} · {a("{{unsubscribe_url}}","수신 거부",MUT)}<br>이 메일은 AI 점령 지도에서 주간 지수 받기를 신청한 분께 보내요.',MUT,12))
    html_=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>{H.escape(subject)}</title></head>
<body style="margin:0;padding:0;background:{BG}"><div style="display:none;max-height:0;overflow:hidden;opacity:0">{H.escape(pre)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG}"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fff;border-top:6px solid {PINK}"><tr><td style="padding:32px 28px 36px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{''.join(rows)}</table></td></tr></table></td></tr></table></body></html>'''
    txt=[subject,'',f'이번 주 AI 점령률 {t*100:.1f}% ({dtxt})','한국 취업자 2,904만 명이 하는 일 가운데 AI가 이미 해낼 수 있는 몫이에요.','','■ 이번 주 숫자를 움직인 소식']
    txt+=[f'- {n["hd"]} ({n["src"]})\n  {n["url"]}' for n in ap] or ['- 없음']
    if seen:txt+=['','■ 지켜보는 소식']+[f'- {n["hd"]} ({n["src"]})\n  {n["url"]}' for n in seen]
    if mv:txt+=['','■ 이번 주 많이 오른 직업']+[f'- {j["name"]} {occ(j,2026,w["adj"])*100:.0f}% (+{d:.1f}%p)' for d,j in mv[:6]]
    txt+=['','■ 가장 많이 노출된 직업']+[f'- {j["name"]} {occ(j,2026,w["adj"])*100:.0f}% · {j["ws"]:.0f}만 명' for j in top]
    txt+=['',f'내 직업 찾아보기: {BASE}/',f'웹에서 보기: {url}','','직업 단위의 경향이며 개인 평가나 인원 감축의 근거로 쓸 수 없어요.','수신 거부: {{unsubscribe_url}}']
    open(f'mail/{wk}.html','w').write(html_);open(f'mail/{wk}.txt','w').write('\n'.join(txt)+'\n')
    meta={'week':wk,'date':w['date'],'subject':subject,'preheader':pre,'web':url,'total':round(t*100,1),'delta':None if dt is None else round(dt,2),'html':f'/mail/{wk}.html','text':f'/mail/{wk}.txt','sent':False}
    json.dump(meta,open(f'mail/{wk}.json','w'),ensure_ascii=False,indent=1);lst.append(meta)
json.dump({'updated':weeks[-1]['date'] if weeks else None,'issues':list(reversed(lst))},open('mail/index.json','w'),ensure_ascii=False,indent=1)
print('mail issues',len(lst))
