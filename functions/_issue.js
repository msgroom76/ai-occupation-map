// 주간 메일 자동 흐름(2026-10-22)
// 1) 월요일 정기 작업이 mail/<주>.json·html·txt를 만들어 올린다(사이트에는 공개되지 않음).
// 2) 사이트에 첫 방문이 들어오면(tick) 새 호를 찾아 운영자에게 '승인 요청' 메일을 한 번 보낸다(본문 = 실제 메일 미리보기 + 승인 링크).
// 3) 운영자가 승인 화면에서 [승인하고 발송]을 누르면, 확인한 구독자에게 50명씩 보낸다. 남은 사람은 이후 방문 때(tick) 이어서,
//    하루 한도(Resend 429)에 걸리면 다음 날 이어서 보낸다. 같은 호를 같은 사람에게 두 번 보내지 않는다(sends 표).
// 4) 새 구독자가 확인 링크를 누르면 환영 메일과 이미 발송한(승인된) 가장 최근 호를 바로 보낸다.
// 상태는 meta 표에 issue:<주> = asked | approved | done, 하루 한도 멈춤은 issue_pause = 날짜.
import { kst, safeEq } from './_db.js';
import { mailOn } from './_mail.js';
export const WEEK = /^\d{4}-W\d{2}$/;
const reply = env => env.MAIL_REPLY_TO ? { reply_to: env.MAIL_REPLY_TO } : {};
export const adminTo = env => env.ADMIN_EMAIL || env.MAIL_REPLY_TO || '';

export async function sign(env, s) {
  const k = await crypto.subtle.importKey('raw', new TextEncoder().encode(env.STATS_KEY || ''), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const b = await crypto.subtle.sign('HMAC', k, new TextEncoder().encode(s));
  return [...new Uint8Array(b)].slice(0, 16).map(x => x.toString(16).padStart(2, '0')).join('');
}
export const verify = async (env, s, sig) => !!env.STATS_KEY && safeEq(await sign(env, s), sig || '');

export async function issues(env, origin) {
  const r = await env.ASSETS.fetch(new URL('/mail/index.json', origin));
  if (!r.ok) return [];
  const j = await r.json();
  return (j.issues || []).filter(i => WEEK.test(i.week)).sort((a, b) => a.week < b.week ? 1 : -1);
}
export async function draft(env, origin, week) {
  const get = async ext => { const r = await env.ASSETS.fetch(new URL(`/mail/${week}.${ext}`, origin)); return r.ok ? r.text() : null; };
  const meta = await get('json'); if (!meta) return null;
  let m; try { m = JSON.parse(meta); } catch (e) { return null; }
  const html = await get('html'); if (!html) return null;
  return { ...m, htmlBody: html, textBody: await get('txt') };
}
export const personal = (s, url) => (s || '').split('{{unsubscribe_url}}').join(url);
export function issueMail(env, origin, m, to, tok, prefix = '') {
  const unsub = tok ? `${origin}/api/unsub?t=${tok}` : `${origin}/`;
  return { from: env.MAIL_FROM, ...reply(env), to: [to], subject: prefix + m.subject, html: personal(m.htmlBody, unsub), text: personal(m.textBody, unsub),
    headers: tok ? { 'List-Unsubscribe': `<${unsub}>`, 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click' } : {} };
}
export async function batch(env, list) {
  const r = await fetch('https://api.resend.com/emails/batch', { method: 'POST', headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, 'content-type': 'application/json' }, body: JSON.stringify(list) });
  const t = await r.text(); let j = {}; try { j = JSON.parse(t); } catch (e) { }
  if (!r.ok) console.error(JSON.stringify({ at: 'batch', status: r.status, body: t.slice(0, 300) }));
  return { ok: r.ok, status: r.status, ids: (j.data || []).map(x => x.id), err: r.ok ? null : t.slice(0, 300) };
}
const getMeta = async (d, k) => (await d.prepare("SELECT v FROM meta WHERE k = ?1").bind(k).first())?.v || null;
export const setMeta = (d, k, v) => d.prepare("INSERT INTO meta (k, v) VALUES (?1, ?2) ON CONFLICT(k) DO UPDATE SET v = excluded.v").bind(k, v).run();
export const issueState = (d, wk) => getMeta(d, 'issue:' + wk);

// 확인한 구독자 중 이번 호를 아직 안 받은 사람에게 최대 limit명 발송
export async function sendNext(env, d, origin, week, limit = 50) {
  const m = await draft(env, origin, week); if (!m) return { ok: false, msg: '원고가 없어요.' };
  const rows = (await d.prepare(`SELECT email, token FROM subscribers s WHERE status = 'active' AND token IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM sends x WHERE x.week = ?1 AND x.email = s.email AND x.status = 'sent') ORDER BY confirmed_at LIMIT ?2`).bind(week, limit).all()).results;
  if (!rows.length) { await setMeta(d, 'issue:' + week, 'done'); return { ok: true, sent: 0, remaining: 0 }; }
  const r = await batch(env, rows.map(x => issueMail(env, origin, m, x.email, x.token)));
  const now = kst();
  await d.batch(rows.map((x, i) => d.prepare("INSERT INTO sends (week, email, status, at, id, err) VALUES (?1, ?2, ?3, ?4, ?5, ?6) ON CONFLICT(week, email) DO UPDATE SET status = excluded.status, at = excluded.at, id = excluded.id, err = excluded.err")
    .bind(week, x.email, r.ok ? 'sent' : 'failed', now, r.ids[i] || null, r.err)));
  if (!r.ok && r.status === 429) await setMeta(d, 'issue_pause', now.slice(0, 10));
  const left = (await d.prepare(`SELECT COUNT(*) AS n FROM subscribers s WHERE status = 'active' AND NOT EXISTS (SELECT 1 FROM sends x WHERE x.week = ?1 AND x.email = s.email AND x.status = 'sent')`).bind(week).first()).n;
  if (r.ok && !left) await setMeta(d, 'issue:' + week, 'done');
  return { ok: r.ok, status: r.status, sent: r.ok ? rows.length : 0, remaining: left, err: r.err };
}

// 승인 요청 메일: 실제 메일 위에 승인 안내 띠를 얹어서 보낸다
export async function askApproval(env, d, origin, it) {
  const to = adminTo(env); if (!to) return false;
  const m = await draft(env, origin, it.week); if (!m) return false;
  const n = (await d.prepare("SELECT COUNT(*) AS n FROM subscribers WHERE status = 'active'").first()).n;
  const link = `${origin}/api/approve?w=${it.week}&s=${await sign(env, 'approve|' + it.week)}`;
  const band = `<div style="font:15px/1.6 -apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;background:#1c1c1e;color:#fff;padding:18px 20px;margin:0 0 16px"><b>[승인 요청] ${it.week} 주간 메일</b><br>아래가 구독자 ${n}명에게 갈 메일이에요. 내용을 확인하고 승인하면 바로 발송을 시작해요.<br><a href="${link}" style="display:inline-block;margin-top:10px;padding:10px 16px;background:#ff8ccd;color:#1c1c1e;font-weight:700;text-decoration:none">승인 화면 열기</a></div>`;
  const body = /<body[^>]*>/i.test(m.htmlBody) ? m.htmlBody.replace(/<body([^>]*)>/i, `<body$1>${band}`) : band + m.htmlBody;
  const r = await batch(env, [{ from: env.MAIL_FROM, to: [to], subject: `[승인 요청] ${m.subject}`, html: personal(body, `${origin}/`), text: `[승인 요청] ${it.week} 주간 메일 · 구독자 ${n}명\n승인 화면: ${link}\n\n` + personal(m.textBody, `${origin}/`) }]);
  return r.ok;
}

// 사이트 방문 때 조용히 도는 작업(5분에 한 번, 실패해도 페이지에는 영향 없음)
export async function tick(env, d, origin) {
  if (!mailOn(env) || !d) return;
  if (globalThis.__tick && Date.now() - globalThis.__tick < 5 * 60e3) return;
  globalThis.__tick = Date.now();
  const list = await issues(env, origin); const it = list[0]; if (!it) return;
  if (Date.now() - Date.parse(it.date + 'T00:00:00+09:00') > 6 * 864e5) return;   // 일주일이 지난 호는 자동으로 다루지 않는다
  const st = await issueState(d, it.week);
  if (!st) { if (await askApproval(env, d, origin, it)) await setMeta(d, 'issue:' + it.week, 'asked'); return; }
  if (st === 'approved') {
    if (await getMeta(d, 'issue_pause') === kst().slice(0, 10)) return;           // 오늘 한도에 걸렸으면 내일
    await sendNext(env, d, origin, it.week, 50);
  }
}

// 새 구독자 환영: 환영 메일 + 이미 발송을 승인한 가장 최근 호
export async function welcome(env, d, origin, email, tok) {
  if (!mailOn(env)) return;
  const unsub = `${origin}/api/unsub?t=${tok}`;
  const list = []; let wk = null;
  for (const it of await issues(env, origin)) { const st = await issueState(d, it.week); if (st === 'approved' || st === 'done') { wk = it.week; break; } }
  const w = { from: env.MAIL_FROM, ...reply(env), to: [email], subject: '[AI 점령 지도] 구독을 시작했어요',
    text: `구독을 시작했어요. 매주 월요일 아침에 AI 점령 지도 주간 메일을 보내드려요.${wk ? '\n가장 최근 호를 바로 이어서 보내드릴게요.' : ''}\n\n내 직업 찾아보기: ${origin}/\n수신 거부: ${unsub}\n보내는 곳: 포스트오피스(AI 점령 지도 운영) · 개인정보처리방침 ${origin}/privacy`,
    html: `<div style="font:15px/1.7 -apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;color:#1c1c1e;max-width:520px"><p><b>AI 점령 지도</b> 구독을 시작했어요.</p><p>매주 월요일 아침, 한 주 동안 AI가 건드린 업무와 지수 변화를 정리해 보내드려요.${wk ? ' 가장 최근 호를 바로 이어서 보내드릴게요.' : ''}</p><p><a href="${origin}/" style="display:inline-block;padding:12px 18px;background:#1c1c1e;color:#fff;text-decoration:none;font-weight:600">내 직업 찾아보기</a></p><p style="color:#6b6b70;font-size:13px">보내는 곳: 포스트오피스(AI 점령 지도 운영) · <a href="${origin}/privacy" style="color:#6b6b70">개인정보처리방침</a> · <a href="${unsub}" style="color:#6b6b70">수신 거부</a></p></div>`,
    headers: { 'List-Unsubscribe': `<${unsub}>`, 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click' } };
  list.push(w);
  let m = null;
  if (wk) { const done = await d.prepare("SELECT 1 AS x FROM sends WHERE week = ?1 AND email = ?2 AND status = 'sent'").bind(wk, email).first(); if (!done) m = await draft(env, origin, wk); }
  if (m) list.push(issueMail(env, origin, m, email, tok));
  const r = await batch(env, list);
  if (r.ok && m) await d.prepare("INSERT INTO sends (week, email, status, at, id) VALUES (?1, ?2, 'sent', ?3, ?4) ON CONFLICT(week, email) DO UPDATE SET status = 'sent', at = excluded.at, id = excluded.id").bind(wk, email, kst(), r.ids[1] || null).run();
}
