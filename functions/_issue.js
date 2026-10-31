// 주간 메일 자동 흐름(2026-10-22)
// 1) 월요일 정기 작업이 mail/<주>.json·html·txt를 만들어 올린다(사이트에는 공개되지 않음).
// 2) 사이트에 첫 방문이 들어오면(tick) 새 호를 찾아 운영자에게 '승인 요청' 메일을 한 번 보낸다(본문 = 실제 메일 미리보기 + 승인 링크).
// 3) 운영자가 승인 화면에서 [승인하고 발송]을 누르면, 확인한 구독자에게 50명씩 보낸다. 남은 사람은 이후 방문 때(tick) 이어서,
//    하루 한도(Resend 429)에 걸리면 다음 날 이어서 보낸다. 같은 호를 같은 사람에게 두 번 보내지 않는다(sends 표).
// 4) 새 구독자가 확인 링크를 누르면 환영 메일과 이미 발송한(승인된) 가장 최근 호를 바로 보낸다.
// 상태는 meta 표에 issue:<주> = asked | approved | done, 하루 한도 멈춤은 issue_pause = 날짜.
import { sourceStatus } from './_sources.js';
import { kst, safeEq, webUrl } from './_db.js';
import { mailOn, confirmMail } from './_mail.js';
import { mailHtml, link, textFoot } from './_tpl.js';
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
// 원고 지문: 승인은 이 값에 묶인다. 승인한 뒤 원고가 바뀌면 보내지 않고 다시 승인을 받는다.
export async function digest(m) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode([m.subject || '', m.htmlBody || '', m.textBody || ''].join('\u0000')));
  return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join('');
}
export const HASH = /^[0-9a-f]{64}$/;
// 보내기 직전에 원고가 승인한 그대로인지 본다. 승인 기록에 지문이 없으면(이 기능 전 승인) 지금 원고로 고정한다.
async function same(d, week, m) {
  const h = await digest(m), k = 'issue_hash:' + week, cur = await getMeta(d, k);
  if (!cur) { await setMeta(d, k, h); return true; }
  return cur === h;
}
// 미리보기 응답: 원고 안의 스크립트·폼이 사이트 권한으로 돌지 않게 격리(sandbox)해서 내보낸다
export const PREVIEW_HEADERS = { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex',
  'content-security-policy': "sandbox; default-src 'none'; img-src https: data:; style-src 'unsafe-inline'; font-src https: data:" };
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

// 확인한 구독자 중 이번 호를 아직 안 받은 사람에게 최대 limit명 발송.
// 받을 사람을 먼저 한 문장으로 '보내는 중'으로 잡아 둔 뒤 보낸다(여러 요청이 동시에 돌아도 같은 사람에게 두 번 가지 않게).
const staleAt = () => new Date(Date.now() + 9 * 3600e3 - 3600e3).toISOString().replace('Z', '+09:00');   // 1시간 넘게 '보내는 중'이면 멈춘 것으로 본다
const UNSENT = `NOT EXISTS (SELECT 1 FROM sends x WHERE x.week = ?1 AND x.email = s.email AND (x.status = 'sent' OR (x.status = 'sending' AND x.at >= ?2)))`;
export async function sendNext(env, d, origin, week, limit = 50) {
  const m = await draft(env, origin, week); if (!m) return { ok: false, msg: '원고가 없어요.' };
  if (!(await same(d, week, m))) { await setMeta(d, 'issue:' + week, 'changed'); return { ok: false, changed: true, sent: 0, remaining: 0, msg: '승인한 뒤 원고가 바뀌어 발송을 멈췄어요. 다시 승인해 주세요.' }; }
  const now = kst(), stale = staleAt();
  const claimed = (await d.prepare(`INSERT INTO sends (week, email, status, at) SELECT ?1, s.email, 'sending', ?3 FROM subscribers s
    WHERE s.status = 'active' AND s.token IS NOT NULL AND ${UNSENT} ORDER BY s.confirmed_at LIMIT ?4
    ON CONFLICT(week, email) DO UPDATE SET status = 'sending', at = excluded.at WHERE sends.status != 'sent' RETURNING email`).bind(week, stale, now, limit).all()).results.map(x => x.email);
  if (!claimed.length) {
    const busy = (await d.prepare("SELECT COUNT(*) AS n FROM sends WHERE week = ?1 AND status = 'sending' AND at >= ?2").bind(week, stale).first()).n;
    if (!busy) await setMeta(d, 'issue:' + week, 'done');
    return { ok: true, sent: 0, remaining: 0 };
  }
  const rows = (await d.prepare("SELECT email, token FROM subscribers WHERE email IN (SELECT value FROM json_each(?1))").bind(JSON.stringify(claimed)).all()).results;
  const r = await batch(env, rows.map(x => issueMail(env, origin, m, x.email, x.token)));
  const at = kst();
  await d.batch(rows.map((x, i) => d.prepare("UPDATE sends SET status = ?3, at = ?4, id = ?5, err = ?6 WHERE week = ?1 AND email = ?2").bind(week, x.email, r.ok ? 'sent' : 'failed', at, r.ids[i] || null, r.err)));
  if (!r.ok && r.status === 429) await setMeta(d, 'issue_pause', at.slice(0, 10));
  const left = (await d.prepare(`SELECT COUNT(*) AS n FROM subscribers s WHERE status = 'active' AND token IS NOT NULL AND ${UNSENT}`).bind(week, staleAt()).first()).n;
  if (r.ok && !left) await setMeta(d, 'issue:' + week, 'done');
  return { ok: r.ok, status: r.status, sent: r.ok ? rows.length : 0, remaining: left, err: r.err };
}

// 이번 호의 근거: index.json의 그 주 반영 원장(ledger)과 feed.json 제목을 묶는다(승인할 때 숫자의 근거를 같이 보게)
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
export async function evidence(env, origin, week) {
  const get = async p => { try { const r = await env.ASSETS.fetch(new URL(p, origin)); return r.ok ? r.json() : null; } catch (e) { return null; } };
  const [idx, feed] = await Promise.all([get('/index.json'), get('/feed.json')]);
  const ws = idx?.weeks || []; const i = ws.findIndex(w => w.week === week); if (i < 0) return null;
  const w = ws[i], prev = ws[i - 1];
  const by = Object.fromEntries((feed?.items || []).map(n => [n.id, n]));
  const rows = (w.ledger || (w.applied || []).map(id => ({ id, w: null })))
    .map(e => ({ id: e.id, dp: e.dp ?? null, why: e.why || '', hd: by[e.id]?.hd || e.id, src: by[e.id]?.src || '', url: by[e.id]?.url || '', rv: by[e.id]?.rv || '', on: e.w == null || e.w > 0 }))
    .filter(e => e.on).sort((a, b) => (b.dp ?? 0) - (a.dp ?? 0));
  return { week, total: w.total, delta: prev?.total != null && w.total != null ? w.total - prev.total : null, scale: w.scale ?? null, review: w.review || null, rows };
}
const pp = x => Math.abs(x) < 5e-6 ? (x > 0 ? '<0.001%p' : '0') : (x >= 0 ? '+' : '') + (x * 100).toFixed(3) + '%p';
export function evidenceHtml(ev) {
  if (!ev) return '';
  const rv = ev.review;
  const rvLine = !rv ? '독립 검토 기록 없음(규칙 도입 전 호)' : rv.by === 'skipped' ? '⚠ 독립 검토 없이 발표됨' :
    `${rv.by === 'independent' ? '독립 검토' : '⚠ 자체 검토'}: 확인 ${rv.ok} · 수정 ${rv.fix} · 보류 ${rv.hold}${rv.late?.length ? ` · 다음 주로 ${rv.late.length}` : ''}`;
  const head = `이번 주 ${ev.total != null ? (ev.total * 100).toFixed(2) + '%' : ''}${ev.delta != null ? ` (${pp(ev.delta)})` : ''} · 반영 소식 ${ev.rows.length}건${ev.scale != null && ev.scale < 1 ? ` · 주간 상한으로 ×${ev.scale} 축소` : ''}`;
  const li = ev.rows.slice(0, 12).map(e => `<tr><td style="padding:6px 8px 6px 0;border-bottom:1px solid #e5e5ea;vertical-align:top;white-space:nowrap;font-variant-numeric:tabular-nums;color:#a3206f">${e.dp != null ? pp(e.dp) : '–'}</td><td style="padding:6px 0;border-bottom:1px solid #e5e5ea">${webUrl(e.url) ? `<a href="${esc(webUrl(e.url))}" style="color:#1c1c1e">${esc(e.hd)}</a>` : esc(e.hd)}<br><span style="color:#6b6b70;font-size:12px">${esc(e.src)}${e.why ? ' · ' + esc(e.why) : ''}${e.rv ? ' · 검토: ' + esc(e.rv) : ''}</span></td></tr>`).join('');
  return `<div style="font:14px/1.55 -apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;color:#1c1c1e;background:#fff;border:1px solid #d1d1d6;padding:14px 16px;margin:0 0 16px"><b>숫자의 근거</b><br><span style="color:#3a3a3c">${esc(head)}</span><br><span style="color:#3a3a3c">${esc(rvLine)}</span>${li ? `<table style="width:100%;border-collapse:collapse;margin-top:8px;font-size:13px">${li}</table>` : ''}${ev.rows.length > 12 ? `<p style="color:#6b6b70;font-size:12px;margin:6px 0 0">외 ${ev.rows.length - 12}건은 운영 화면에서 볼 수 있어요.</p>` : ''}</div>`;
}
export function evidenceText(ev) {
  if (!ev) return '';
  const rv = ev.review; const lines = [`[숫자의 근거] ${ev.total != null ? (ev.total * 100).toFixed(2) + '%' : ''}${ev.delta != null ? ` (${pp(ev.delta)})` : ''} · 반영 ${ev.rows.length}건` + (rv && rv.by !== 'skipped' ? ` · 검토 확인 ${rv.ok}/수정 ${rv.fix}/보류 ${rv.hold}${rv.by !== 'independent' ? '(자체)' : ''}` : rv ? ' · 독립 검토 없음' : '')];
  for (const e of ev.rows.slice(0, 12)) lines.push(`- ${e.dp != null ? pp(e.dp) : '–'} ${e.hd} (${e.src})`);
  return lines.join('\n') + '\n\n';
}

// 승인 요청 메일: 실제 메일 위에 승인 안내 띠와 '숫자의 근거'를 얹어서 보낸다
export async function askApproval(env, d, origin, it) {
  const to = adminTo(env); if (!to) return false;
  const m = await draft(env, origin, it.week); if (!m) return false;
  const n = (await d.prepare("SELECT COUNT(*) AS n FROM subscribers WHERE status = 'active'").first()).n;
  const h = await digest(m);
  const link = `${origin}/api/approve?w=${it.week}&h=${h}&s=${await sign(env, 'approve|' + it.week + '|' + h)}`;
  const S = (await sourceStatus(env, d)).filter(x => x.st === 'new' || x.st === 'due');
  const srcLine = S.length ? `<br><span style="color:#ffc266">자료 출처 확인 필요 ${S.length}건: ${S.map(x => esc(x.name)).join(', ')} · <a href="${origin}/admin" style="color:#ffc266">운영 화면</a></span>` : '';
  const band = `<div style="font:15px/1.6 -apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;background:#1c1c1e;color:#fff;padding:18px 20px;margin:0 0 16px"><b>[승인 요청] ${it.week} 주간 메일</b><br>아래가 구독자 ${n}명에게 갈 메일이에요. 내용을 확인하고 승인하면 바로 발송을 시작해요.${srcLine}<br><a href="${link}" style="display:inline-block;margin-top:10px;padding:10px 16px;background:#ff8ccd;color:#1c1c1e;font-weight:700;text-decoration:none">승인 화면 열기</a></div>`;
  const ev = await evidence(env, origin, it.week); const top = band + `<div style="max-width:640px;margin:0 auto">${evidenceHtml(ev)}</div>`;
  const body = /<body[^>]*>/i.test(m.htmlBody) ? m.htmlBody.replace(/<body([^>]*)>/i, `<body$1>${top}`) : top + m.htmlBody;
  const r = await batch(env, [{ from: env.MAIL_FROM, to: [to], subject: `[승인 요청] ${m.subject}`, html: personal(body, `${origin}/`), text: `[승인 요청] ${it.week} 주간 메일 · 구독자 ${n}명\n승인 화면: ${link}\n${S.length ? `자료 출처 확인 필요 ${S.length}건: ${S.map(x => x.name).join(', ')} · ${origin}/admin\n` : ''}\n` + evidenceText(ev) + personal(m.textBody, `${origin}/`) }]);
  return r.ok;
}

// 사이트 방문 때 조용히 도는 작업(5분에 한 번, 실패해도 페이지에는 영향 없음)
export async function tick(env, d, origin) {
  if (!mailOn(env) || !d) return;
  if (globalThis.__tick && Date.now() - globalThis.__tick < 5 * 60e3) return;
  globalThis.__tick = Date.now();
  await confirmCatchUp(env, d, origin);
  const list = await issues(env, origin); const it = list[0]; if (!it) return;
  if (Date.now() - Date.parse(it.date + 'T00:00:00+09:00') > 6 * 864e5) return;   // 일주일이 지난 호는 자동으로 다루지 않는다
  const st = await issueState(d, it.week);
  if (!st || st === 'changed') { if (await askApproval(env, d, origin, it)) await setMeta(d, 'issue:' + it.week, 'asked'); return; }
  if (st === 'approved') {
    if (await getMeta(d, 'issue_pause') === kst().slice(0, 10)) return;           // 오늘 한도에 걸렸으면 내일
    await sendNext(env, d, origin, it.week, 50);
  }
}

// 하루 한도(CONFIRM_DAY)에 걸려 확인 메일을 못 받은 최근 3일 신청자에게, 하루에 한 번 남은 한도만큼 보낸다
const CONFIRM_DAY = 40;
async function confirmCatchUp(env, d, origin) {
  const today = kst().slice(0, 10);
  if (await getMeta(d, 'confirm_catchup') === today) return;
  await setMeta(d, 'confirm_catchup', today);
  const c = await getMeta(d, 'confirm_day') || ''; const n = c.startsWith(today + ':') ? +c.split(':')[1] : 0;
  const room = Math.min(50, CONFIRM_DAY - n); if (room <= 0) return;
  const rows = (await d.prepare(`SELECT email, token FROM subscribers s WHERE status = 'pending' AND token IS NOT NULL AND consent_at >= ?1
    AND NOT EXISTS (SELECT 1 FROM sends x WHERE x.week = 'confirm' AND x.email = s.email AND x.status = 'sent') LIMIT ?2`).bind(new Date(Date.now() + 9 * 3600e3 - 3 * 864e5).toISOString().slice(0, 10), room).all()).results;
  if (!rows.length) return;
  const r = await batch(env, rows.map(x => ({ from: env.MAIL_FROM, ...reply(env), to: [x.email], ...confirmMail(origin, x.token) })));
  const now = kst();
  await d.batch([...rows.map((x, i) => d.prepare("INSERT INTO sends (week, email, status, at, id, err) VALUES ('confirm', ?1, ?2, ?3, ?4, ?5) ON CONFLICT(week, email) DO UPDATE SET status = excluded.status, at = excluded.at, id = excluded.id, err = excluded.err").bind(x.email, r.ok ? 'sent' : 'failed', now, r.ids[i] || null, r.err)),
    d.prepare("INSERT INTO meta (k, v) VALUES ('confirm_day', ?1) ON CONFLICT(k) DO UPDATE SET v = excluded.v").bind(`${today}:${n + (r.ok ? rows.length : 0)}`)]);
}

// 새 구독자 환영: 환영 메일 + 이미 발송을 승인한 가장 최근 호
export async function welcome(env, d, origin, email, tok) {
  if (!mailOn(env)) return;
  const unsub = `${origin}/api/unsub?t=${tok}`;
  const list = []; let wk = null;
  for (const it of await issues(env, origin)) { const st = await issueState(d, it.week); if (st === 'approved' || st === 'done') { wk = it.week; break; } }
  const w = { from: env.MAIL_FROM, ...reply(env), to: [email], subject: '[AI 점령 지도] 구독을 시작했어요',
    text: `구독을 시작했어요. 매주 월요일 아침에 AI 점령 지도 주간 메일을 보내드려요.${wk ? '\n가장 최근 호를 바로 이어서 보내드릴게요.' : ''}\n\n지도에서 내 직업을 찾아 저장하면, 그 직업에 닿은 AI 소식을 함께 볼 수 있어요.\n내 직업 찾아보기: ${origin}/\n수신 거부: ${unsub}` + textFoot(origin),
    html: mailHtml({ base: origin, label: 'WELCOME', title: '구독을 시작했어요', pre: '매주 월요일 아침, AI가 건드린 업무와 지수 변화를 보내드려요.',
      blocks: [{ p: `매주 월요일 아침, 한 주 동안 AI가 건드린 업무와 지수 변화, 그 숫자의 근거를 정리해 보내드려요.${wk ? ' 가장 최근 호는 이 메일 바로 다음에 이어서 보내드릴게요.' : ''}` },
        { box: '<b>이렇게 써 보세요</b><br>지도에서 내 직업을 찾아 저장하면, 그 직업에 닿은 AI 소식과 내 업무 중 AI가 해낼 수 있는 몫을 함께 볼 수 있어요.' },
        { cta: { url: `${origin}/`, text: '내 직업 찾아보기 →' } }],
      foot: `이 메일은 AI 점령 지도에서 주간 메일을 신청하고 구독을 확인한 분께 보내요. · ${link(unsub, '수신 거부')}` }),
    headers: { 'List-Unsubscribe': `<${unsub}>`, 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click' } };
  list.push(w);
  let m = null;
  if (wk) {
    const mm = await draft(env, origin, wk);
    // 이 사람 몫을 먼저 잡아 둔다(방문 때 도는 발송과 겹쳐 두 번 가지 않게). 원고가 승인한 것과 다르면 보내지 않는다.
    if (mm && await same(d, wk, mm)) {
      const got = await d.prepare("INSERT INTO sends (week, email, status, at) VALUES (?1, ?2, 'sending', ?3) ON CONFLICT(week, email) DO UPDATE SET status = 'sending', at = excluded.at WHERE sends.status = 'failed' RETURNING email").bind(wk, email, kst()).first();
      if (got) m = mm;
    }
  }
  if (m) list.push(issueMail(env, origin, m, email, tok));
  const r = await batch(env, list);
  if (m) await d.prepare("UPDATE sends SET status = ?3, at = ?4, id = ?5 WHERE week = ?1 AND email = ?2").bind(wk, email, r.ok ? 'sent' : 'failed', kst(), r.ids[1] || null).run();
}
