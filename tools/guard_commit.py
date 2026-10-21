"""정기 작업이 push하기 직전에 돌리는 안전장치: 바꾼 파일이 그 작업이 바꿔도 되는 파일인지 확인한다.
사용: python3 tools/guard_commit.py news     (소식 갱신 작업: feed.json만)
      python3 tools/guard_commit.py weekly   (주간 작업: feed.json, index.json, w/, j/, og/, mail/, sitemap.xml, robots.txt)
origin/main과 비교해 아직 push하지 않은 커밋 + 작업 중인 변경을 모두 본다. 허용 밖 파일이 있으면 종료 코드 1 → push하지 말고 보고한다.
(외부 기사를 읽는 작업이 기사 속 지시에 넘어가 코드·화면을 고치는 일을 막기 위한 것)"""
import subprocess, sys

ALLOW = {
    'news': lambda f: f == 'feed.json',
    'weekly': lambda f: f in ('feed.json', 'index.json', 'sitemap.xml', 'robots.txt') or f.split('/')[0] in ('w', 'j', 'og', 'mail'),
}
role = sys.argv[1] if len(sys.argv) > 1 else ''
if role not in ALLOW: sys.exit(__doc__)
run = lambda *a: subprocess.run(a, capture_output=True, text=True).stdout.split()
subprocess.run(['git', 'fetch', '-q', 'origin', 'main'])
files = set(run('git', 'diff', '--name-only', 'origin/main')) | set(run('git', 'ls-files', '--others', '--exclude-standard'))
bad = sorted(f for f in files if not ALLOW[role](f))
print(f'바꾼 파일 {len(files)}개: ' + ', '.join(sorted(files)[:20]) + (' …' if len(files) > 20 else ''))
if bad:
    print('ERROR 이 작업이 바꾸면 안 되는 파일: ' + ', '.join(bad)); sys.exit(1)
print('통과')
