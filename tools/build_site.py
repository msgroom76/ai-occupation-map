"""사이트 페이지 만들기: 마스터(tools/site_src/*.html) → 저장소 루트의 index.html·test.html·org.html.
저장소 루트에서: python3 tools/build_site.py
- 지도 검색 코드(/*@SEARCH@*/)와 공통 헤더·메뉴(자리표시 <!--@GNAV..@-->, <!--@HEADER:..@-->)를 여기서 채운다. 메뉴는 NAV 한 곳만 고치면 된다.
- 작업 폴더(web/·site/)에서 돌리면 예전처럼 site/에 만든다."""
import shutil,os
REPO=os.path.isdir('functions')
W='tools/site_src/' if REPO else 'web/'
O='' if REPO else 'site/'

# ===== 공통 헤더: 메뉴를 바꿀 때는 여기 NAV만 고친다 =====
NAV=[('/','지도'),('/test','내 직업 전망'),('/org','기업 자가 진단')]
def gnav(cur,cls='gnav'):
    return f'<nav class="{cls}" aria-label="주요 메뉴">'+''.join(f'<a href="{h}"'+(' aria-current="page"' if h==cur else '')+f'>{t}</a>' for h,t in NAV)+'</nav>'
# 메뉴 모양(지도·하위 페이지 공통). 색은 각 페이지 변수(--ink, --ink2, --hot)를 쓴다
GNAV_CSS=""".gnav{display:flex;align-items:center;gap:4px;flex:none}
.gnav a{display:inline-flex;align-items:center;justify-content:center;min-height:36px;padding:0 12px;font-size:14px;font-weight:600;color:var(--ink2);text-decoration:none;border-bottom:2px solid transparent;white-space:nowrap}
.gnav a:hover{color:var(--ink)}.gnav a[aria-current="page"]{color:var(--ink);border-bottom-color:var(--hot)}
.gnav a:focus-visible{outline:2px solid var(--hot);outline-offset:2px}
@media (max-width:899px){.gnav{gap:0}.gnav a{flex:1;min-height:32px;padding:0 4px;font-size:13.5px}}
"""
# 하위 페이지 헤더: 지도 위 막대와 같은 높이(데스크톱 64px, 휴대폰 62px + 메뉴 줄)·같은 로고·같은 아래 선
GH_CSS=GNAV_CSS+""".gh{position:sticky;top:0;z-index:30;display:flex;align-items:center;gap:14px;min-height:64px;box-sizing:border-box;padding:calc(11px + env(safe-area-inset-top,0px)) 16px 11px;background:var(--bg);border-bottom:1px solid var(--ink)}
.gh-mark{display:flex;align-items:center;gap:5px;color:var(--hot);text-decoration:none;font-family:Inter,'Helvetica Neue',Arial,sans-serif;font-weight:700;flex:none}
.gh-mark b{font-size:36px;letter-spacing:-.045em;line-height:.8}.gh-mark span{font-size:11.5px;line-height:1.02;letter-spacing:-.02em}
.gh .gnav{margin-left:auto}
@media (max-width:899px){.gh{flex-wrap:wrap;row-gap:4px;min-height:0;padding:calc(10px + env(safe-area-inset-top,0px)) 12px 10px}.gh-mark{min-height:46px}.gh-mark b{font-size:30px}.gh-mark span{font-size:10px}.gh .gnav{width:100%;margin:0 -4px}}
html{scroll-padding-top:76px}@media (max-width:899px){html{scroll-padding-top:115px}}
@media print{.gh{display:none}}
"""
# 지도 쪽 강조색은 로고색(--c100)에 맞춘다
MAP_GNAV_FIX=".topbar .gnav a[aria-current=page],.gnav-sheet a[aria-current=page]{border-bottom-color:var(--c100)}\n"
FONT='<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@700&display=swap">'
def header(cur):
    return '<header class="gh"><a class="gh-mark" href="/" aria-label="AI 점령 지도 처음으로"><b>AI</b><span>Occupied<br>Map</span></a>'+gnav(cur)+'</header>'
def apply(t):
    import re
    t=t.replace('/*@GNAV_CSS@*/',GNAV_CSS+MAP_GNAV_FIX).replace('/*@GH_CSS@*/',GH_CSS)
    t=t.replace('<!--@GNAV:/@-->',gnav('/')).replace('<!--@GNAV_SHEET@-->',gnav('/','gnav gnav-sheet'))
    t=re.sub(r'<!--@HEADER:(/[a-z]*)@-->',lambda m:header(m.group(1)),t)
    if '<!--@HEADER' in t or 'class="gh"' in t and FONT not in t: t=t.replace('</head>',FONT+'</head>',1)
    assert '@GNAV' not in t and '@GH_CSS' not in t and '@HEADER' not in t
    return t
src=open(W+'index.html').read()
i=src.index('<div class="stage"')
head,body=src[:i],src[i:]
head=head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n','')
og='''<meta name="description" content="사람이 하던 일, AI가 어디까지 들어왔나. 한국 취업자 2,904만 명의 일을 지도로 그리고, AI 소식을 하루 세 번 반영합니다.">
<meta property="og:type" content="website"><meta property="og:title" content="AI 점령 지도 · AI Occupied Map"><meta property="og:description" content="사람의 일, AI가 어디까지 장악했나? 한국 직업 163개의 AI 노출도와 실제 사용을 지도로.">
<meta property="og:image" content="https://aijido.org/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:url" content="https://aijido.org/"><meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#0b0b0f">
'''
html='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>[hidden]{display:none!important}</style>\n'+og+head+'</head><body>\n'+body+'\n<!-- Cloudflare Web Analytics --><script defer src=\'https://static.cloudflareinsights.com/beacon.min.js\' data-cf-beacon=\'{"token": "8eb4d903bad84bb89dd088032173bafb"}\'></script><!-- End Cloudflare Web Analytics -->\n</body></html>\n'
os.makedirs(O or '.',exist_ok=True)
open(O+'index.html','w').write(apply(html))
if not REPO:
  for f in ['city_index.png','city_roads.png','city_meta.json','ksco_titles.json']: shutil.copy('web/'+f,'site/'+f)
if not REPO: open('site/_headers','w').write('''/*.json
  Cache-Control: no-cache
/*.png
  Cache-Control: public, max-age=86400
/
  Cache-Control: no-cache
''')
print('built')
# 물때 테스트(/test): 검색 코드는 지도 페이지의 것을 그대로 가져다 쓴다(직업명 사전·별칭이 한 곳에서 관리되게)
t=open(W+'test.html').read()
a=src.index('// ---------- 검색 ----------');b=src.index('function wireSearch',a)
assert '/*@SEARCH@*/' in t
open(O+'test.html','w').write(apply(t.replace('/*@SEARCH@*/',src[a:b])))
print('built test')
# 조직 자가 진단(/org): 같은 검색 코드를 주입
o=open(W+'org.html').read()
assert '/*@SEARCH@*/' in o
open(O+'org.html','w').write(apply(o.replace('/*@SEARCH@*/',src[a:b])))
print('built org')
