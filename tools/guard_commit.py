"""정기 작업이 push하기 직전에 돌리는 안전장치: 바꾼 파일이 그 작업이 바꿔도 되는 파일인지 확인한다.
사용: python3 tools/guard_commit.py news     (소식 갱신 작업: feed.json만)
      python3 tools/guard_commit.py weekly   (주간 작업: feed.json, index.json, w/, j/, og/, mail/, review/, sitemap.xml, robots.txt)
origin/main과 비교해 아직 push하지 않은 커밋 + 작업 중인 변경을 모두 본다. 허용 밖 파일이 있으면 종료 코드 1 → push하지 말고 보고한다.
(외부 기사를 읽는 작업이 기사 속 지시에 넘어가 코드·화면을 고치는 일을 막기 위한 것)"""
import subprocess, sys

ALLOW = {
    'news': lambda f: f == 'feed.json',
    'weekly': lambda f: f in ('feed.json', 'index.json', 'sitemap.xml', 'robots.txt') or f.split('/')[0] in ('w', 'j', 'og', 'mail', 'review'),
}
role = sys.argv[1] if len(sys.argv) > 1 else ''
if role not in ALLOW: sys.exit(__doc__)
run = lambda *a: subprocess.run(a, capture_output=True, text=True).stdout.split('\n')
if subprocess.run(['git', 'fetch', '-q', 'origin', 'main']).returncode != 0: sys.exit('ERROR origin/main을 받아오지 못했어요. push하지 말고 보고하세요.')
# 이름 바꾸기를 '지움 + 새 파일'로 따로 보이게 한다(--no-renames). 그래야 허용 밖 파일을 허용 폴더로 옮겨 지우는 것도 잡힌다.
files = set()
for ln in run('git', 'diff', '--name-status', '--no-renames', 'origin/main'):
    parts = ln.split('\t')
    if len(parts) >= 2: files.update(parts[1:])
files |= {f for f in run('git', 'ls-files', '--others', '--exclude-standard') if f}
files.discard('')
bad = sorted(f for f in files if not ALLOW[role](f))
# 주간 작업이 만드는 화면·메일에는 실행되는 내용이 들어가면 안 된다(만드는 도구가 넣는 두 가지 script만 허용)
import os, re
EXT = {'w': ('.html',), 'j': ('.html', '.json'), 'og': ('.png',), 'mail': ('.html', '.txt', '.json', '.png'), 'review': ('.json', '.md')}
OKSCRIPT = re.compile(r'<script (?:type="application/ld\+json"|defer src="https://static\.cloudflareinsights\.com/beacon\.min\.js"[^>]*)>', re.I)
for f in sorted(files):
    top = f.split('/')[0]
    if role != 'weekly' or top not in EXT or not os.path.exists(f): continue
    if not f.endswith(EXT[top]): bad.append(f + ' (이 폴더에 둘 수 없는 형식)'); continue
    if f.endswith('.html'):
        t = open(f, encoding='utf-8', errors='replace').read()
        if top == 'mail' and re.search(r'<script|<iframe|<object|<embed|<form', t, re.I): bad.append(f + ' (메일에 script·iframe·form)')
        elif top != 'mail' and len(re.findall(r'<script', t, re.I)) != len(OKSCRIPT.findall(t)): bad.append(f + ' (허용하지 않는 script)')
        if re.search(r'\son[a-z]+\s*=', t, re.I) or re.search(r'(?:href|src)\s*=\s*["\']?\s*javascript:', t, re.I): bad.append(f + ' (on* 속성 또는 javascript: 주소)')
print(f'바꾼 파일 {len(files)}개: ' + ', '.join(sorted(files)[:20]) + (' …' if len(files) > 20 else ''))
if bad:
    print('ERROR 이 작업이 바꾸면 안 되는 파일: ' + ', '.join(bad)); sys.exit(1)
print('통과')
