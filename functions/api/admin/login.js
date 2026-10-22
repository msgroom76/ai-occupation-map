// 운영자 로그인 링크.
// POST: 운영자 메일로 로그인 링크를 보낸다(누가 눌러도 운영자 메일로만 간다, 2분에 한 번).
// GET ?e=<만료>&s=<서명>: 링크를 누르면 30일 로그인 쿠키를 주고 /admin으로 보낸다(링크는 15분 동안만 유효).
// DELETE: 로그아웃.
import { db, json, html, kst } from '../../_db.js';
import { mailOn } from '../../_mail.js';
import { sign, verify, adminTo, batch, setMeta } from '../../_issue.js';
import { COOKIE, makeSession } from '../../_admin.js';
export async function onRequestPost({ request, env }) {
  const to = adminTo(env);
  if (!mailOn(env) || !to || !env.STATS_KEY) return json({ ok: false, msg: '메일 로그인을 쓸 수 없어요(메일 발송 설정·STATS_KEY 확인). 운영 키로 들어오세요.' }, 409);
  const d = await db(env);
  if (d) {
    const last = (await d.prepare("SELECT v FROM meta WHERE k = 'admin_login_at'").first())?.v;
    if (last && Date.now() - Date.parse(last) < 120e3) return json({ ok: true, msg: '방금 로그인 링크를 보냈어요. 메일함을 확인하세요.' });
    await setMeta(d, 'admin_login_at', new Date().toISOString());
  }
  const exp = Math.floor(Date.now() / 1000) + 15 * 60, origin = new URL(request.url).origin;
  const link = `${origin}/api/admin/login?e=${exp}&s=${await sign(env, 'login|' + exp)}`;
  const r = await batch(env, [{ from: env.MAIL_FROM, to: [to], subject: '[AI 점령 지도] 운영 화면 로그인 링크',
    text: `운영 화면에 로그인하려면 15분 안에 아래 주소를 여세요.\n${link}\n\n직접 요청하지 않았다면 무시하세요. ${kst()}`,
    html: `<div style="font:15px/1.7 -apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;color:#1c1c1e"><p>AI 점령 지도 운영 화면 로그인 링크예요. 15분 동안만 쓸 수 있어요.</p><p><a href="${link}" style="display:inline-block;padding:12px 18px;background:#1c1c1e;color:#fff;text-decoration:none;font-weight:600">운영 화면 열기</a></p><p style="color:#6b6b70;font-size:13px">직접 요청하지 않았다면 이 메일은 무시하세요.</p></div>` }]);
  const m = to.replace(/^(.{2}).*@/, '$1***@');
  return json({ ok: r.ok, msg: r.ok ? `${m}로 로그인 링크를 보냈어요. 15분 안에 눌러 주세요.` : '메일을 보내지 못했어요.' }, r.ok ? 200 : 502);
}
export async function onRequestGet({ request, env }) {
  const u = new URL(request.url), e = u.searchParams.get('e') || '', s = u.searchParams.get('s') || '';
  if (!/^\d+$/.test(e) || +e < Date.now() / 1000 || !(await verify(env, 'login|' + e, s)))
    return html('링크가 만료됐어요', '<p>로그인 링크는 15분 동안만 쓸 수 있어요. 운영 화면에서 다시 받아 주세요.</p><p><a class="b" href="/admin">운영 화면으로</a></p>', 403);
  return new Response(null, { status: 303, headers: { location: '/admin', 'set-cookie': `${COOKIE}=${await makeSession(env)}; Path=/; Max-Age=${30 * 86400}; HttpOnly; Secure; SameSite=Lax`, 'cache-control': 'no-store' } });
}
export async function onRequestDelete() {
  return new Response(JSON.stringify({ ok: true }), { headers: { 'content-type': 'application/json', 'set-cookie': `${COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax` } });
}
