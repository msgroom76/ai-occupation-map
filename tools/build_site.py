import shutil,os
src=open('web/index.html').read()
i=src.index('<div class="stage"')
head,body=src[:i],src[i:]
head=head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n','')
og='''<meta name="description" content="사람이 하던 일, AI가 어디까지 들어왔나. 한국 취업자 2,904만 명의 일을 지도로 그리고, AI 소식을 하루 세 번 반영합니다.">
<meta property="og:type" content="website"><meta property="og:title" content="AI 점령 지도 · AI Occupied Map"><meta property="og:description" content="사람의 일, AI가 어디까지 장악했나? 한국 직업 163개의 AI 노출도와 실제 사용을 지도로.">
<meta property="og:image" content="https://ai-occupation-map.pages.dev/og.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:url" content="https://ai-occupation-map.pages.dev/"><meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#0b0b0f">
'''
html='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>[hidden]{display:none!important}</style>\n'+og+head+'</head><body>\n'+body+'\n<!-- Cloudflare Web Analytics --><script defer src=\'https://static.cloudflareinsights.com/beacon.min.js\' data-cf-beacon=\'{"token": "8eb4d903bad84bb89dd088032173bafb"}\'></script><!-- End Cloudflare Web Analytics -->\n</body></html>\n'
os.makedirs('site',exist_ok=True)
open('site/index.html','w').write(html)
for f in ['city_index.png','city_roads.png','city_meta.json','ksco_titles.json']: shutil.copy('web/'+f,'site/'+f)
open('site/_headers','w').write('''/*.json
  Cache-Control: no-cache
/*.png
  Cache-Control: public, max-age=86400
/
  Cache-Control: no-cache
''')
print('built')
