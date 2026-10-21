// 구독 확인 링크(확인 메일의 '구독 확인하기'). 링크를 연 것만으로 확인된다.
import { db, html, kst } from '../_db.js';
export async function onRequestGet({ request, env }) {
  const t = new URL(request.url).searchParams.get('t') || '';
  if (!/^[0-9a-f]{48}$/.test(t)) return html('링크가 올바르지 않아요', '<p>메일의 링크를 다시 눌러 주세요.</p>', 400);
  const d = await db(env); if (!d) return html('잠시 후 다시 시도해 주세요', '<p>준비 중이에요.</p>', 503);
  const s = await d.prepare("SELECT status FROM subscribers WHERE token = ?1").bind(t).first();
  if (!s) return html('링크가 만료됐어요', '<p>신청한 지 오래됐거나 이미 해지한 링크예요. 사이트에서 다시 신청해 주세요.</p><p><a class="b" href="/">AI 점령 지도로</a></p>', 404);
  if (s.status !== 'active') await d.prepare("UPDATE subscribers SET status = 'active', confirmed_at = ?2 WHERE token = ?1").bind(t, kst()).run();
  return html('구독이 시작됐어요', '<p>매주 월요일 아침에 주간 지수와 한 주의 AI 소식을 보내드릴게요. 메일마다 있는 \'수신 거부\' 링크로 언제든 끊을 수 있어요.</p><p><a class="b" href="/">AI 점령 지도로</a></p>');
}
