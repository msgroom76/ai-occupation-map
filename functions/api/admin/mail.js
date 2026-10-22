// 운영 화면(/admin)용 API. 로그인 쿠키(메일 로그인 링크) 또는 'Authorization: Bearer <STATS_KEY>'가 있어야 열린다.
// GET                      → 구독자 현황, 최근 30일 신규·확인·해지, 호별 발송 현황, 최근 구독자(주소 일부 가림), 자동 발송 설정 상태
// GET ?week=…&view=html    → 그 호 미리보기
// POST {mode:'test', week, to}          → 한 주소에 시험 발송([시험])
// POST {mode:'approve', week}           → 승인하고 발송 시작(승인 요청 메일의 버튼과 같음)
// POST {mode:'ask', week}               → 승인 요청 메일 다시 보내기
// POST {mode:'confirm-pending'}         → 확인 전 신청자에게 확인 메일(한 사람에 한 번)
import { db, json, kst, token } from '../../_db.js';
import { mailOn, confirmMail } from '../../_mail.js';
import { WEEK, issues, draft, personal, issueMail, batch, issueState, setMeta, sendNext, askApproval, adminTo } from '../../_issue.js';
import { authed } from '../../_admin.js';
const mask = e => { const [a, b] = String(e).split('@'); return (a.length <= 2 ? a[0] + '*' : a.slice(0, 2) + '*'.repeat(Math.min(6, a.length - 2))) + '@' + b; };

export async function onRequestGet({ request, env }) {
  if (!(await authed(request, env))) return json({ ok: false }, 403);
  const u = new URL(request.url), origin = u.origin, week = u.searchParams.get('week') || '';
  if (WEEK.test(week) && u.searchParams.get('view') === 'html') {
    const m = await draft(env, origin, week); if (!m) return new Response('원고가 없어요', { status: 404 });
    return new Response(personal(m.htmlBody, '#'), { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' } });
  }
  const d = await db(env); if (!d) return json({ ok: false, msg: 'DB 연결 전' }, 503);
  const st = Object.fromEntries((await d.prepare("SELECT COALESCE(status,'pending') AS s, COUNT(*) AS n FROM subscribers GROUP BY 1").all()).results.map(r => [r.s, r.n]));
  const daily = (await d.prepare(`SELECT day, SUM(newn) AS signup, SUM(conf) AS confirmed, SUM(un) AS unsub FROM (
      SELECT substr(COALESCE(consent_at, created),1,10) AS day, 1 AS newn, 0 AS conf, 0 AS un FROM subscribers
      UNION ALL SELECT substr(confirmed_at,1,10), 0, 1, 0 FROM subscribers WHERE confirmed_at IS NOT NULL
      UNION ALL SELECT substr(COALESCE(unsub_at, unsubscribed),1,10), 0, 0, 1 FROM subscribers WHERE status = 'unsub')
    WHERE day >= date('now','+9 hours','-30 day') GROUP BY day ORDER BY day DESC`).all()).results;
  const list = await issues(env, origin);
  const sends = Object.fromEntries((await d.prepare("SELECT week, SUM(status='sent') AS sent, SUM(status='failed') AS failed, MAX(at) AS last FROM sends GROUP BY week").all()).results.map(r => [r.week, r]));
  const iss = [];
  for (const it of list.slice(0, 8)) iss.push({ week: it.week, date: it.date, subject: it.subject, state: await issueState(d, it.week) || 'new', sent: sends[it.week]?.sent || 0, failed: sends[it.week]?.failed || 0, last: sends[it.week]?.last || null });
  const recent = (await d.prepare("SELECT email, status, COALESCE(consent_at, created) AS at, confirmed_at, job FROM subscribers ORDER BY COALESCE(consent_at, created) DESC LIMIT 20").all()).results.map(r => ({ ...r, email: mask(r.email) }));
  return json({ ok: true, mailOn: mailOn(env), adminTo: adminTo(env) ? mask(adminTo(env)) : '', counts: { active: st.active || 0, pending: st.pending || 0, unsub: st.unsub || 0 }, confirmMails: sends.confirm || { sent: 0, failed: 0 }, daily, issues: iss, recent });
}

export async function onRequestPost({ request, env }) {
  if (!(await authed(request, env))) return json({ ok: false }, 403);
  let b = {}; try { b = await request.json(); } catch (e) { return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 400); }
  if (!mailOn(env)) return json({ ok: false, msg: '메일 발송이 꺼져 있어요(MAIL_ENABLED·RESEND_API_KEY·MAIL_FROM).' }, 409);
  const origin = new URL(request.url).origin, d = await db(env); if (!d) return json({ ok: false, msg: 'DB 연결 전' }, 503);
  const week = String(b.week || '');
  if (b.mode === 'confirm-pending') {
    const rows = (await d.prepare("SELECT email, token FROM subscribers WHERE status = 'pending' AND NOT EXISTS (SELECT 1 FROM sends x WHERE x.week = 'confirm' AND x.email = subscribers.email AND x.status = 'sent') LIMIT 50").all()).results;
    if (!rows.length) return json({ ok: true, msg: '확인 메일을 보낼 신청자가 없어요.' });
    for (const x of rows) if (!x.token) { x.token = token(); await d.prepare("UPDATE subscribers SET token = ?2 WHERE email = ?1").bind(x.email, x.token).run(); }
    const r = await batch(env, rows.map(x => ({ from: env.MAIL_FROM, ...(env.MAIL_REPLY_TO ? { reply_to: env.MAIL_REPLY_TO } : {}), to: [x.email], ...confirmMail(origin, x.token) })));
    const now = kst();
    await d.batch(rows.map((x, i) => d.prepare("INSERT INTO sends (week, email, status, at, id, err) VALUES ('confirm', ?1, ?2, ?3, ?4, ?5) ON CONFLICT(week, email) DO UPDATE SET status = excluded.status, at = excluded.at, id = excluded.id, err = excluded.err").bind(x.email, r.ok ? 'sent' : 'failed', now, r.ids[i] || null, r.err)));
    return json({ ok: r.ok, msg: r.ok ? `확인 메일 ${rows.length}통을 보냈어요.` : `보내지 못했어요 (${r.status})` }, r.ok ? 200 : 502);
  }
  if (!WEEK.test(week)) return json({ ok: false, msg: '호를 고르세요.' }, 400);
  const it = (await issues(env, origin)).find(i => i.week === week); if (!it) return json({ ok: false, msg: '그 호의 원고가 없어요.' }, 404);
  if (b.mode === 'test') {
    const to = String(b.to || '').trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(to)) return json({ ok: false, msg: '받을 주소를 입력하세요.' }, 400);
    const m = await draft(env, origin, week);
    const r = await batch(env, [issueMail(env, origin, m, to, null, '[시험] ')]);
    return json({ ok: r.ok, msg: r.ok ? `${to}로 시험 메일을 보냈어요.` : `보내지 못했어요 (${r.status}) ${r.err || ''}` }, r.ok ? 200 : 502);
  }
  if (b.mode === 'ask') {
    const ok = await askApproval(env, d, origin, it); if (ok && !(await issueState(d, week))) await setMeta(d, 'issue:' + week, 'asked');
    return json({ ok, msg: ok ? '승인 요청 메일을 다시 보냈어요.' : '보내지 못했어요(받을 주소 MAIL_REPLY_TO 또는 ADMIN_EMAIL 확인).' }, ok ? 200 : 502);
  }
  if (b.mode === 'approve') {
    const st = await issueState(d, week);
    if (st !== 'approved' && st !== 'done') { await setMeta(d, 'issue:' + week, 'approved'); await setMeta(d, 'issue_approved_at:' + week, kst()); }
    let sent = 0, r = { ok: true, remaining: 0 };
    for (let i = 0; i < 2; i++) { r = await sendNext(env, d, origin, week, 50); sent += r.sent || 0; if (!r.ok || !r.remaining) break; }
    const msg = !r.ok ? (r.status === 429 ? `${sent}명에게 보냈고, 오늘 한도(하루 100통)에 걸려 멈췄어요. 내일 자동으로 이어서 보내요.` : `${sent}명에게 보냈고 일부 실패했어요(${r.status}). 사이트 방문 때 다시 시도해요.`)
      : r.remaining ? `${sent}명에게 보냈어요. 남은 ${r.remaining}명은 사이트 방문 때 50명씩 자동으로 이어서 보내요.` : `${sent}명에게 보냈어요. 이 호는 모두 보냈어요.`;
    return json({ ok: r.ok, msg });
  }
  return json({ ok: false, msg: '알 수 없는 요청이에요.' }, 400);
}
