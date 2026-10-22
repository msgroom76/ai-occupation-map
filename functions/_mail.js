// 메일 보내기(Resend). 세 가지가 모두 설정돼 있을 때만 실제로 보낸다 — 운영자가 발송을 켜기 전에는 아무 메일도 나가지 않는다.
//   MAIL_ENABLED = "1", RESEND_API_KEY (비밀값), MAIL_FROM (예: "AI 점령 지도 <news@aijido.org>"). 답장 받을 곳은 MAIL_REPLY_TO(선택).
import { mailHtml, link, textFoot } from './_tpl.js';
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
  const text = `AI 점령 지도 주간 메일 구독 신청을 받았어요.\n아래 주소를 열면 구독이 시작되고, 환영 메일과 가장 최근 호를 바로 보내드려요.\n${c}\n\n직접 신청하지 않으셨다면 이 메일은 무시하셔도 돼요. 확인하지 않으면 30일 뒤 신청 기록이 지워져요.\n신청 취소: ${u}` + textFoot(base);
  const html = mailHtml({ base, label: '구독 확인', title: '구독을 확인해 주세요', pre: '버튼을 누르면 주간 메일 구독이 시작돼요.',
    blocks: [{ p: '주간 메일 구독 신청을 받았어요. 아래 버튼을 누르면 구독이 시작되고, 환영 메일과 가장 최근 호를 바로 보내드려요.' },
      { cta: { url: c, text: '구독 확인하기', accent: true } },
      { muted: `버튼이 눌리지 않으면 이 주소를 여세요.<br>${link(c, c)}` }],
    foot: `직접 신청하지 않으셨다면 이 메일은 무시하셔도 돼요. 확인하지 않으면 30일 뒤 신청 기록이 지워져요. · ${link(u, '신청 취소')}` });
  return { subject, text, html, headers: { 'List-Unsubscribe': `<${u}>`, 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click' } };
}
