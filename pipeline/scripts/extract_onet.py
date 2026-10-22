# O*NET 원본(약 100MB)에서 파이프라인이 실제로 쓰는 부분만 뽑아 dl_onet/db_text/에 넣는다. run.sh는 이 스크립트를 부르지 않는다.
# 사용: python3 extract_onet.py <원본 db_XX_X_text 폴더> <pipeline/inputs/dl_onet/db_text>
# 원본: https://www.onetcenter.org/database.html 의 텍스트 묶음(db_XX_X_text.zip, CC BY 4.0). 지금 쓰는 판은 db_text/Read Me.txt 첫 줄.
# - Work Activities.txt, Task Ratings.txt: 중요도(Scale ID = IM) 줄과 쓰는 열만 남긴다.
# - Task Statements, Occupation Data, Read Me: 그대로 복사.
# - 세부 업무(DWA): 30.0까지는 'DWA Reference.txt'와 'Tasks to DWAs.txt'(DWA ID 예: 4.A.2.a.4.I09.D03),
#   31.0부터는 'GWAs to IWAs to DWAs.txt'와 'Tasks to DWAs.txt'(DWA Element ID 예: 4.A.2.a.4.i.3)로 바뀌었다.
#   소식(feed.json)의 dwa와 tasks.json이 옛 ID를 쓰므로, 같은 DWA 이름으로 옛 ID에 맞춰(dwa_ids_30.tsv) 30.0 형식으로 써 둔다.
#   업무 묶음(GWA, Element ID)은 새 판 값을 쓴다(31.0에서 117개가 다른 업무로 옮겨졌다).
import csv, os, shutil, sys
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
def rows(fn): return list(csv.DictReader(open(os.path.join(src, fn)), delimiter='\t'))
KEEP = {'Work Activities.txt': ['O*NET-SOC Code', 'Element ID', 'Element Name', 'Scale ID', 'Data Value'],
        'Task Ratings.txt': ['O*NET-SOC Code', 'Task ID', 'Scale ID', 'Data Value']}
for fn, cols in KEEP.items():
    with open(os.path.join(dst, fn), 'w') as g:
        g.write('\t'.join(cols) + '\n')
        for r in rows(fn):
            if r['Scale ID'] == 'IM': g.write('\t'.join(r[c] for c in cols) + '\n')
for fn in ['Task Statements.txt', 'Occupation Data.txt', 'Read Me.txt']:
    shutil.copy(os.path.join(src, fn), os.path.join(dst, fn))
if os.path.exists(os.path.join(src, 'DWA Reference.txt')):          # 30.0 이하
    for fn in ['DWA Reference.txt', 'Tasks to DWAs.txt']: shutil.copy(os.path.join(src, fn), os.path.join(dst, fn))
else:                                                                # 31.0 이상
    here = os.path.dirname(os.path.abspath(dst.rstrip('/')))
    OLD = {r['DWA Title']: r for r in csv.DictReader(open(os.path.join(here, 'dwa_ids_30.tsv')), delimiter='\t')}
    new2old, extra = {}, 0
    with open(os.path.join(dst, 'DWA Reference.txt'), 'w') as g:
        g.write('Element ID\tIWA ID\tDWA ID\tDWA Title\n')
        for r in rows('GWAs to IWAs to DWAs.txt'):
            o = OLD.get(r['DWA Element Name'])
            if not o: extra += 1
            iwa, did = (o['IWA ID'], o['DWA ID']) if o else (r['IWA Element ID'], r['DWA Element ID'])
            new2old[r['DWA Element ID']] = did
            g.write(f"{r['GWA Element ID']}\t{iwa}\t{did}\t{r['DWA Element Name']}\n")
    with open(os.path.join(dst, 'Tasks to DWAs.txt'), 'w') as g:
        g.write('O*NET-SOC Code\tTask ID\tDWA ID\tDate\tDomain Source\n')
        for r in rows('Tasks to DWAs.txt'):
            g.write(f"{r['O*NET-SOC Code']}\t{r['Task ID']}\t{new2old[r['DWA Element ID']]}\t{r['Date']}\t{r['Domain Source']}\n")
    print('새 DWA(옛 ID 없음):', extra)
print('ok', dst)
