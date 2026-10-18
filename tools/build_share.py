"""직업별 공유 페이지(j/)와 미리보기 이미지(og/)를 만든다. playwright가 필요하다.
사용: python3 tools/build_share.py (저장소 루트에서)"""
import json,math,os,base64,io,asyncio,html as H
import numpy as np
from PIL import Image
from playwright.async_api import async_playwright
BASE='https://ai-occupation-map.pages.dev'
m=json.load(open('city_meta.json'));idx=json.load(open('index.json'))
R=m['R'];ADJ=idx['weeks'][-1]['adj']
p=lambda r,y:R[r][2]/(1+math.exp(-R[r][1]*(y-R[r][0]+ADJ.get(r,0))))
occ=lambda j,y:min(.99,j['cal']*sum(x*p(r,y) for r,x in j['w41'].items()))
GN={'g1':'관리자','g2':'전문가','g3':'사무','g4':'서비스','g5':'판매','g6':'농림어업','g7':'기능','g8':'기계 조작·조립','g9':'단순노무'}
RAMP=['#552f42','#873e63','#bc4b87','#ed60ac','#ff8ccd']
binc=lambda v:RAMP[min(4,int(v/.2))]
ri=np.array(Image.open('city_index.png'))[...,0]
city=(ri<250)|(ri==250)
os.makedirs('og',exist_ok=True);os.makedirs('j',exist_ok=True)
def mapimg(i):
    sm=city[::3,::3];rg=(ri==i)[::3,::3]
    im=np.zeros(sm.shape+(4,),np.uint8);im[sm]=(58,52,62,255);im[rg]=(255,140,205,255)
    ys,xs=np.nonzero(sm);im=im[ys.min():ys.max()+1,xs.min():xs.max()+1]
    b=io.BytesIO();Image.fromarray(im).save(b,'PNG');return base64.b64encode(b.getvalue()).decode()
TPL=open('tools/share_tpl.html').read()
async def main():
    async with async_playwright() as pw:
        b=await pw.chromium.launch();pg=await b.new_page(viewport={'width':1200,'height':630})
        for i,j in enumerate(m['jobs']):
            v=occ(j,2026);v30=occ(j,2030)
            h=TPL.replace('{{NAME}}',H.escape(j['name'])).replace('{{GROUP}}',GN[j['group']]+' 구역').replace('{{V}}',str(round(v*100))).replace('{{V30}}',str(round(v30*100))).replace('{{W}}',f"{v*100:.1f}").replace('{{COL}}',binc(v)).replace('{{WS}}',f"{round(j['ws']):,}" if j['ws']>=10 else f"{j['ws']:.1f}").replace('{{MAP}}',mapimg(i)).replace('{{FULL}}',H.escape(j['full']))
            await pg.set_content(h);await pg.wait_for_timeout(50)
            await pg.screenshot(path=f"og/{j['code']}.png")
            title=f"{j['name']}, AI가 이미 {round(v*100)}%를 해낼 수 있어요"
            desc=f"표준직업분류 {j['code']} {j['full']} · 취업자 {round(j['ws']) if j['ws']>=10 else j['ws']}만 명 · 2030년 예측 {round(v30*100)}% · AI 점령 지도"
            open(f"j/{j['code']}.html",'w').write(f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{H.escape(title)} · AI 점령 지도</title><meta name="description" content="{H.escape(desc)}">
<meta property="og:type" content="article"><meta property="og:title" content="{H.escape(title)}"><meta property="og:description" content="{H.escape(desc)}">
<meta property="og:image" content="{BASE}/og/{j['code']}.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:url" content="{BASE}/j/{j['code']}">
<meta name="twitter:card" content="summary_large_image"><link rel="canonical" href="{BASE}/#j={j['code']}">
<meta http-equiv="refresh" content="0;url=/#j={j['code']}"></head><body style="background:#0b0b0f;color:#fff;font-family:sans-serif">
<script>var q=new URLSearchParams(location.search).get('q');location.replace('/#j={j['code']}'+(q?'&q='+encodeURIComponent(q):''));</script>
<p><a href="/#j={j['code']}" style="color:#ff8ccd">{H.escape(j['name'])} 지도로 가기</a></p></body></html>''')
        await b.close()
asyncio.run(main())
print('ok',len(m['jobs']))
