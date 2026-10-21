#!/usr/bin/env bash
# AI 점령 지도 데이터 파이프라인: inputs/의 원자료 → out/의 지도 데이터.
# 사용: bash pipeline/run.sh [출력 폴더, 기본 pipeline/out]   (KEEP=1 이면 작업 폴더를 지우지 않음)
# 저장소의 실제 파일(city_meta.json 등)은 건드리지 않는다. 결과를 확인한 뒤 손으로 복사한다.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$(mkdir -p "${1:-$HERE/out}" && cd "${1:-$HERE/out}" && pwd)"
W="$(mktemp -d)"
if [ "${KEEP:-0}" = "1" ]; then echo "작업 폴더: $W"; else trap 'rm -rf "$W"' EXIT; fi

# 작업 폴더는 처음 만든 곳(scratchpad)과 같은 배치: 스크립트와 자료가 한 폴더에 섞여 있다.
cp -r "$HERE/inputs/." "$W/"
cp -r "$HERE/scripts/." "$W/"
cd "$W"; mkdir -p web
export PYTHONHASHSEED=0 MPLBACKEND=Agg
LOG="$OUT/run.log"; : > "$LOG"
step() { echo "== $*" | tee -a "$LOG"; "$@" >> "$LOG" 2>&1; }

# 1. 직업명 사전: 고용24 직업코드 매핑(konet.csv) → 세분류별 직업명. 옛 57개 직업판 지도(bak18, 고정)를 기준으로 만든다.
cp bak18/city_meta.json web/city_meta.json
step python3 build_titles.py
cp web/ksco_titles.json bak18/ksco_titles.json

# 2. 중분류 56개 골격: KOSIS 지역별고용조사 취업자 수 + 직업명 사전 → samples/jobs_v3.json
step python3 build_v3.py
cp samples/jobs_v3.json samples/jobs_v3_synth.json

# 3. 업무 41개의 연도 곡선: O*NET 업무 ↔ Eloundou 외(2024) 업무 노출도 → dl_gpts_gwa.json → real_R.json
step python3 real_gwa.py
step python3 real_curves.py

# 4. 중분류별 업무 구성(미국 고용 가중) → real_profiles2.json, real_detail.json → bak21/jobs_v3.json, ksco_soc_map.json(기본판)
step python3 real_profiles2.py
step python3 apply_profiles.py

# 5. 소분류 163개: 미국 직업 연결 → real_small.json, ILO·실제 사용 평균 → real_small2.json → samples/jobs_v3.json 갱신
step python3 real_small.py
step python3 isco_occ.py
step python3 usage_agg.py
step python3 ksco_isco_official.py
step python3 real_blend.py
step python3 update_v3b.py

# 6. 지도 그리기와 마무리 → web/city_index.png, city_roads.png, city_meta.json, ksco_titles.json, ksco_soc_map.json
step python3 samples/make19.py
step python3 post19.py
step python3 post20.py
step python3 groups.py web/city_meta.json
step python3 post21.py

# 7. 직업별 세부 작업(O*NET DWA) → tasks.json ('이 발표가 닿는 내 업무')
step python3 build_tasks.py

cp web/city_meta.json web/city_index.png web/city_roads.png web/ksco_titles.json ksco_soc_map.json tasks.json "$OUT/"
mkdir -p "$OUT/intermediate"
cp real_R.json real_gwa_final.json real_detail.json real_profiles2.json real_small.json real_small2.json isco_occ.csv usage_agg.json dl_gpts_gwa.json samples/jobs_v3.json "$OUT/intermediate/"
echo "완료: $OUT" | tee -a "$LOG"
