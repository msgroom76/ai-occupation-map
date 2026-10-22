// 거래 메일(구독 확인·환영·문의 접수·운영자 알림·로그인) 공통 틀.
// 주간 메일(tools/build_mail.py)과 같은 모양: 회색 바탕, 흰 카드 위 분홍 띠, 로고 머리, 검은 굵은 선, 네모난 검은 버튼, 회색 작은 꼬리말.
// 메일 프로그램은 <style>을 잘 지우므로 모든 모양은 인라인으로 넣는다. 밝은 모드 고정(color-scheme: light).
const INK = '#16161a', MUT = '#6b6b76', LINE = '#e6e6ea', PINK = '#8a085a', SOFT = '#fbf1f7', BG = '#f6f6f8';
const F = "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif";
export const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const tr = (inner, pad = '0') => `<tr><td style="padding:${pad}">${inner}</td></tr>`;

// 블록: {p:'문단(HTML 허용, 호출하는 쪽이 esc)'} · {muted:'작은 회색 문단'} · {cta:{url,text,accent?}} · {box:'분홍 바탕 상자(HTML)'}
//       · {rows:[[라벨, 값(HTML)],…]} · {rule:true}
export function mailHtml({ base, label, title, pre = '', blocks = [], foot = '' }) {
  const mast = `<table role="presentation" width="100%" cellpadding="0" cellspacing="0">`
    + `<tr><td colspan="2" style="padding:0 0 10px;font:600 12px/1.4 ${F};color:${INK}">AI 점령 지도 <span style="color:${MUT};font-weight:400">— 사람의 일, AI가 어디까지 장악했나?</span></td></tr>`
    + `<tr><td valign="bottom"><a href="${base}/" style="text-decoration:none"><img src="${base}/mail/img/logo.png" width="150" height="47" alt="AI 점령 지도 · AI Occupied Map" style="display:block;border:0;width:150px;height:auto;color:${PINK};font:700 20px ${F}"></a></td>`
    + `<td valign="bottom" align="right" style="font:700 12px/1.5 ${F};color:${INK};letter-spacing:.06em;white-space:nowrap">${esc(label)}</td></tr>`
    + `<tr><td colspan="2" style="padding:14px 0 0;border-bottom:2px solid ${INK}"></td></tr></table>`;
  const rows = [tr(mast), tr(`<div style="font:800 22px/1.4 ${F};letter-spacing:-.02em;color:${INK}">${esc(title)}</div>`, '28px 0 8px')];
  for (const b of blocks) {
    if (b.p) rows.push(tr(`<div style="font:15px/1.7 ${F};color:${INK}">${b.p}</div>`, '4px 0'));
    if (b.muted) rows.push(tr(`<div style="font:13px/1.6 ${F};color:${MUT}">${b.muted}</div>`, '8px 0 0'));
    if (b.box) rows.push(tr(`<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${SOFT}"><tr><td style="padding:16px 18px;font:15px/1.6 ${F};color:${INK}">${b.box}</td></tr></table>`, '12px 0'));
    if (b.cta) rows.push(tr(`<a href="${esc(b.cta.url)}" style="display:inline-block;background:${b.cta.accent ? PINK : INK};color:#ffffff;font:700 15px ${F};padding:13px 22px;text-decoration:none">${esc(b.cta.text)}</a>`, '20px 0 8px'));
    if (b.rows) rows.push(tr(`<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid ${INK}">${b.rows.map(([k, v]) => `<tr><td valign="top" width="88" style="padding:9px 0;border-bottom:1px solid ${LINE};font:700 13px/1.6 ${F};color:${MUT};white-space:nowrap">${esc(k)}</td><td valign="top" style="padding:9px 0;border-bottom:1px solid ${LINE};font:15px/1.6 ${F};color:${INK};word-break:break-word">${v}</td></tr>`).join('')}</table>`, '12px 0'));
    if (b.rule) rows.push(tr('', `20px 0 0;border-bottom:1px solid ${LINE}`));
  }
  rows.push(tr('', `32px 0 0;border-bottom:1px solid ${INK}`));
  rows.push(tr(`<div style="font:12px/1.7 ${F};color:${MUT}">${foot ? foot + '<br>' : ''}보내는 곳: 포스트오피스(AI 점령 지도 운영) · 문의 msgr@post-office.kr · <a href="${base}/privacy" style="color:${MUT};text-decoration:underline">개인정보처리방침</a></div>`, '12px 0 0'));
  return `<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>${esc(title)}</title></head>`
    + `<body style="margin:0;padding:0;background:${BG}"><div style="display:none;max-height:0;overflow:hidden;opacity:0">${esc(pre)}</div>`
    + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${BG}"><tr><td align="center" style="padding:24px 12px">`
    + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-top:6px solid ${PINK}"><tr><td style="padding:32px 28px 36px">`
    + `<table role="presentation" width="100%" cellpadding="0" cellspacing="0">${rows.join('')}</table></td></tr></table></td></tr></table></body></html>`;
}
export const link = (url, text, color = MUT) => `<a href="${esc(url)}" style="color:${color};text-decoration:underline">${esc(text)}</a>`;
export const textFoot = base => `\n\n보내는 곳: 포스트오피스(AI 점령 지도 운영) · 문의 msgr@post-office.kr · 개인정보처리방침 ${base}/privacy`;
