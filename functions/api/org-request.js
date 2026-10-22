// 조직 자가 진단(/org)의 '진단 보고서 요청'. 연락처는 늘 저장하고, 직무·인원(config)은 담당자가 함께 보내기로 동의했을 때만 저장한다.
// 저장: org_requests(보고서 작업용 원본) + leads(기존 문의 목록·메일 알림과 같은 흐름). 둘 다 접수 1년 뒤 지운다.
// 악용 방지: 같은 출처만, 숨은 입력란(봇), 이메일 형식, 입력값 검사(직무 40개·한 직무 10만 명 이하·직업 코드 형식), 같은 주소 하루 3건.
import { db, json, kst, clip, isEmail, sameOrigin } from '../_db.js';
import { mailOn } from '../_mail.js';
import { adminTo, batch } from '../_issue.js';
import { leadMails, bump } from './contact.js';
const SCOPES = ['진단 보고서', '진단 보고서 + 임직원 워크숍'];
export function cleanConfig(c) {
  if (!c || typeof c !== 'object' || !Array.isArray(c.roles)) return null;
  const roles = c.roles.slice(0, 40).map(r => ({ name: clip(r && r.name, 40), code: String(r && r.code || ''), n: Math.round(+(r && r.n) || 0), group: r && r.group ? 1 : 0 }))
    .filter(r => /^\d{2,3}$/.test(r.code) && r.n > 0 && r.n <= 100000);
  if (!roles.length) return null;
  const num = v => (v == null || v === '' || !isFinite(+v)) ? null : Math.round(+v * 100) / 100;
  return { asof: /^\d{4}-\d{2}-\d{2}$/.test(c.asof) ? c.asof : kst().slice(0, 10), industry: /^[A-U]$/.test(c.industry || '') ? c.industry : null,
    groups: Array.isArray(c.groups) ? c.groups.slice(0, 2).map(g => clip(g, 12)) : null, payroll: num(c.payroll), opProfit: num(c.opProfit), roles };
}
export async function onRequestPost({ request, env, waitUntil }) {
  if (!sameOrigin(request)) return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 403);
  let b = {}; try { b = await request.json(); } catch (e) { return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 400); }
  if (b.website) return json({ ok: true });
  const email = clip(b.email, 254).toLowerCase();
  if (!isEmail(email)) return json({ ok: false, msg: '이메일 주소를 확인해 주세요.' }, 400);
  if (!b.consent) return json({ ok: false, msg: '개인정보 수집·이용에 동의해 주세요.' }, 400);
  const org = clip(b.org, 100); if (org.length < 2) return json({ ok: false, msg: '회사·기관명을 적어 주세요.' }, 400);
  const d = await db(env); if (!d) return json({ ok: false, msg: '접수 준비 중이에요. 잠시 후 다시 시도해 주세요.' }, 503);
  const at = kst();
  const recent = (await d.prepare("SELECT COUNT(*) AS n FROM org_requests WHERE email = ?1 AND created >= ?2").bind(email, new Date(Date.now() + 9 * 3600e3 - 864e5).toISOString()).first()).n;
  if (recent >= 3) return json({ ok: false, msg: '오늘은 이미 요청을 받았어요. 메일로 연락드릴게요.' }, 429);
  const cfg = b.share ? cleanConfig(b.config) : null;
  const scope = SCOPES.includes(b.scope) ? b.scope : SCOPES[0], name = clip(b.name, 60), msg = String(b.msg || '').slice(0, 1000).trim();
  const r = await d.prepare("INSERT INTO org_requests (created, name, org, email, scope, msg, config, status) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 'new')")
    .bind(at, name, org, email, scope, msg, cfg ? JSON.stringify(cfg) : null).run();
  const id = r.meta && r.meta.last_row_id;
  const sum = cfg ? `직무 ${cfg.roles.length}개 · ${cfg.roles.reduce((s, x) => s + x.n, 0).toLocaleString()}명${cfg.industry ? ' · 업종 ' + cfg.industry : ''}${cfg.payroll ? ' · 급여 총액 ' + cfg.payroll + '억' : ''}` : '직무·인원 미제공';
  const L = { name, org, email, kind: '조직 리포트', msg: `[자가 진단 요청 #${id}] ${scope}\n${sum}\n\n${msg}`.trim(), at };
  await d.prepare("INSERT INTO leads (name, org, email, kind, msg, created) VALUES (?1, ?2, ?3, ?4, ?5, ?6)").bind(L.name, L.org, email, L.kind, L.msg, at).run();
  waitUntil((async () => {
    if (!mailOn(env)) return;
    const today = at.slice(0, 10), M = leadMails(env, new URL(request.url).origin, L), out = [];
    if (adminTo(env) && await bump(d, 'lead_alert_day', 30, today)) out.push(M.alert);
    if (recent === 0 && await bump(d, 'lead_receipt_day', 20, today)) out.push(M.receipt);
    if (out.length) await batch(env, out);
  })().catch(e => console.error(JSON.stringify({ at: 'org-mail', err: String(e) }))));
  return json({ ok: true, msg: '요청을 받았어요. 영업일 기준 2일 안에 이메일로 연락드릴게요.' });
}
