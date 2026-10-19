// 뉴스레터 구독: 이메일과(선택) 관심 직업만 받는다.
import { db, json, kst, clip, isEmail } from '../_db.js';
export async function onRequestPost({ request, env }) {
  let b = {}; try { b = await request.json(); } catch (e) { return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 400); }
  if (b.website) return json({ ok: true });
  const email = clip(b.email, 254).toLowerCase();
  if (!isEmail(email)) return json({ ok: false, msg: '이메일 주소를 확인해 주세요.' }, 400);
  if (!b.consent) return json({ ok: false, msg: '개인정보 수집·이용에 동의해 주세요.' }, 400);
  const d = await db(env); if (!d) return json({ ok: false, msg: '구독 접수 준비 중이에요. 잠시 후 다시 시도해 주세요.' }, 503);
  await d.prepare("INSERT INTO subscribers (email, job, src, created) VALUES (?1, ?2, ?3, ?4) ON CONFLICT(email) DO UPDATE SET job = excluded.job, unsubscribed = NULL")
    .bind(email, clip(b.job, 60), clip(b.src, 40), kst()).run();
  return json({ ok: true, msg: '구독했어요. 매주 월요일 주간 지수를 보내드릴게요.' });
}
