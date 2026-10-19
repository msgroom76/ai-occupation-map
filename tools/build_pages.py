"""주간 리포트 페이지(w/), 사이트맵, robots.txt를 만든다. 표준 라이브러리만 쓴다.
사용: python3 tools/build_pages.py   (저장소 루트에서, weekly.py 다음에)"""
import json,math,os,html as H
BASE='https://ai-occupation-map.pages.dev'
cm=json.load(open('city_meta.json'));idx=json.load(open('index.json'));feed=json.load(open('feed.json'))
R=cm['R'];J=cm['jobs'];WS=sum(j['ws'] for j in J)
def p(r,y,a):m,k,K=R[r];return K/(1+math.exp(-k*(y-m+a.get(r,0))))
def occ(j,y,a):return min(.99,j['cal']*sum(x*p(r,y,a) for r,x in j['w41'].items()))
def tot(a):return sum(j['ws']*occ(j,2026,a) for j in J)/WS
items={n['id']:n for n in feed['items']}
os.makedirs('w',exist_ok=True)
CSS='''*{box-sizing:border-box}body{margin:0;background:#0b0b0f;color:#f5f5f7;font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;line-height:1.6;word-break:keep-all}
main{max-width:680px;margin:0 auto;padding:40px 20px 80px}a{color:#ff8ccd}.brand{font-weight:700;text-decoration:none;color:#f5f5f7}
h1{font-size:30px;line-height:1.3;margin:28px 0 8px;letter-spacing:-.02em}.big{font-size:64px;font-weight:800;color:#ff8ccd;letter-spacing:-.03em;line-height:1.1}
.sub{color:#a1a1aa;font-size:15px}h2{font-size:19px;margin:40px 0 10px}table{width:100%;border-collapse:collapse;font-size:15px}td,th{padding:9px 6px;border-bottom:1px solid #26262b;text-align:left}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}ul{padding-left:20px}li{margin:6px 0}.cta{display:inline-block;margin-top:28px;background:#ff8ccd;color:#111;font-weight:700;padding:12px 20px;border-radius:999px;text-decoration:none}
.foot{margin-top:48px;font-size:13px;color:#71717a}'''
pages=[]
weeks=[w for w in idx['weeks'] if w.get('total') is not None]
for i,w in enumerate(weeks):
    prev=weeks[i-1] if i else None
    t=tot(w['adj']);dt=(t-tot(prev['adj']))*100 if prev else None
    mv=[]
    if prev:
        for j in J:
            d=(occ(j,2026,w['adj'])-occ(j,2026,prev['adj']))*100
            if d>=0.05: mv.append((d,j))
        mv.sort(key=lambda x:-x[0])
    ap=[items[a] for a in w.get('applied',[]) if a in items]
    wk=w['week'];num=wk.split('-W')[1]
    title=f"{wk[:4]}년 {int(num)}주차 AI 점령률 {t*100:.1f}%"
    lede=(f"지난주보다 {dt:+.2f}%p. " if dt is not None and abs(dt)<0.1 else f"지난주보다 {dt:+.1f}%p. " if dt is not None else "첫 주간 지수예요. ")+f"한국 취업자 2,904만 명이 하는 일 가운데 AI가 이미 해낼 수 있는 몫이에요."
    rows=''.join(f'<tr><td><a href="/j/{j["code"]}">{H.escape(j["name"])}</a></td><td class="n">{occ(j,2026,w["adj"])*100:.0f}%</td><td class="n">+{d:.1f}%p</td></tr>' for d,j in mv[:8])
    news=''.join(f'<li><a href="{H.escape(n["url"])}" rel="noopener">{H.escape(n["hd"])}</a> <span class="sub">· {H.escape(n["src"])} · {H.escape(n["tier"])}</span></li>' for n in ap)
    top=sorted(J,key=lambda j:-occ(j,2026,w['adj']))[:5]
    toprows=''.join(f'<tr><td><a href="/j/{j["code"]}">{H.escape(j["name"])}</a></td><td class="n">{occ(j,2026,w["adj"])*100:.0f}%</td><td class="n">{j["ws"]:.0f}만 명</td></tr>' for j in top)
    body=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · AI 점령 지도</title><meta name="description" content="{H.escape(lede)}">
<meta property="og:type" content="article"><meta property="og:title" content="{title}"><meta property="og:description" content="{H.escape(lede)}"><meta property="og:image" content="{BASE}/og.png"><meta property="og:url" content="{BASE}/w/{wk}">
<meta name="twitter:card" content="summary_large_image"><link rel="canonical" href="{BASE}/w/{wk}"><style>{CSS}</style></head><body><main>
<a class="brand" href="/">AI 점령 지도</a><div class="sub">{w["date"]} 발표 · 주간 지수</div>
<h1>{wk[:4]}년 {int(num)}주차 AI 점령률</h1><div class="big">{t*100:.1f}%</div><p>{H.escape(lede)}</p>
{'<h2>이번 주 반영된 소식</h2><ul>'+news+'</ul>' if news else '<h2>이번 주 반영된 소식</h2><p class="sub">숫자를 움직인 확인된 소식이 없었어요.</p>'}
{'<h2>이번 주 많이 오른 직업</h2><table><tr><th>직업</th><th class="n">노출도</th><th class="n">변화</th></tr>'+rows+'</table>' if rows else ''}
<h2>가장 많이 노출된 직업</h2><table><tr><th>직업</th><th class="n">노출도</th><th class="n">취업자</th></tr>{toprows}</table>
<a class="cta" href="/">내 직업 찾아보기</a>
<p class="foot">노출도: Eloundou 외(2024, Science)·ILO Gmyrek 외(2025) 평균 · 업무: O*NET 30.0 · 취업자: 국가데이터처 지역별고용조사 2025년 하반기. 연도별 경로와 소식 반영은 AI 점령 지도의 추정이에요. 직업 단위의 경향이며 개인 평가나 인원 감축의 근거로 쓸 수 없어요. <a href="/w/">지난 주간 지수</a></p>
</main></body></html>'''
    open(f'w/{wk}.html','w').write(body);pages.append((wk,title,w['date']))
lst=''.join(f'<li><a href="/w/{wk}">{H.escape(t)}</a> <span class="sub">· {d}</span></li>' for wk,t,d in reversed(pages))
open('w/index.html','w').write(f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>주간 지수 · AI 점령 지도</title><link rel="canonical" href="{BASE}/w/"><style>{CSS}</style></head><body><main><a class="brand" href="/">AI 점령 지도</a><h1>주간 지수</h1><p class="sub">매주 월요일 아침, 지난주 확인된 AI 소식을 반영해 발표해요.</p><ul>{lst or '<li class="sub">첫 발표 전이에요.</li>'}</ul></main></body></html>''')
exec(open('tools/build_jobs.py').read(),{'__name__':'build_jobs'})
urls=[BASE+'/',BASE+'/w/']+[f'{BASE}/w/{wk}' for wk,_,_ in pages]+json.load(open('j/_urls.json'))
open('sitemap.xml','w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{u}</loc></url>\n' for u in urls)+'</urlset>\n')
open('robots.txt','w').write(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
print('weeks',len(pages),'urls',len(urls))
