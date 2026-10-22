// 주간 메일 승인 화면. 승인 요청 메일의 링크(서명 포함)로만 열리고, 그 호를 만든 날부터 7일 동안만 쓸 수 있다.
// GET: 미리보기와 받을 사람 수, [승인하고 발송] 버튼(메일 보안 검사기가 링크를 미리 열어도 발송되지 않게 버튼을 한 번 더 누른다)
// GET &view=html: 미리보기용 원고
// POST: 승인 → 바로 최대 100명(50명×2) 발송, 남은 사람은 사이트 방문 때 50명씩 이어서(하루 한도에 걸리면 다음 날)
import { db, html, kst } from '../_db.js';
import { mailOn } from '../_mail.js';
import { WEEK, verify, issues, draft, personal, issueState, setMeta, sendNext, evidence, evidenceHtml } from '../_issue.js';
async function check(request, env) {
  const u = new URL(request.url), w = u.searchParams.get('w') || '', s = u.searchParams.get('s') || '';
  if (!WEEK.test(w) || !(await verify(env, 'approve|' + w, s))) return null;
  const it = (await issues(env, u.origin)).find(i => i.week === w);
  if (!it || Date.now() > Date.parse(it.date + 'T00:00:00+09:00') + 7 * 864e5) return { expired: true };
  return { w, s, u };
}
export async function onRequestGet({ request, env }) {
  const c = await check(request, env); if (!c) return html('링크가 올바르지 않아요', '<p>승인 요청 메일의 링크를 다시 눌러 주세요.</p>', 403);
  if (c.expired) return html('승인 링크가 만료됐어요', '<p>승인 링크는 호를 만든 날부터 7일 동안만 쓸 수 있어요. 운영 화면에서 승인해 주세요.</p><p><a class="b" href="/admin">운영 화면으로</a></p>', 410);
  const origin = c.u.origin, m = await draft(env, origin, c.w);
  if (!m) return html('원고가 없어요', `<p>${c.w} 주간 메일 원고를 찾지 못했어요.</p>`, 404);
  if (c.u.searchParams.get('view') === 'html') return new Response(personal(m.htmlBody, '#'), { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' } });
  const d = await db(env); if (!d) return html('잠시 후 다시 시도해 주세요', '<p>준비 중이에요.</p>', 503);
  const st = await issueState(d, c.w);
  const n = (await d.prepare("SELECT COUNT(*) AS n FROM subscribers WHERE status = 'active'").first()).n;
  const sent = (await d.prepare("SELECT COUNT(*) AS n FROM sends WHERE week = ?1 AND status = 'sent'").bind(c.w).first()).n;
  const pv = `<iframe src="/api/approve?w=${c.w}&s=${c.s}&view=html" title="미리보기" style="width:100%;height:560px;border:1px solid rgba(128,128,128,.4);background:#fff;margin:12px 0"></iframe>`;
  const head = `<p><b>${esc(m.subject)}</b></p><p>받을 사람: 확인한 구독자 ${n}명 · 지금까지 보낸 사람 ${sent}명</p>`;
  const evh = evidenceHtml(await evidence(env, origin, c.w));
  if (st === 'approved' || st === 'done')
    return html('이미 승인한 호예요', head + `<p>${st === 'done' ? '모두 보냈어요.' : '발송 중이에요. 남은 분들은 사이트 방문이 있을 때 50명씩 이어서 보내요.'}</p>` + evh + pv);
  if (!mailOn(env)) return html('메일 발송이 꺼져 있어요', head + '<p>Pages 설정의 MAIL_ENABLED·RESEND_API_KEY·MAIL_FROM을 확인하세요.</p>' + evh + pv);
  return html(`${c.w} 주간 메일 승인`, head + `<form method="post"><button class="b" type="submit">승인하고 발송</button></form><p style="font-size:13px">승인하면 바로 보내기 시작해요. Resend 무료 요금은 하루 100통이라, 더 많으면 다음 날 이어서 보내요.</p>` + evh + pv);
}
export async function onRequestPost({ request, env }) {
  const c = await check(request, env); if (!c) return html('링크가 올바르지 않아요', '<p>승인 요청 메일의 링크를 다시 눌러 주세요.</p>', 403);
  if (c.expired) return html('승인 링크가 만료됐어요', '<p>승인 링크는 호를 만든 날부터 7일 동안만 쓸 수 있어요. 운영 화면에서 승인해 주세요.</p><p><a class="b" href="/admin">운영 화면으로</a></p>', 410);
  if (!mailOn(env)) return html('메일 발송이 꺼져 있어요', '<p>Pages 설정을 확인하세요.</p>', 409);
  const d = await db(env); if (!d) return html('잠시 후 다시 시도해 주세요', '<p>준비 중이에요.</p>', 503);
  const st = await issueState(d, c.w);
  if (st !== 'approved' && st !== 'done') { await setMeta(d, 'issue:' + c.w, 'approved'); await setMeta(d, 'issue_approved_at:' + c.w, kst()); }
  let sent = 0, r = { remaining: 0, ok: true };
  for (let i = 0; i < 2; i++) { r = await sendNext(env, d, c.u.origin, c.w, 50); sent += r.sent || 0; if (!r.ok || !r.remaining) break; }
  const tail = !r.ok ? (r.status === 429 ? '오늘 보낼 수 있는 양(하루 100통)을 넘어서 멈췄어요. 내일 사이트 방문이 있으면 자동으로 이어서 보내요.' : `일부를 보내지 못했어요(${r.status}). 사이트 방문 때 다시 시도해요.`)
    : r.remaining ? `남은 ${r.remaining}명은 사이트 방문이 있을 때 50명씩 자동으로 이어서 보내요.` : '모두 보냈어요.';
  return html('승인했어요', `<p>${sent}명에게 보냈어요. ${tail}</p><p><a class="b" href="/">AI 점령 지도로</a></p>`);
}
const esc = s => String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
