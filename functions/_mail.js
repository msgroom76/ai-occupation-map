// 메일 보내기(Resend). 세 가지가 모두 설정돼 있을 때만 실제로 보낸다 — 운영자가 발송을 켜기 전에는 아무 메일도 나가지 않는다.
//   MAIL_ENABLED = "1", RESEND_API_KEY (비밀값), MAIL_FROM (예: "AI 점령 지도 <news@aijido.org>"). 답장 받을 곳은 MAIL_REPLY_TO(선택).
export const mailOn = env => env.MAIL_ENABLED === '1' && !!env.RESEND_API_KEY && !!env.MAIL_FROM;
export async function sendMail(env, { to, subject, html, text, headers }) {
  if (!mailOn(env)) return { sent: false, reason: 'off' };
  const r = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'authorization': `Bearer ${env.RESEND_API_KEY}`, 'content-type': 'application/json' },
    body: JSON.stringify({ from: env.MAIL_FROM, to: [to], subject, html, text, headers, ...(env.MAIL_REPLY_TO ? { reply_to: env.MAIL_REPLY_TO } : {}) })
  });
  if (!r.ok) { console.error(JSON.stringify({ at: 'sendMail', status: r.status, body: (await r.text()).slice(0, 300) })); return { sent: false, reason: 'error' }; }
  return { sent: true };
}
export function confirmMail(base, tok) {
  const c = `${base}/api/confirm?t=${tok}`, u = `${base}/api/unsub?t=${tok}`;
  const subject = '[AI 점령 지도] 구독을 확인해 주세요';
  const text = `AI 점령 지도 주간 메일 구독 신청을 받았어요.\n아래 주소를 열면 구독이 시작돼요.\n${c}\n\n직접 신청하지 않으셨다면 이 메일은 무시하셔도 돼요. 확인하지 않으면 30일 뒤 신청 기록이 지워져요.\n\n운영: 포스트오피스 · 개인정보처리방침 ${base}/privacy`;
  const html = `<div style="font:15px/1.7 -apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif;color:#1c1c1e;max-width:520px"><p><b>AI 점령 지도</b> 주간 메일 구독 신청을 받았어요.</p><p><a href="${c}" style="display:inline-block;padding:12px 18px;background:#1c1c1e;color:#fff;text-decoration:none;font-weight:600">구독 확인하기</a></p><p style="color:#6b6b70;font-size:13px">직접 신청하지 않으셨다면 이 메일은 무시하셔도 돼요. 확인하지 않으면 30일 뒤 신청 기록이 지워져요.<br>운영: 포스트오피스 · <a href="${base}/privacy" style="color:#6b6b70">개인정보처리방침</a> · <a href="${u}" style="color:#6b6b70">신청 취소</a></p></div>`;
  return { subject, text, html, headers: { 'List-Unsubscribe': `<${u}>`, 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click' } };
}
