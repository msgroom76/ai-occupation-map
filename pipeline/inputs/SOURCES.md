# 입력 자료 출처

`run.sh`는 이 폴더를 작업 폴더에 그대로 복사해서 쓴다. 경로는 처음 만든 작업 폴더와 같은 배치다.

| 경로 | 무엇 | 출처 · 이용 조건 |
|---|---|---|
| `dl_onet/db_30_0_text/` | O*NET 30.0 일부. `Work Activities.txt`, `Task Ratings.txt`는 중요도(IM) 줄과 쓰는 열만 남김(`scripts/extract_onet.py`). 나머지 4개는 원본 그대로 | 미국 노동부 O*NET, https://www.onetcenter.org/dl_files/database/db_30_0_text.zip · CC BY 4.0 |
| `gpts/full_labelset.tsv`, `gpts/occ_level.csv` | 업무·직업별 언어 모델 노출도(α·β·γ) | Eloundou 외(2024) GPTs are GPTs, https://github.com/openai/GPTs-are-GPTs · MIT (`gpts/LICENSE`) |
| `gpts/national_May2021_dl.csv` | 미국 직업별 고용(OEWS 2021년 5월) | 같은 저장소에 포함. 원자료는 미국 노동통계국(공공 저작물) |
| `dl_konet/konet.csv` | 직업명 6,713개 ↔ 한국표준직업분류 8차 세분류 | 한국고용정보원 고용24 직업코드 직업분류코드 매핑정보(2026.04.09) · 이용허락범위 제한 없음 |
| `dl_lfs/occ_2025h2.json` | 직업 소분류별 취업자 수(천 명) | 국가데이터처 지역별고용조사 2025년 하반기, KOSIS DT_1ES3B32J · 출처 표시. **고정본**: KOSIS 화면 응답에서 표로 옮긴 스크립트가 남아 있지 않다 |
| `dl2/Final_Scores_ISCO08_Gmyrek_et_al_2025.xlsx`, `dl2/DATA_DICTIONARY.md` | ISCO-08 업무별 생성형 AI 노출 점수 | ILO Gmyrek 외(2025) Working Paper 140 · CC BY 4.0 (출처 표시) |
| `dl2/job_exposure.csv` | 미국 직업별 관측 노출도(실제 사용) | Anthropic 경제지수(2026.3) · CC BY |
| `frozen/usage_ms.json` | 미국 직업별 AI 적용도(Tomlinson 외 2025, Microsoft)를 한국 소분류·중분류로 집계한 값(교차 확인용) | 원자료 `ai_applicability_scores.csv`는 재배포 조건이 확인되지 않아 저장소에 넣지 않았다. 원자료를 `dl2/`에 두면 usage_agg.py가 그것으로 다시 계산한다 |
| `bak18/city_meta.json` | 옛 57개 직업판 지도 데이터. 업무 41개 이름표(RN)와 옛 직업 이름을 여기서 읽는다 | **고정본**(2026-10-18 16:07 백업). 가상 데이터 시연판(make18) 결과라 실제 자료에서 다시 만들 대상이 아니다. 이름표만 쓴다 |

나머지 중간 파일(`bak21/jobs_v3.json`, `ksco_titles` 옛판, `isco_occ.csv`, `usage_agg.json`, `ksco_soc_map.json` 기본판)은 모두 run.sh가 위 자료에서 다시 만든다.
