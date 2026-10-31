// 후원·제휴·기관 리포트 문의 접수.
// 접수하면 ① 운영자에게 알림 메일(답장하면 문의한 사람에게 바로 감) ② 문의한 사람에게 접수 확인 메일을 보낸다.
// 악용 방지: 접수 확인 메일에는 입력한 글(이름·내용)을 다시 싣지 않는다(남의 주소로 스팸을 보내는 통로가 되지 않게).
// 같은 주소에는 24시간에 한 번, 하루 최대 RECEIPT_DAY통. 운영자 알림은 하루 최대 ALERT_DAY통. 넘으면 저장만 하고 운영 화면에서 본다.
// 저장 자체도 한 접속에서 하루 LEAD_IP건, 전체 하루 LEAD_ALL건까지(가짜 문의로 알림 한도를 다 쓰고 진짜 문의를 묻어 버리는 것 막기).
import { db, json, kst, clip, isEmail, sameOrigin, count, allow } from '../_db.js';
import { mailOn } from '../_mail.js';
import { adminTo, batch } from '../_issue.js';
import { mailHtml, esc, link, textFoot } from '../_tpl.js';
const KINDS = ['후원', '제휴·공동 콘텐츠', '조직 리포트', '워크숍·강연', '언론 취재', '공동 리포트·연구', '기타'];
const RECEIPT_DAY = 20, ALERT_DAY = 30;
export const LEAD_IP = 5, LEAD_ALL = 200;
export const bump = (d, key, cap, today) => count(d, key, cap, today);
export function leadMails(env, origin, L) {
  const reply = env.MAIL_REPLY_TO ? { reply_to: env.MAIL_REPLY_TO } : {};
  const to = adminTo(env), M = {};
  {
    const body = esc(L.msg).replace(/\n/g, '<br>');
    M.alert = ({ from: env.MAIL_FROM, to: [to], reply_to: L.email, subject: `[AI 점령 지도 문의] ${L.kind} · ${L.org || L.name || L.email}`,
      text: `${L.kind} 문의가 들어왔어요. 이 메일에 답장하면 문의한 분께 바로 가요.\n\n종류: ${L.kind}\n이름: ${L.name}\n소속: ${L.org}\n이메일: ${L.email}\n접수: ${L.at.slice(0, 16).replace('T', ' ')}\n\n${L.msg}\n\n운영 화면: ${origin}/admin`,
      html: mailHtml({ base: origin, label: '새 문의', title: `${L.kind} 문의가 들어왔어요`, pre: `${L.org || L.name} · ${L.msg.slice(0, 60)}`,
        blocks: [{ p: '이 메일에 답장하면 문의한 분께 바로 가요.' },
          { rows: [['종류', esc(L.kind)], ['이름', esc(L.name) || '—'], ['소속', esc(L.org) || '—'], ['이메일', link(`mailto:${L.email}`, L.email, '#16161a')], ['접수', esc(L.at.slice(0, 16).replace('T', ' '))]] },
          { box: body },
          { cta: { url: `mailto:${L.email}?subject=${encodeURIComponent('[AI 점령 지도] 문의 주신 내용 답변드려요')}`, text: '답장하기' } }],
        foot: `문의 기록은 접수 후 1년 뒤 지워져요. · ${link(`${origin}/admin`, '운영 화면')}` }) });
  }
  {
    M.receipt = ({ from: env.MAIL_FROM, ...reply, to: [L.email], subject: '[AI 점령 지도] 문의를 받았어요',
      text: `${L.kind} 문의를 잘 받았어요. 영업일 기준 2일 안에 이 주소로 답장드릴게요.\n\n직접 보내지 않으셨다면 이 메일은 무시하셔도 돼요. 문의 기록은 접수 후 1년 뒤 지워져요.` + textFoot(origin),
      html: mailHtml({ base: origin, label: '문의 접수', title: '문의를 받았어요', pre: '영업일 기준 2일 안에 답장드릴게요.',
        blocks: [{ p: `<b>${esc(L.kind)}</b> 문의를 잘 받았어요. 영업일 기준 2일 안에 이 주소로 답장드릴게요.` },
          { p: '기다리시는 동안 우리 조직 직무가 지도에서 어디쯤 있는지 미리 살펴보셔도 좋아요.' },
          { cta: { url: `${origin}/`, text: 'AI 점령 지도 보기 →' } }],
        foot: '직접 보내지 않으셨다면 이 메일은 무시하셔도 돼요. 문의 기록은 접수 후 1년 뒤 지워져요.' }) });
  }
  return M;
}
async function notify(env, d, origin, L) {
  if (!mailOn(env)) return;
  const today = L.at.slice(0, 10), out = [], M = leadMails(env, origin, L);
  if (adminTo(env) && await bump(d, 'lead_alert_day', ALERT_DAY, today)) out.push(M.alert);
  const again = (await d.prepare("SELECT COUNT(*) AS n FROM leads WHERE email = ?1 AND created >= ?2").bind(L.email, new Date(Date.now() + 9 * 3600e3 - 864e5).toISOString()).first()).n;
  if (again <= 1 && await bump(d, 'lead_receipt_day', RECEIPT_DAY, today)) out.push(M.receipt);
  if (out.length) await batch(env, out);
}
export async function onRequestPost({ request, env, waitUntil }) {
  if (!sameOrigin(request)) return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 403);
  let b = {}; try { b = await request.json(); } catch (e) { return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 400); }
  if (b.website) return json({ ok: true });
  const email = clip(b.email, 254).toLowerCase();
  if (!isEmail(email)) return json({ ok: false, msg: '이메일 주소를 확인해 주세요.' }, 400);
  if (!b.consent) return json({ ok: false, msg: '개인정보 수집·이용에 동의해 주세요.' }, 400);
  const msg = clip(b.msg, 2000); if (msg.length < 5) return json({ ok: false, msg: '문의 내용을 조금 더 적어 주세요.' }, 400);
  const d = await db(env); if (!d) return json({ ok: false, msg: '문의 접수 준비 중이에요. 잠시 후 다시 시도해 주세요.' }, 503);
  if (!(await allow(d, request, env, 'lead', LEAD_IP, LEAD_ALL))) return json({ ok: false, msg: '오늘은 문의를 많이 받았어요. 내일 다시 보내 주시거나 메일로 연락해 주세요.' }, 429);
  const kind = KINDS.includes(b.kind) ? b.kind : '기타';
  const L = { name: clip(b.name, 60), org: clip(b.org, 100), email, kind, msg: String(b.msg || '').slice(0, 2000).trim(), at: kst() };
  await d.prepare("INSERT INTO leads (name, org, email, kind, msg, created) VALUES (?1, ?2, ?3, ?4, ?5, ?6)").bind(L.name, L.org, email, kind, msg, L.at).run();
  waitUntil(notify(env, d, new URL(request.url).origin, L).catch(e => console.error(JSON.stringify({ at: 'lead-mail', err: String(e) }))));
  return json({ ok: true, msg: '문의를 받았어요. 영업일 기준 2일 안에 메일로 연락드릴게요.' });
}
