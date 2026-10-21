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
- `python3 tools/build_pages.py` → `w/<주>.html` 주간 리포트, `w/index.html` 목록, 직업 페이지 `j/<코드>.html`(중분류 56 + 소분류 154, tools/build_jobs.py), `sitemap.xml`, `robots.txt`, 주간 메일 원고 `mail/<주>.html·.txt·.json`과 `mail/index.json`(tools/build_mail.py, 발송 전 보관용 · 브리핑 원고 `mail/brief/<주>.json`이 있으면 브리핑형으로, 형식은 build_mail.py 맨 위 설명 · 지난 호는 다시 만들지 않음 · 검색 제외 · 수신 거부 링크는 `{{unsubscribe_url}}` 자리표시)
- `python3 tools/build_share.py` → `og/<코드>.png` 미리보기(그 주 숫자로). playwright가 없으면 건너뛴다.

## 서버 기능 (functions/, Cloudflare Pages Functions)
- `POST /api/e` 행동 집계(날짜·이벤트·라벨별 횟수만). `POST /api/subscribe` 뉴스레터 구독. `POST /api/contact` 기관·기업 문의. `GET /api/stats?k=…` 운영자 집계 조회.
- Cloudflare Pages 프로젝트 설정 → 바인딩에 D1 데이터베이스를 `DB` 이름으로 연결해야 저장된다(표는 첫 요청 때 자동 생성). 환경 변수 `STATS_KEY`를 넣어야 집계 조회가 열린다.
- 바인딩이 없으면 집계는 조용히 건너뛰고, 구독·문의는 '준비 중' 안내를 돌려준다.

## 데이터 파이프라인 (pipeline/)
지도 데이터(`city_meta.json`, `city_index.png`, `city_roads.png`, `ksco_titles.json`, `ksco_soc_map.json`)를 원자료부터 다시 만드는 스크립트와 입력 자료. 숫자를 고치거나 자료를 새로 받았을 때 여기서 다시 만든다.
- 실행: `bash pipeline/run.sh` → `pipeline/out/`에 결과(약 40초). 저장소의 실제 파일은 건드리지 않는다. `python3 pipeline/verify.py`로 지금 파일과 비교한 뒤, 바꿀 때만 손으로 복사한다.
- 순서: 직업명 사전(build_titles) → 중분류 골격(build_v3) → 업무 곡선(real_gwa, real_curves) → 업무 구성(real_profiles2, apply_profiles) → 소분류(real_small, isco_occ, usage_agg, real_blend, update_v3b) → 지도(samples/make19, post19, post20, groups, post21). 자세한 흐름은 `run.sh` 주석.
- 입력: `pipeline/inputs/` (출처와 이용 조건은 `inputs/SOURCES.md`). O*NET은 쓰는 부분만 뽑아 두었다(`scripts/extract_onet.py`).
- 고정본: `inputs/bak18/city_meta.json`(옛 시연판, 업무 41개 이름표와 옛 직업 이름만 씀), `inputs/dl_lfs/occ_2025h2.json`(KOSIS 응답을 표로 옮긴 스크립트가 남아 있지 않음).
- 복원 스크립트: `apply_profiles.py`, `isco_occ.py`, `usage_agg.py`는 당시 대화 중에 바로 실행해 파일로 남지 않은 단계를 다시 쓴 것. 원래 결과와 바이트 단위로 같음을 확인했다.
- 결과는 값과 픽셀이 지금 파일과 같다. `city_meta.json`만 JSON 키 순서가 다르다(원래 실행은 파이썬 해시 순서가 매번 달랐고, run.sh는 PYTHONHASHSEED=0으로 고정).
- 필요한 환경: Python 3, numpy, scipy, pandas, openpyxl, Pillow, matplotlib, Noto Sans CJK 글꼴(`/usr/share/fonts/opentype/noto/`, 이름표 위치가 글꼴 크기에 따라 달라짐).
- 이용 조건: O*NET CC BY 4.0, GPTs-are-GPTs MIT, 고용24 매핑정보 제한 없음, KOSIS·ILO·Anthropic 경제지수(CC BY)는 출처 표시. Microsoft 적용도 자료와 ILO 자료는 재배포 조건을 확인해야 한다.

## 변경 기록 (숫자가 바뀐 변경)
| 날짜 | 버전 | 무엇이 바뀌었나 | 전체 2026 노출도 |
|---|---|---|---|
| 2026-10-19 | v0.14 | 한국 직업 ↔ ISCO 연결을 손으로 만든 표에서 국가데이터처 공식 연계표(2025.11.03)로 교체. ILO 값이 소분류 163개 모두 새로 계산됨(직업별 평균 ±0.9%p, 가장 큰 변화: 기획·영업·인사 사무 +8%p, 공공행정 사무 −4%p, 영업직 −4%p). 지난 주간 지수(W42·W43)도 같은 기준으로 다시 계산(index.json의 `rebased`) | 31.4% → 31.5% |

## 세부 작업 매칭 (feed.json의 `dwa`, tasks.json)
- `tasks.json` — 직업별 세부 작업(O*NET DWA) 목록. pipeline/scripts/build_tasks.py가 만든다. 세분류(4자리)는 국가데이터처 KSCO↔ISCO 연계표 → O*NET의 ESCO↔O*NET-SOC 연계표로 '세부 직무' 후보(최대 6개)를 잇고, 소분류·중분류는 SOC 연결표로 잇는다. 한국어 이름은 pipeline/inputs/tasks_ko/(처음 한 번 번역한 고정본).
- 소식마다 `dwa`: `[["DWA ID","수준"], …]` 0~6개. 수준 `f` 완성(사람 손 없이 끝냄) · `d` 초안(첫 결과물을 대신 만듦) · `a` 보조(하는 일을 도움). 발표 내용에 적힌 기능만, 가장 직접적인 작업만 붙인다. 범용 모델 출시처럼 특정 작업을 말하지 않는 소식은 비워 둔다.
- 찾기: `python3 tools/find_dwa.py 낱말…` (한국어·영어), `--job 2955`(그 직업의 작업 목록). tasks.json에 있는 ID만 쓴다(점검이 막는다).
- 화면: 직업 카드의 '이 발표가 닿는 내 업무'. 사용자가 세부 직무를 고르고, 하지 않는 업무는 체크를 풀어 계산에서 뺀다(이 기기에만 저장). 지수 숫자에는 영향 없음.
