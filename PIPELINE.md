# AI 점령지도 운영 규칙

이 저장소는 Cloudflare Pages가 main 브랜치에 push될 때마다 자동 배포한다. 빌드 없음, 출력 디렉터리 `/`.

## 파일
- `feed.json` — AI 소식 목록. 하루 세 번(08:00, 12:00, 18:00 KST) 갱신. **숫자는 움직이지 않는다.**
- `index.json` — 주간 지수 기록. 매주 월요일 08:00 KST에 `tools/weekly.py`로 한 주를 추가. **숫자는 여기서만 움직인다.**
- `config.json` — 광고 설정. `ads.enabled`가 false면 광고 자리를 그리지 않는다.
- `city_*.png`, `city_meta.json`, `ksco_titles.json` — 지도와 직업 사전. 손대지 않는다.

## 소식 항목 (feed.json items[])
| 필드 | 뜻 |
|---|---|
| id | `YYYY-MM-DD-짧은영문` 고유값. 같은 소식을 두 번 넣지 않는다 |
| ts | 기사·발표 시각 (ISO, +09:00) |
| src, url | 출처 이름과 원문 링크. 링크는 직접 열어 확인한 것만 |
| tier | `1차 출처`(기업·정부 공식 발표 원문) / `신뢰 매체`(주요 언론·전문지) / `확인 필요`(요약 매체, 커뮤니티, 원문 미확인) |
| sig | `능력` / `도입` / `규제` / `정책` / `고용` |
| us | 미국 발표면 true (반영 절반). 국내면 `kr: true` |
| hd | 한국어 제목 한 줄. 과장 없이 사실만 |
| r | 영향받는 O*NET 업무 코드(A1–D17) 0~3개. 능력·도입만. 규제·정책·고용은 [] |
| st | `pending`(다음 월요일 반영) / `hold`(확인 필요, 반영 안 함) / `none`(수치 영향 없음) / `applied`(반영됨, weekly.py가 씀) |
| note | hold·none일 때 이유 한 줄 |

규칙: tier가 `확인 필요`면 st는 반드시 `hold`. 1차 출처를 찾으면 tier와 url을 원문으로 바꾸고 `pending`으로 올린다. 목록은 최근 60건만 남긴다(applied가 아닌 오래된 것부터 정리, applied는 index.json에 id가 남아 있으므로 지워도 된다).

## 업무 코드
A1 정보 찾아 모으기 · A2 상황 지켜보기 · A3 사물·사건 알아보기 · A4 장비·재료 점검 · A5 수량·비용 가늠
B1 질 판단하기 · B2 정보 처리하기 · B3 기준 충족 평가 · B4 데이터 분석 · B5 결정·문제 풀기 · B6 창의적으로 생각하기 · B7 지식 활용 · B8 목표·전략 세우기 · B9 일정 짜기 · B10 우선순위 정하기
C1 몸 쓰는 반복 작업 · C2 물건 옮기기 · C3 기계·공정 제어 · C4 차량·장비 운전 · C5 컴퓨터로 일하기 · C6 설계·도면 · C7 기계 수리·정비 · C8 전자 장비 정비 · C9 기록·문서화
D1 풀어 설명하기 · D2 동료와 소통 · D3 고객 응대 · D4 관계 맺기 · D5 돌보기 · D6 팔고 설득하기 · D7 갈등 조정 · D8 대중 앞에서 · D9 남의 일 조율 · D10 팀 만들기 · D11 가르치기 · D12 지휘하기 · D13 코칭 · D14 상담·조언 · D15 행정 처리 · D16 채용·배치 · D17 자원 관리

## 주간 작업이 함께 만드는 파일
- `python3 tools/weekly.py YYYY-MM-DD` → index.json에 한 주 추가
- `python3 tools/build_pages.py` → `w/<주>.html` 주간 리포트, `w/index.html` 목록, 직업 페이지 `j/<코드>.html`(중분류 56 + 소분류 154, tools/build_jobs.py), `sitemap.xml`, `robots.txt`, 주간 메일 원고 `mail/<주>.html·.txt·.json`과 `mail/index.json`(tools/build_mail.py, 발송 전 보관용 · 검색 제외 · 수신 거부 링크는 `{{unsubscribe_url}}` 자리표시)
- `python3 tools/build_share.py` → `og/<코드>.png` 미리보기(그 주 숫자로). playwright가 없으면 건너뛴다.

## 서버 기능 (functions/, Cloudflare Pages Functions)
- `POST /api/e` 행동 집계(날짜·이벤트·라벨별 횟수만). `POST /api/subscribe` 뉴스레터 구독. `POST /api/contact` 기관·기업 문의. `GET /api/stats?k=…` 운영자 집계 조회.
- Cloudflare Pages 프로젝트 설정 → 바인딩에 D1 데이터베이스를 `DB` 이름으로 연결해야 저장된다(표는 첫 요청 때 자동 생성). 환경 변수 `STATS_KEY`를 넣어야 집계 조회가 열린다.
- 바인딩이 없으면 집계는 조용히 건너뛰고, 구독·문의는 '준비 중' 안내를 돌려준다.
