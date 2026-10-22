// 운영자 로그인 링크.
// POST(JSON): 운영자 메일로 로그인 링크를 보낸다(누가 눌러도 운영자 메일로만 간다, 2분에 한 번).
// GET ?e=<만료>&n=<일회용 값>&s=<서명>: [로그인] 버튼만 있는 화면. 메일 보안 검사기가 링크를 미리 열어도 로그인되지 않는다.
// POST(폼, 같은 e·n·s): 버튼을 누르면 일회용 값을 지우고 30일 로그인 쿠키를 준다. 링크는 15분, 한 번만, 가장 최근 것만 쓸 수 있다.
// DELETE: 로그아웃.
import { db, json, html, kst, token, sameOrigin } from '../../_db.js';
import { mailOn } from '../../_mail.js';
import { sign, verify, adminTo, batch, setMeta } from '../../_issue.js';
import { COOKIE, makeSession } from '../../_admin.js';
import { mailHtml } from '../../_tpl.js';
async function linkOk(env, d, e, n, s) {
  if (!/^\d+$/.test(e) || +e < Date.now() / 1000 || !/^[0-9a-f]{48}$/.test(n) || !(await verify(env, `login|${e}|${n}`, s))) return false;
  return !!d && (await d.prepare("SELECT v FROM meta WHERE k = 'admin_login_nonce'").first())?.v === n;
}
const expired = () => html('링크가 만료됐어요', '<p>로그인 링크는 15분 동안, 한 번만 쓸 수 있어요. 새 링크를 받으면 전에 받은 링크는 쓸 수 없어요. 운영 화면에서 다시 받아 주세요.</p><p><a class="b" href="/admin">운영 화면으로</a></p>', 403);
export async function onRequestPost({ request, env }) {
  if (/application\/x-www-form-urlencoded/.test(request.headers.get('content-type') || '')) {   // 로그인 버튼
    if (!sameOrigin(request)) return expired();
    const f = await request.formData(), e = String(f.get('e') || ''), n = String(f.get('n') || ''), s = String(f.get('s') || '');
    const d = await db(env); if (!(await linkOk(env, d, e, n, s))) return expired();
    await d.prepare("DELETE FROM meta WHERE k = 'admin_login_nonce'").run();
    return new Response(null, { status: 303, headers: { location: '/admin', 'set-cookie': `${COOKIE}=${await makeSession(env)}; Path=/; Max-Age=${30 * 86400}; HttpOnly; Secure; SameSite=Lax`, 'cache-control': 'no-store' } });
  }
  const to = adminTo(env);
  if (!mailOn(env) || !to || !env.STATS_KEY) return json({ ok: false, msg: '메일 로그인을 쓸 수 없어요(메일 발송 설정·STATS_KEY 확인). 운영 키로 들어오세요.' }, 409);
  const d = await db(env);
  if (d) {
    const last = (await d.prepare("SELECT v FROM meta WHERE k = 'admin_login_at'").first())?.v;
    if (last && Date.now() - Date.parse(last) < 120e3) return json({ ok: true, msg: '방금 로그인 링크를 보냈어요. 메일함을 확인하세요.' });
    await setMeta(d, 'admin_login_at', new Date().toISOString());
  }
  if (!d) return json({ ok: false, msg: 'DB 연결 전이에요.' }, 503);
  const exp = Math.floor(Date.now() / 1000) + 15 * 60, origin = new URL(request.url).origin, nonce = token();
  await setMeta(d, 'admin_login_nonce', nonce);
  const link = `${origin}/api/admin/login?e=${exp}&n=${nonce}&s=${await sign(env, `login|${exp}|${nonce}`)}`;
  const r = await batch(env, [{ from: env.MAIL_FROM, to: [to], subject: '[AI 점령 지도] 운영 화면 로그인 링크',
    text: `운영 화면에 로그인하려면 15분 안에 아래 주소를 열고 [로그인]을 누르세요. 링크는 한 번만 쓸 수 있어요.\n${link}\n\n직접 요청하지 않았다면 무시하세요. 요청 시각 ${kst().slice(0, 16).replace('T', ' ')}`,
    html: mailHtml({ base: origin, label: 'ADMIN', title: '운영 화면 로그인', pre: '15분 안에 한 번만 쓸 수 있는 로그인 링크예요.',
      blocks: [{ p: '아래 버튼을 열고 [로그인]을 누르면 이 기기에서 30일 동안 로그인돼요. 링크는 15분 동안 한 번만 쓸 수 있고, 새 링크를 받으면 이 링크는 쓸 수 없어요.' },
        { cta: { url: link, text: '운영 화면 열기' } }],
      foot: `직접 요청하지 않았다면 이 메일은 무시하세요. 요청 시각 ${kst().slice(0, 16).replace('T', ' ')}` }) }]);
  const m = to.replace(/^(.{2}).*@/, '$1***@');
  return json({ ok: r.ok, msg: r.ok ? `${m}로 로그인 링크를 보냈어요. 15분 안에 눌러 주세요.` : '메일을 보내지 못했어요.' }, r.ok ? 200 : 502);
}
export async function onRequestGet({ request, env }) {
  const u = new URL(request.url), e = u.searchParams.get('e') || '', n = u.searchParams.get('n') || '', s = u.searchParams.get('s') || '';
  if (!(await linkOk(env, await db(env), e, n, s))) return expired();
  const q = v => String(v).replace(/[^0-9a-f]/g, '');
  return html('운영 화면 로그인', `<p>이 기기에서 운영 화면에 로그인할게요. 로그인은 30일 동안 유지돼요.</p><form method="post" action="/api/admin/login"><input type="hidden" name="e" value="${q(e)}"><input type="hidden" name="n" value="${q(n)}"><input type="hidden" name="s" value="${q(s)}"><button class="b" type="submit">로그인</button></form>`);
}
export async function onRequestDelete() {
  return new Response(JSON.stringify({ ok: true }), { headers: { 'content-type': 'application/json', 'set-cookie': `${COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax` } });
}
