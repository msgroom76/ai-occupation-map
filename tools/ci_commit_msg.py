"""GitHub Actions에서 Claude 실행 기록(execution_file)의 마지막 응답 첫 줄 'COMMIT: …'을 커밋 메시지로 꺼낸다. 없으면 기본 문구."""
import json, sys
path, default = sys.argv[1], sys.argv[2]
msg = default
try:
    data = json.load(open(path))
    texts = [m.get('result', '') for m in data if isinstance(m, dict) and m.get('type') == 'result']
    for line in (texts[-1] if texts else '').splitlines():
        if line.strip().startswith('COMMIT:'):
            msg = line.split('COMMIT:', 1)[1].strip()[:200] or default; break
except Exception:
    pass
print(msg)
