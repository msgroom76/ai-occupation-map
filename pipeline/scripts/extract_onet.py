# O*NET 30.0 원본(db_30_0_text, 약 100MB)에서 파이프라인이 실제로 쓰는 부분만 뽑는다. run.sh는 이 스크립트를 부르지 않는다.
# 사용: python3 extract_onet.py <원본 db_30_0_text 폴더> <pipeline/inputs/dl_onet/db_30_0_text>
# 원본: https://www.onetcenter.org/dl_files/database/db_30_0_text.zip (CC BY 4.0)
# - Work Activities.txt, Task Ratings.txt: 중요도(Scale ID = IM) 줄과 쓰는 열만 남긴다(스크립트는 IM만 읽고, 업무 이름표도 IM 줄에 41개가 모두 있다).
# - DWA Reference, Tasks to DWAs, Task Statements, Occupation Data, Read Me: 그대로 복사.
import csv, os, shutil, sys
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
KEEP = {'Work Activities.txt': ['O*NET-SOC Code', 'Element ID', 'Element Name', 'Scale ID', 'Data Value'],
        'Task Ratings.txt': ['O*NET-SOC Code', 'Task ID', 'Scale ID', 'Data Value']}
for fn, cols in KEEP.items():
    with open(os.path.join(src, fn)) as f, open(os.path.join(dst, fn), 'w') as g:
        g.write('\t'.join(cols) + '\n')
        for r in csv.DictReader(f, delimiter='\t'):
            if r['Scale ID'] == 'IM': g.write('\t'.join(r[c] for c in cols) + '\n')
for fn in ['DWA Reference.txt', 'Tasks to DWAs.txt', 'Task Statements.txt', 'Occupation Data.txt', 'Read Me.txt']:
    shutil.copy(os.path.join(src, fn), os.path.join(dst, fn))
print('ok', dst)
