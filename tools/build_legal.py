# 개인정보처리방침·이용약관·소개 페이지를 만든다. 사용: python3 tools/build_legal.py (저장소 루트에서). 고칠 때는 이 파일을 고치고 다시 실행한다.
import os
OUT=''
EFF='2026년 10월 21일'
CONTACT='msgr@post-office.kr'
HEAD='''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · AI 점령 지도</title><meta name="description" content="{desc}"><link rel="canonical" href="https://aijido.org/{slug}">
<style>*{{box-sizing:border-box}}:root{{--bg:#f3f3f6;--ink:#1c1c1e;--ink2:rgba(60,60,67,.8);--hair:rgba(28,28,30,.16);--hot:#a3206f;color-scheme:light}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0b0c10;--ink:#f5f5f7;--ink2:rgba(235,235,245,.72);--hair:rgba(245,245,247,.18);--hot:#ff8ccd;color-scheme:dark}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Pretendard Variable",Pretendard,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;font-size:15px;line-height:1.75;word-break:keep-all}}
main{{max-width:720px;margin:0 auto;padding:28px 20px 72px}}a{{color:inherit}}
.top{{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--ink);padding-bottom:10px;font-size:13px}}
.brand{{font-weight:700;text-decoration:none}}.brand b{{color:var(--hot)}}
h1{{font-size:30px;line-height:1.25;letter-spacing:-.035em;margin:36px 0 6px}}.sub{{color:var(--ink2);font-size:13px;margin:0 0 8px}}
h2{{font-size:17px;letter-spacing:-.02em;border-top:1px solid var(--ink);padding-top:12px;margin:40px 0 10px}}
p,li{{margin:6px 0}}ul,ol{{padding-left:20px}}.note{{color:var(--ink2);font-size:13px}}
table{{width:100%;border-collapse:collapse;font-size:14px;margin:8px 0}}td,th{{padding:8px 8px 8px 0;border-bottom:1px solid var(--hair);text-align:left;vertical-align:top}}th{{font-weight:600;font-size:13px;color:var(--ink2)}}
.wrap{{overflow-x:auto}}@media (max-width:600px){{table,tbody,tr,td{{display:block;width:100%}}tr:first-child{{display:none}}tr{{border-bottom:1px solid var(--hair);padding:8px 0}}td{{border:0;padding:2px 0}}td[data-l]::before{{content:attr(data-l);display:block;font-size:12px;color:var(--ink2)}}td:first-child{{font-weight:700}}}}footer{{margin-top:56px;border-top:1px solid var(--ink);padding-top:12px;font-size:13px;color:var(--ink2);display:flex;gap:16px;flex-wrap:wrap}}footer a{{text-decoration:none;padding:6px 0}}
</style></head><body><main>
<div class="top"><a class="brand" href="/"><b>AI</b> 점령 지도</a><span>aijido.org</span></div>
<h1>{title}</h1><p class="sub">{sub}</p>
'''
FOOT='''<footer><a href="/">지도</a><a href="/w/">주간 리포트</a><a href="/about">소개</a><a href="/privacy">개인정보처리방침</a><a href="/terms">이용약관</a></footer>
</main></body></html>'''
import re
def labels(body):
    def fix(m):
        t=m.group(0);hs=re.findall(r'<th>(.*?)</th>',t)
        def row(r):
            cells=re.findall(r'<td>(.*?)</td>',r.group(0))
            if not cells: return r.group(0)
            return '<tr>'+''.join(f'<td data-l="{hs[i]}">{c}</td>' if i else f'<td>{c}</td>' for i,c in enumerate(cells))+'</tr>'
        return re.sub(r'<tr>(?:(?!</tr>).)*</tr>',row,t,flags=re.S)
    return re.sub(r'<table>.*?</table>',fix,body,flags=re.S)
def page(slug,title,desc,sub,body):
    body=labels(body)
    open(OUT+slug+'.html','w').write(HEAD.format(title=title,desc=desc,slug=slug,sub=sub)+body+FOOT)

page('privacy','개인정보처리방침','AI 점령 지도(aijido.org)가 어떤 개인정보를 왜, 얼마 동안 처리하는지 알려드려요.',f'시행일 {EFF} · 운영 포스트오피스',f'''
<p>포스트오피스(이하 '운영자')는 AI 점령 지도(aijido.org, 이하 '서비스')를 운영하면서 「개인정보 보호법」에 따라 이용자의 개인정보를 보호하고, 관련 고충을 빠르게 처리하기 위해 이 처리방침을 둡니다. 서비스는 회원 가입 없이 쓸 수 있고, 꼭 필요한 정보만 받습니다.</p>

<h2>1. 처리하는 개인정보와 목적, 보유 기간</h2>
<div class="wrap"><table><tr><th>구분</th><th>항목</th><th>목적</th><th>보유 기간</th></tr>
<tr><td>주간 메일 구독</td><td>이메일, (선택) 관심 직업, 동의 시각·동의 문구 버전</td><td>구독 확인 메일과 주간 메일 발송</td><td>수신 거부 후 30일 뒤 삭제. 확인 메일을 누르지 않은 신청은 30일 뒤 삭제</td></tr>
<tr><td>기관·기업 문의</td><td>이름, 소속, 이메일, 문의 종류·내용</td><td>문의 답변과 견적 안내</td><td>접수 후 1년 뒤 삭제</td></tr>
<tr><td>'내 일과 비교하면?' 의견</td><td>직업 코드, 의견 방향, 화면에 보인 값, (선택) 메모, 접속 주소를 날짜별 비밀값과 섞어 만든 해시</td><td>같은 의견의 반복 제출 막기, 숫자 점검 대상 고르기</td><td>해시는 이틀 뒤 삭제, 메모는 1년 뒤 삭제</td></tr>
<tr><td>이용 통계</td><td>날짜별 기능 사용 횟수(예: 검색한 직업명, 연 화면 이름). 개인을 알아볼 수 있는 정보는 받지 않습니다</td><td>서비스 개선</td><td>400일 뒤 삭제</td></tr>
</table></div>
<p class="note">메모나 문의 내용에 주민등록번호·건강 정보 같은 민감한 정보를 적지 말아 주세요. 운영자는 만 14세 미만 아동의 개인정보를 알면서 받지 않습니다.</p>

<h2>2. 기기에만 저장되는 정보</h2>
<p>저장한 직업, 고른 세부 직무, 접은 메뉴 같은 화면 설정은 이용자 브라우저(localStorage)에만 저장되고 운영자에게 보내지 않습니다. 브라우저 설정에서 사이트 데이터를 지우면 함께 지워집니다. 서비스는 광고·추적용 쿠키를 쓰지 않습니다. 방문 통계는 쿠키를 쓰지 않는 Cloudflare Web Analytics로 집계합니다.</p>

<h2>3. 제3자 제공</h2>
<p>운영자는 이용자의 개인정보를 제3자에게 제공하지 않습니다. 법령에 따라 수사기관 등이 요구하는 경우는 예외입니다.</p>

<h2>4. 처리 위탁과 국외 이전</h2>
<p>서비스는 아래 업체의 서버를 이용하며, 이 과정에서 개인정보가 국외(미국 등)에 저장·처리됩니다. 정보는 이용자가 양식을 제출하거나 메일이 발송될 때 암호화된 네트워크로 전송됩니다.</p>
<div class="wrap"><table><tr><th>업체(국가)</th><th>위탁 업무</th><th>이전 항목</th><th>보유 기간</th><th>연락처</th></tr>
<tr><td>Cloudflare, Inc.(미국)</td><td>웹사이트 호스팅, 구독·문의·의견 저장(D1), 방문 통계</td><td>1번 표의 모든 항목</td><td>1번 표와 같음</td><td>PrivacyQuestions@cloudflare.com</td></tr>
<tr><td>Plus Five Five, Inc.(Resend, 미국)</td><td>구독 확인 메일·주간 메일 발송(발송을 시작한 뒤부터)</td><td>이메일, 메일 내용</td><td>발송 기록은 업체 정책에 따름</td><td>support@resend.com</td></tr>
</table></div>
<p>국외 이전을 원하지 않으면 구독·문의·의견을 보내지 않으면 됩니다. 이 경우에도 지도와 모든 콘텐츠는 그대로 이용할 수 있습니다.</p>

<h2>5. 파기 절차와 방법</h2>
<p>보유 기간이 지난 정보는 매일 자동으로 데이터베이스에서 삭제합니다. 복구할 수 없는 방식으로 지우며, 종이 문서는 만들지 않습니다.</p>

<h2>6. 이용자의 권리와 행사 방법</h2>
<ul><li>언제든 자신의 개인정보 열람·정정·삭제·처리 정지를 요구할 수 있습니다. 아래 연락처로 메일을 보내 주시면 10일 안에 처리 결과를 알려드립니다.</li>
<li>주간 메일은 메일마다 있는 '수신 거부' 링크로 바로 끊을 수 있습니다.</li>
<li>구독 동의는 언제든 철회할 수 있고, 철회해도 서비스 이용에 제한이 없습니다.</li></ul>

<h2>7. 안전성 확보 조치</h2>
<ul><li>데이터베이스 접근은 운영자 계정으로만 가능하며, 관리 화면은 별도 비밀값으로 보호합니다.</li>
<li>모든 전송은 HTTPS로 암호화합니다.</li>
<li>의견 제출 시 접속 주소 원문은 저장하지 않고, 날짜별 비밀값과 섞은 해시만 이틀 동안 둡니다.</li></ul>

<h2>8. 개인정보 보호책임자</h2>
<p>개인정보 처리에 관한 문의, 불만, 피해 구제는 아래로 연락해 주세요.</p>
<p>담당: 포스트오피스 운영팀 · 이메일 <a href="mailto:{CONTACT}">{CONTACT}</a></p>

<h2>9. 권익 침해 구제</h2>
<p>개인정보 침해로 상담이 필요하면 아래 기관에 문의할 수 있습니다.</p>
<ul><li>개인정보침해신고센터 (국번 없이) 118 · privacy.kisa.or.kr</li>
<li>개인정보분쟁조정위원회 1833-6972 · www.kopico.go.kr</li>
<li>대검찰청 (국번 없이) 1301 · 경찰청 (국번 없이) 182</li></ul>

<h2>10. 변경</h2>
<p>이 방침을 바꾸면 시행 7일 전에 이 페이지에 알립니다. 이용자에게 불리한 변경은 30일 전에 알립니다. 시행일: {EFF}.</p>
''')

page('terms','이용약관','AI 점령 지도(aijido.org) 이용 조건과 숫자를 읽는 법, 책임 범위를 안내해요.',f'시행일 {EFF} · 운영 포스트오피스',f'''
<h2>1. 서비스</h2>
<p>AI 점령 지도(이하 '서비스')는 포스트오피스(이하 '운영자')가 운영합니다. 한국의 직업별로 생성형 AI가 기술적으로 해낼 수 있는 업무의 비중(노출도)을 연구 자료로 추정해 지도로 보여주고, AI 관련 소식을 업무와 연결해 알려드립니다. 회원 가입 없이 무료로 이용할 수 있습니다.</p>

<h2>2. 숫자를 읽는 법</h2>
<ul><li>노출도는 공개 연구(미국 직업 연구, 국제노동기구 연구 등)를 한국 직업 분류에 연결해 계산한 <b>추정치</b>입니다. 일자리가 사라지는 비율이나 실제로 AI가 쓰이는 비율이 아닙니다.</li>
<li>2026년 이후 값은 예측이며 범위로 보여드립니다. 모형과 자료가 바뀌면 숫자도 바뀝니다. 바뀐 내용은 변경 기록으로 남깁니다.</li>
<li>소식은 원문을 확인한 것만 싣지만, 원문의 내용과 정확성은 각 출처에 책임이 있습니다.</li></ul>

<h2>3. 쓰지 말아야 할 곳</h2>
<p>서비스의 숫자는 개인의 업무 평가, 채용·해고·인원 감축, 임금 결정의 근거로 쓸 수 없습니다. 직업 전체에 대한 참고 자료로만 써 주세요.</p>

<h2>4. 인용과 저작권</h2>
<ul><li>서비스의 글·그림·숫자를 인용할 때는 'AI 점령 지도(aijido.org)'와 해당 주차를 출처로 밝혀 주세요. 상업적으로 대량 복제하거나 재판매하려면 미리 연락해 주세요.</li>
<li>바탕 자료의 권리는 각 원저작자에게 있으며, 출처와 이용 조건은 <a href="/about">소개</a> 페이지에 적었습니다.</li></ul>

<h2>5. 금지 행위</h2>
<p>자동화된 대량 요청으로 서비스에 부담을 주는 행위, 남의 이메일로 구독을 신청하는 행위, 의견·문의 양식으로 광고나 거짓 정보를 보내는 행위를 금지합니다. 이런 요청은 받지 않거나 지울 수 있습니다.</p>

<h2>6. 책임의 한계</h2>
<p>운영자는 숫자와 소식을 정확하게 유지하려고 노력하지만, 그 정확성·완전성을 보증하지 않습니다. 서비스 내용을 근거로 한 결정에 대해 운영자는 고의나 중대한 과실이 없는 한 책임지지 않습니다. 서비스는 점검이나 사정에 따라 바뀌거나 중단될 수 있습니다.</p>

<h2>7. 개인정보</h2>
<p>개인정보 처리는 <a href="/privacy">개인정보처리방침</a>을 따릅니다.</p>

<h2>8. 약관 변경과 문의</h2>
<p>약관을 바꾸면 시행 7일 전에 이 페이지에 알립니다. 이 약관은 대한민국 법을 따릅니다. 문의: <a href="mailto:{CONTACT}">{CONTACT}</a> · 시행일: {EFF}.</p>
''')

page('about','소개','AI 점령 지도를 누가, 왜, 어떤 자료로 만드는지 소개해요.',f'운영 포스트오피스 · 마지막 수정 {EFF}',f'''
<p>AI 점령 지도는 "내 일의 어느 부분을 AI가 할 수 있게 됐나"를 한국 직업 기준으로 쉽게 보여주려고 만든 지도입니다. 지도의 넓이는 실제 취업자 수, 색은 생성형 AI 노출도입니다. 매주 월요일 AI 소식을 확인해 지수를 갱신합니다.</p>

<h2>운영</h2>
<p>포스트오피스(Post Office) — 디자인·브랜딩·콘텐츠 제작을 하는 한국의 크리에이티브 에이전시입니다. 문의: <a href="mailto:{CONTACT}">{CONTACT}</a></p>

<h2>이해관계 고지</h2>
<ul><li>서비스의 자료 정리, 소식 확인, 코드 작성에 Anthropic의 AI(Claude)를 씁니다. 모든 숫자 규칙과 출처는 사람이 정하고 공개합니다.</li>
<li>'실제 사용 확인' 수치는 Anthropic이 공개한 경제지수(Claude 사용 기록, 미국 이용자 위주)를 씁니다. 한 회사 서비스의 기록이라 전체 AI 사용보다 낮거나 치우쳐 있을 수 있습니다.</li>
<li>소식 목록에는 특정 회사의 발표가 들어가지만, 광고비나 대가를 받고 싣는 소식은 없습니다.</li></ul>

<h2>바탕 자료</h2>
<div class="wrap"><table><tr><th>자료</th><th>쓰는 곳</th><th>이용 조건</th></tr>
<tr><td><a href="https://github.com/openai/GPTs-are-GPTs">Eloundou 외, 「GPTs are GPTs」</a> 직업별 노출도, 미국 직업별 고용(OEWS 2021)</td><td>노출도(미국 연구), 업무 가중</td><td>MIT · 미국 정부 공공 저작물</td></tr>
<tr><td><a href="https://www.ilo.org/">국제노동기구(ILO) Gmyrek 외(2025)</a> 생성형 AI 노출 점수</td><td>노출도(국제노동기구)</td><td>CC BY 4.0</td></tr>
<tr><td><a href="https://www.anthropic.com/economic-index">Anthropic 경제지수(2026.3)</a></td><td>실제 사용 확인</td><td>CC BY</td></tr>
<tr><td><a href="https://github.com/microsoft/working-with-ai">Microsoft, Tomlinson 외(2025) AI 적용도</a></td><td>교차 확인용(사이트 숫자에는 쓰지 않음)</td><td>CC BY 4.0</td></tr>
<tr><td><a href="https://www.onetcenter.org/">O*NET 30.0</a>(미국 노동부)</td><td>업무 구성, 세부 작업</td><td>CC BY 4.0</td></tr>
<tr><td>국가데이터처 한국표준직업분류–ISCO 연계표(2025.11), 한국고용정보원 고용24 직업코드 매핑(2026.4)</td><td>한국 직업 연결, 직업명 검색</td><td>출처 표시</td></tr>
<tr><td>국가데이터처 지역별고용조사 2025년 하반기(KOSIS)</td><td>지도 넓이, 취업자 가중</td><td>출처 표시</td></tr></table></div>
<p class="note">계산 방법과 한계는 지도 화면의 '근거' 탭과 직업 페이지의 질문·답변에 적었습니다. 숫자 오류를 발견하면 메일로 알려 주세요.</p>
''')
print('ok')
