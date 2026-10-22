// 뉴스레터 구독 신청: 이메일과(선택) 관심 직업만 받는다.
// 이중 확인: 신청하면 '확인 전(pending)'으로만 저장하고, 확인 메일의 링크를 눌러야 구독(active)이 된다. 남의 주소를 대신 넣어도 메일이 가지 않는다.
// 이미 해지한 주소도 다시 신청하면 확인 메일을 거쳐야 한다(예전처럼 조용히 다시 구독되지 않음).
// 악용 방지(2026-10-22): 같은 주소에는 24시간에 한 번만 확인 메일을 보낸다. 확인 메일은 하루 최대 CONFIRM_DAY통만 보내
// 주간 메일 몫(Resend 무료 하루 100통)을 남긴다. 넘친 신청은 대기로만 저장하고, 운영 화면의 '확인 메일 다시 보내기'나 다음 날 자동으로 보낸다.
import { db, json, kst, clip, isEmail, token, sameOrigin } from '../_db.js';
import { sendMail, confirmMail, mailOn } from '../_mail.js';
export const CONSENT_VER = '2026-10-21';
export const CONFIRM_DAY = 40;
export async function onRequestPost({ request, env }) {
  if (!sameOrigin(request)) return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 403);
  if (!/application\/json/.test(request.headers.get('content-type') || '')) return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 415);
  let b = {}; try { b = await request.json(); } catch (e) { return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 400); }
  if (b.website) return json({ ok: true });
  const email = clip(b.email, 254).toLowerCase();
  if (!isEmail(email)) return json({ ok: false, msg: '이메일 주소를 확인해 주세요.' }, 400);
  if (!b.consent) return json({ ok: false, msg: '개인정보 수집·이용에 동의해 주세요.' }, 400);
  const d = await db(env); if (!d) return json({ ok: false, msg: '구독 접수 준비 중이에요. 잠시 후 다시 시도해 주세요.' }, 503);
  const cur = await d.prepare("SELECT status, token, consent_at FROM subscribers WHERE email = ?1").bind(email).first();
  // 이미 구독 중인 주소: 아무것도 바꾸지 않는다(누가 구독 중인지 알려주지 않도록 같은 문구)
  if (cur && cur.status === 'active') return json({ ok: true, msg: done(env) });
  // 24시간 안에 이미 확인 메일을 보낸 대기 주소: 다시 보내지 않는다(같은 문구)
  if (cur && cur.status === 'pending' && cur.token && cur.consent_at && Date.now() - Date.parse(cur.consent_at) < 864e5) return json({ ok: true, msg: done(env) });
  const tok = token(), now = kst();
  await d.prepare(`INSERT INTO subscribers (email, job, src, created, status, token, consent_at, consent_ver) VALUES (?1, ?2, ?3, ?4, 'pending', ?5, ?4, ?6)
    ON CONFLICT(email) DO UPDATE SET job = excluded.job, src = excluded.src, status = 'pending', token = excluded.token, consent_at = excluded.consent_at, consent_ver = excluded.consent_ver, unsubscribed = NULL, unsub_at = NULL`)
    .bind(email, clip(b.job, 60), clip(b.src, 40), now, tok, CONSENT_VER).run();
  if (mailOn(env)) {
    const today = now.slice(0, 10);
    const sent = (await d.prepare("SELECT v FROM meta WHERE k = 'confirm_day'").first())?.v || '';
    const n = sent.startsWith(today + ':') ? +sent.split(':')[1] : 0;
    if (n >= CONFIRM_DAY) return json({ ok: true, msg: '신청을 받았어요. 오늘 신청이 많아 확인 메일이 내일 갈 수 있어요. 메일이 오면 \'구독 확인하기\'를 눌러 주세요.' });
    await d.prepare("INSERT INTO meta (k, v) VALUES ('confirm_day', ?1) ON CONFLICT(k) DO UPDATE SET v = excluded.v").bind(`${today}:${n + 1}`).run();
    const m = confirmMail(new URL(request.url).origin, tok);
    const r = await sendMail(env, { to: email, ...m });
    await d.prepare("INSERT INTO sends (week, email, status, at) VALUES ('confirm', ?1, ?2, ?3) ON CONFLICT(week, email) DO UPDATE SET status = excluded.status, at = excluded.at").bind(email, r.sent ? 'sent' : 'failed', now).run();
  }
  return json({ ok: true, msg: done(env) });
}
const done = env => mailOn(env)
  ? '확인 메일을 보냈어요. 메일의 \'구독 확인하기\'를 누르면 구독이 시작돼요.'
  : '구독 신청을 받았어요. 메일 발송을 시작하면 구독 확인 메일을 먼저 보내드릴게요.';
