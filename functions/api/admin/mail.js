// 주간 메일 발송(운영자 전용). /admin 화면이 부른다. 'Authorization: Bearer <STATS_KEY>'가 있어야 열린다.
// 원고는 build_mail.py가 만든 mail/<주>.json·.html·.txt(사이트에는 공개되지 않음)를 읽는다.
// GET  ?week=2026-W44            → 원고 제목, 구독자 수(확인 완료), 이미 보낸 수
// GET  ?week=…&view=html         → 원고 HTML(미리보기용)
// POST {week, mode:'test', to}   → 한 주소에만 시험 발송(제목 앞에 [시험])
// POST {week, mode:'send', confirm:'<주>', limit} → 확인한 구독자 중 이번 주에 아직 안 보낸 사람에게 최대 limit명(기본 50) 발송.
//      남은 사람이 있으면 remaining으로 알려준다. 같은 주에 같은 사람에게 두 번 보내지 않는다(sends 표).
// POST {mode:'confirm-pending', limit} → 아직 확인 전(pending)인 신청자에게 구독 확인 메일을 보낸다(이전에 받아 둔 신청 포함, 한 사람에 한 번).
// 메일은 MAIL_ENABLED=1, RESEND_API_KEY, MAIL_FROM이 모두 있을 때만 나간다.
import { db, json, kst, safeEq, token } from '../../_db.js';
import { mailOn, confirmMail } from '../../_mail.js';
const WEEK = /^\d{4}-W\d{2}$/;
const authed = (request, env) => !!env.STATS_KEY && safeEq((request.headers.get('authorization') || '').replace(/^Bearer\s+/i, ''), env.STATS_KEY);

async function draft(env, request, week) {
  const get = async ext => {
    const r = await env.ASSETS.fetch(new URL(`/mail/${week}.${ext}`, new URL(request.url).origin));
    return r.ok ? r.text() : null;
  };
  const meta = await get('json'); if (!meta) return null;
  let m; try { m = JSON.parse(meta); } catch (e) { return null; }
  return { ...m, htmlBody: await get('html'), textBody: await get('txt') };
}
const personal = (s, url) => (s || '').split('{{unsubscribe_url}}').join(url);

export async function onRequestGet({ request, env }) {
  if (!authed(request, env)) return json({ ok: false }, 403);
  const u = new URL(request.url), week = u.searchParams.get('week') || '';
  const d = await db(env); if (!d) return json({ ok: false, msg: 'DB 연결 전' }, 503);
  if (!WEEK.test(week)) {
    const r = await env.ASSETS.fetch(new URL('/mail/index.json', u.origin));
    const idx = r.ok ? await r.json() : { issues: [] };
    return json({ ok: true, issues: idx.issues.map(i => ({ week: i.week, subject: i.subject, date: i.date })), mailOn: mailOn(env) });
  }
  const m = await draft(env, request, week); if (!m) return json({ ok: false, msg: '그 주의 원고가 없어요.' }, 404);
  if (u.searchParams.get('view') === 'html') return new Response(personal(m.htmlBody, '#수신거부-링크-자리'), { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' } });
  const act = await d.prepare("SELECT COUNT(*) AS n FROM subscribers WHERE status = 'active'").first();
  const pend = await d.prepare("SELECT COUNT(*) AS n FROM subscribers WHERE status = 'pending'").first();
  const sent = await d.prepare("SELECT status, COUNT(*) AS n FROM sends WHERE week = ?1 GROUP BY status").bind(week).all();
  return json({ ok: true, week, subject: m.subject, preheader: m.preheader, active: act.n, pending: pend.n, sends: Object.fromEntries(sent.results.map(r => [r.status, r.n])), mailOn: mailOn(env) });
}

export async function onRequestPost({ request, env }) {
  if (!authed(request, env)) return json({ ok: false }, 403);
  if (!mailOn(env)) return json({ ok: false, msg: '메일 발송이 꺼져 있어요(MAIL_ENABLED·RESEND_API_KEY·MAIL_FROM).' }, 409);
  let b = {}; try { b = await request.json(); } catch (e) { return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 400); }
  const week = String(b.week || ''); if (b.mode !== 'confirm-pending' && !WEEK.test(week)) return json({ ok: false, msg: '주를 고르세요.' }, 400);
  const m = b.mode === 'confirm-pending' ? {} : await draft(env, request, week); if (b.mode !== 'confirm-pending' && (!m || !m.htmlBody)) return json({ ok: false, msg: '그 주의 원고가 없어요.' }, 404);
  const base = new URL(request.url).origin;
  const one = (to, tok, test) => {
    const unsub = tok ? `${base}/api/unsub?t=${tok}` : `${base}/`;
    return {
      from: env.MAIL_FROM, ...(env.MAIL_REPLY_TO ? { reply_to: env.MAIL_REPLY_TO } : {}), to: [to], subject: (test ? '[시험] ' : '') + m.subject,
      html: personal(m.htmlBody, unsub), text: personal(m.textBody, unsub),
      headers: tok ? { 'List-Unsubscribe': `<${unsub}>`, 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click' } : {}
    };
  };
  const call = async list => {
    const r = await fetch('https://api.resend.com/emails/batch', { method: 'POST', headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, 'content-type': 'application/json' }, body: JSON.stringify(list) });
    const t = await r.text(); let j = {}; try { j = JSON.parse(t); } catch (e) { }
    return { ok: r.ok, status: r.status, ids: (j.data || []).map(x => x.id), err: r.ok ? null : t.slice(0, 300) };
  };

  if (b.mode === 'test') {
    const to = String(b.to || '').trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(to)) return json({ ok: false, msg: '받을 주소를 확인하세요.' }, 400);
    const r = await call([one(to, null, true)]);
    return json({ ok: r.ok, msg: r.ok ? `${to}로 시험 메일을 보냈어요.` : `보내지 못했어요 (${r.status}) ${r.err || ''}` }, r.ok ? 200 : 502);
  }
  if (b.mode === 'confirm-pending') {
    const d = await db(env); if (!d) return json({ ok: false, msg: 'DB 연결 전' }, 503);
    const rows = (await d.prepare("SELECT email, token FROM subscribers WHERE status = 'pending' AND NOT EXISTS (SELECT 1 FROM sends x WHERE x.week = 'confirm' AND x.email = subscribers.email AND x.status = 'sent') LIMIT ?1").bind(Math.max(1, Math.min(100, +b.limit || 50))).all()).results;
    if (!rows.length) return json({ ok: true, sent: 0, remaining: 0, msg: '확인 메일을 보낼 신청자가 없어요.' });
    for (const x of rows) if (!x.token) { x.token = token(); await d.prepare("UPDATE subscribers SET token = ?2 WHERE email = ?1").bind(x.email, x.token).run(); }
    const r = await call(rows.map(x => ({ from: env.MAIL_FROM, ...(env.MAIL_REPLY_TO ? { reply_to: env.MAIL_REPLY_TO } : {}), to: [x.email], ...confirmMail(base, x.token) })));
    const now = kst();
    await d.batch(rows.map((x, i) => d.prepare("INSERT INTO sends (week, email, status, at, id, err) VALUES ('confirm', ?1, ?2, ?3, ?4, ?5) ON CONFLICT(week, email) DO UPDATE SET status = excluded.status, at = excluded.at, id = excluded.id, err = excluded.err").bind(x.email, r.ok ? 'sent' : 'failed', now, r.ids[i] || null, r.err)));
    return json({ ok: r.ok, sent: r.ok ? rows.length : 0, msg: r.ok ? `확인 메일 ${rows.length}통을 보냈어요.` : `보내지 못했어요 (${r.status}) ${r.err || ''}` }, r.ok ? 200 : 502);
  }
  if (b.mode !== 'send' || b.confirm !== week) return json({ ok: false, msg: '확인 문구로 주(예: 2026-W44)를 정확히 입력하세요.' }, 400);
  const d = await db(env); if (!d) return json({ ok: false, msg: 'DB 연결 전' }, 503);
  const limit = Math.max(1, Math.min(100, +b.limit || 50));
  const rows = (await d.prepare(`SELECT s.email, s.token FROM subscribers s WHERE s.status = 'active' AND s.token IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM sends x WHERE x.week = ?1 AND x.email = s.email AND x.status = 'sent') ORDER BY s.confirmed_at LIMIT ?2`).bind(week, limit).all()).results;
  if (!rows.length) return json({ ok: true, sent: 0, remaining: 0, msg: '이번 주 메일을 모두 보냈어요.' });
  const r = await call(rows.map(x => one(x.email, x.token, false)));
  const now = kst();
  await d.batch(rows.map((x, i) => d.prepare("INSERT INTO sends (week, email, status, at, id, err) VALUES (?1, ?2, ?3, ?4, ?5, ?6) ON CONFLICT(week, email) DO UPDATE SET status = excluded.status, at = excluded.at, id = excluded.id, err = excluded.err")
    .bind(week, x.email, r.ok ? 'sent' : 'failed', now, r.ids[i] || null, r.err)));
  const left = await d.prepare(`SELECT COUNT(*) AS n FROM subscribers s WHERE s.status = 'active' AND NOT EXISTS (SELECT 1 FROM sends x WHERE x.week = ?1 AND x.email = s.email AND x.status = 'sent')`).bind(week).first();
  if (!r.ok) return json({ ok: false, sent: 0, remaining: left.n, msg: r.status === 429 ? '오늘 보낼 수 있는 양을 넘었어요(Resend 무료: 하루 100통). 내일 이어서 보내세요.' : `보내지 못했어요 (${r.status}) ${r.err || ''}` }, 502);
  return json({ ok: true, sent: rows.length, remaining: left.n, msg: `${rows.length}명에게 보냈어요. 남은 사람 ${left.n}명.` });
}
