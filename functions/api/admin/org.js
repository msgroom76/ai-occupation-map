// 운영 화면: 조직 자가 진단 보고서 요청.
// GET                  → 최근 요청 목록(설정 요약 포함)
// GET ?id=N&fmt=config → reports/<id>.json 형식의 설정 파일(tools/build_report.py에 바로 넣는 형식)
// POST {id, status}    → 상태 바꾸기(new 접수 · doing 진행 · sent 전달 · hold 보류)
import { db, json, kst } from '../../_db.js';
import { authed } from '../../_admin.js';
const STATUS = ['new', 'doing', 'sent', 'hold'];
// 소분류·중분류 코드 → 직무 군상 그림의 기본 인물(운영자가 바꿀 수 있음)
const FIG3 = { '224': 'data', '235': 'engineer', '283': 'marketer', '284': 'sales', '291': 'writer', '293': 'video', '295': 'designer', '298': 'event', '331': 'accountant', '321': 'scm', '362': 'cs', '521': 'store', '740': 'welder', '851': 'machinist', '855': 'assembler', '811': 'foodworker', '930': 'foodworker', '872': 'driver', '873': 'logistics', '921': 'logistics' };
const FIG2 = { '21': 'researcher', '22': 'developer', '23': 'engineer', '24': 'researcher', '25': 'researcher', '27': 'admin', '28': 'marketer', '29': 'designer', '31': 'admin', '32': 'scm', '33': 'accountant', '34': 'accountant', '35': 'admin', '36': 'cs', '37': 'admin', '39': 'cs', '74': 'welder', '75': 'technician', '81': 'foodworker', '84': 'machinist', '85': 'assembler', '87': 'driver', '92': 'logistics' };
const FIG1 = { '1': 'exec', '2': 'researcher', '3': 'admin', '4': 'cs', '5': 'sales', '6': 'technician', '7': 'technician', '8': 'machinist', '9': 'logistics' };
const fig = c => FIG3[c] || FIG2[c.slice(0, 2)] || FIG1[c[0]] || 'admin';
export function toReport(row) {
  const c = JSON.parse(row.config || 'null'); if (!c) return null;
  const id = `org${row.id}`;
  const roles = c.roles.map((r, i) => { const rid = 'r' + (i + 1); return { id: rid, name: r.name || r.code, n: r.n, code: r.code, fig: fig(r.code) }; });
  const C = { id, name: row.org, asof: c.asof, headcount: roles.reduce((s, r) => s + r.n, 0), basis: `담당자 제공 인원표(${c.asof}, 자가 진단 요청 #${row.id})`,
    office: roles.filter((r, i) => !c.roles[i].group).map(r => r.id), groups: c.groups && c.groups[0] ? [c.groups[0], c.groups[1] || '현장'] : ['사무·기술', '현장'],
    readers: '경영진, 인사 책임자', roles };
  if (c.payroll) { C.payroll_actual = c.payroll; C.payroll_note = '담당자 입력 급여 총액'; }
  if (c.opProfit) C.op_profit = c.opProfit;
  if (c.industry) C._industry = c.industry;   // 동종사 파일(reports/<id>_peers.json)의 industry를 정할 때 참고
  return C;
}
export async function onRequestGet({ request, env }) {
  if (!(await authed(request, env))) return json({ ok: false }, 403);
  const d = await db(env); if (!d) return json({ ok: false, msg: 'DB 연결 전' }, 503);
  const u = new URL(request.url), id = +u.searchParams.get('id');
  if (id && u.searchParams.get('fmt') === 'config') {
    const row = await d.prepare("SELECT * FROM org_requests WHERE id = ?1").bind(id).first();
    const C = row && toReport(row); if (!C) return json({ ok: false, msg: '함께 보낸 직무·인원이 없어요.' }, 404);
    return new Response(JSON.stringify(C, null, 1), { headers: { 'content-type': 'application/json; charset=utf-8', 'content-disposition': `attachment; filename="org${id}.json"`, 'cache-control': 'no-store' } });
  }
  const rows = (await d.prepare("SELECT id, created, name, org, email, scope, msg, config, status, updated FROM org_requests ORDER BY id DESC LIMIT 100").all()).results;
  return json({ ok: true, list: rows.map(r => { const c = JSON.parse(r.config || 'null'); return { ...r, config: undefined, roles: c ? c.roles.length : 0, n: c ? c.roles.reduce((s, x) => s + x.n, 0) : 0, industry: c && c.industry, payroll: c && c.payroll }; }) });
}
export async function onRequestPost({ request, env }) {
  if (!(await authed(request, env))) return json({ ok: false }, 403);
  const d = await db(env); if (!d) return json({ ok: false, msg: 'DB 연결 전' }, 503);
  let b = {}; try { b = await request.json(); } catch (e) {}
  if (!+b.id || !STATUS.includes(b.status)) return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 400);
  await d.prepare("UPDATE org_requests SET status = ?1, updated = ?2 WHERE id = ?3").bind(b.status, kst(), +b.id).run();
  return json({ ok: true, msg: '상태를 바꿨어요.' });
}
