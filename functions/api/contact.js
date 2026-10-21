// 기관·기업 리포트 문의 접수.
import { db, json, kst, clip, isEmail, sameOrigin } from '../_db.js';
export async function onRequestPost({ request, env }) {
  if (!sameOrigin(request)) return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 403);
  let b = {}; try { b = await request.json(); } catch (e) { return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 400); }
  if (b.website) return json({ ok: true });
  const email = clip(b.email, 254).toLowerCase();
  if (!isEmail(email)) return json({ ok: false, msg: '이메일 주소를 확인해 주세요.' }, 400);
  if (!b.consent) return json({ ok: false, msg: '개인정보 수집·이용에 동의해 주세요.' }, 400);
  const msg = clip(b.msg, 2000); if (msg.length < 5) return json({ ok: false, msg: '문의 내용을 조금 더 적어 주세요.' }, 400);
  const d = await db(env); if (!d) return json({ ok: false, msg: '문의 접수 준비 중이에요. 잠시 후 다시 시도해 주세요.' }, 503);
  await d.prepare("INSERT INTO leads (name, org, email, kind, msg, created) VALUES (?1, ?2, ?3, ?4, ?5, ?6)")
    .bind(clip(b.name, 60), clip(b.org, 100), email, clip(b.kind, 40), msg, kst()).run();
  return json({ ok: true, msg: '문의를 받았어요. 영업일 기준 2일 안에 메일로 연락드릴게요.' });
}
