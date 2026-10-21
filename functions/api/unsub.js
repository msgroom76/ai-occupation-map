// 수신 거부.
// GET: 확인 화면(메일 보안 검사기가 링크를 미리 열어도 해지되지 않게 버튼을 한 번 더 누르게 한다)
// POST: 실제 해지. 메일 앱의 '구독 취소' 버튼(List-Unsubscribe-Post: One-Click)도 이 주소로 POST한다.
import { db, html, kst } from '../_db.js';
const ok = t => /^[0-9a-f]{48}$/.test(t);
export async function onRequestGet({ request }) {
  const t = new URL(request.url).searchParams.get('t') || '';
  if (!ok(t)) return html('링크가 올바르지 않아요', '<p>메일의 수신 거부 링크를 다시 눌러 주세요.</p>', 400);
  return html('메일 수신을 거부할까요?', `<p>아래 버튼을 누르면 더 이상 AI 점령 지도 메일을 보내지 않아요. 해지한 주소는 30일 뒤 지워져요.</p><form method="post" action="/api/unsub?t=${t}"><button class="b" type="submit">수신 거부하기</button></form>`);
}
export async function onRequestPost({ request, env }) {
  const t = new URL(request.url).searchParams.get('t') || '';
  if (!ok(t)) return html('링크가 올바르지 않아요', '<p>메일의 수신 거부 링크를 다시 눌러 주세요.</p>', 400);
  const d = await db(env); if (!d) return html('잠시 후 다시 시도해 주세요', '<p>준비 중이에요.</p>', 503);
  const now = kst();
  await d.prepare("UPDATE subscribers SET status = 'unsub', unsub_at = ?2, unsubscribed = ?2 WHERE token = ?1 AND status != 'unsub'").bind(t, now).run();
  return html('수신 거부했어요', '<p>더 이상 메일을 보내지 않아요. 다시 받고 싶으면 사이트에서 새로 신청해 주세요.</p><p><a class="b" href="/">AI 점령 지도로</a></p>');
}
