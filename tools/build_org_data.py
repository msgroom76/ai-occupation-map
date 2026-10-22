"""자가 진단(/org)용 공개 자료: org_bench.json(업종 직업 구성)을 reports/industry_bench.json에서 만든다.
저장소 루트에서: python3 tools/build_org_data.py  — 업종 평균 노출도는 브라우저가 이번 주 보정으로 다시 계산하므로 구성(mix)만 싣는다."""
import json, re
B = json.load(open('reports/industry_bench.json'))
NAME = {'A': '농업·임업·어업', 'B': '광업', 'C': '제조업', 'D': '전기·가스·증기', 'E': '수도·하수·폐기물', 'F': '건설업', 'G': '도소매업', 'H': '운수·창고업',
        'I': '숙박·음식점업', 'J': '정보통신업', 'K': '금융·보험업', 'L': '부동산업', 'M': '전문·과학·기술서비스업', 'N': '사업지원서비스업', 'O': '공공행정',
        'P': '교육서비스업', 'Q': '보건·사회복지업', 'R': '예술·스포츠·여가업', 'S': '협회·기타 개인서비스업', 'T': '가구 내 고용', 'U': '국제·외국기관'}
out = {'src': B['src'], 'period': B['period'], 'note': B['note'], 'industry': {}}
for k, v in B['industry'].items():
    m = re.match(r'([A-U])\.', k)
    if not m: continue
    c = m.group(1); out['industry'][c] = {'name': NAME[c], 'mix': {a: round(b, 4) for a, b in v['mix'].items() if b > 0}, 'e26_ref': v['e26']}
json.dump(out, open('org_bench.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('org_bench.json', len(out['industry']))
