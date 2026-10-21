// 뉴스레터 구독 신청: 이메일과(선택) 관심 직업만 받는다.
// 이중 확인: 신청하면 '확인 전(pending)'으로만 저장하고, 확인 메일의 링크를 눌러야 구독(active)이 된다. 남의 주소를 대신 넣어도 메일이 가지 않는다.
// 이미 해지한 주소도 다시 신청하면 확인 메일을 거쳐야 한다(예전처럼 조용히 다시 구독되지 않음).
import { db, json, kst, clip, isEmail, token, sameOrigin } from '../_db.js';
import { sendMail, confirmMail, mailOn } from '../_mail.js';
export const CONSENT_VER = '2026-10-21';
export async function onRequestPost({ request, env }) {
  if (!sameOrigin(request)) return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 403);
  if (!/application\/json/.test(request.headers.get('content-type') || '')) return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 415);
  let b = {}; try { b = await request.json(); } catch (e) { return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 400); }
  if (b.website) return json({ ok: true });
  const email = clip(b.email, 254).toLowerCase();
  if (!isEmail(email)) return json({ ok: false, msg: '이메일 주소를 확인해 주세요.' }, 400);
  if (!b.consent) return json({ ok: false, msg: '개인정보 수집·이용에 동의해 주세요.' }, 400);
  const d = await db(env); if (!d) return json({ ok: false, msg: '구독 접수 준비 중이에요. 잠시 후 다시 시도해 주세요.' }, 503);
  const cur = await d.prepare("SELECT status, token FROM subscribers WHERE email = ?1").bind(email).first();
  // 이미 구독 중인 주소: 아무것도 바꾸지 않는다(누가 구독 중인지 알려주지 않도록 같은 문구)
  if (cur && cur.status === 'active') return json({ ok: true, msg: done(env) });
  const tok = token(), now = kst();
  await d.prepare(`INSERT INTO subscribers (email, job, src, created, status, token, consent_at, consent_ver) VALUES (?1, ?2, ?3, ?4, 'pending', ?5, ?4, ?6)
    ON CONFLICT(email) DO UPDATE SET job = excluded.job, src = excluded.src, status = 'pending', token = excluded.token, consent_at = excluded.consent_at, consent_ver = excluded.consent_ver, unsubscribed = NULL, unsub_at = NULL`)
    .bind(email, clip(b.job, 60), clip(b.src, 40), now, tok, CONSENT_VER).run();
  if (mailOn(env)) {
    const m = confirmMail(new URL(request.url).origin, tok);
    await sendMail(env, { to: email, ...m });
  }
  return json({ ok: true, msg: done(env) });
}
const done = env => mailOn(env)
  ? '확인 메일을 보냈어요. 메일의 \'구독 확인하기\'를 누르면 구독이 시작돼요.'
  : '구독 신청을 받았어요. 메일 발송을 시작하면 구독 확인 메일을 먼저 보내드릴게요.';
