// 운영자 로그인: 비밀번호 대신 운영자 메일(ADMIN_EMAIL 또는 MAIL_REPLY_TO)로 로그인 링크를 보내고,
// 링크를 누르면 30일짜리 서명 쿠키를 준다. 예전 방식(Authorization: Bearer <STATS_KEY>)도 계속 된다.
import { safeEq } from './_db.js';
import { sign } from './_issue.js';
export const COOKIE = 'aimap_admin';
export async function makeSession(env, days = 30) {
  const exp = Math.floor(Date.now() / 1000) + days * 86400;
  return `${exp}.${await sign(env, 'session|' + exp)}`;
}
export async function authed(request, env) {
  if (!env.STATS_KEY) return false;
  const bearer = (request.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (bearer && safeEq(bearer, env.STATS_KEY)) return true;
  const c = (request.headers.get('cookie') || '').split(/;\s*/).find(x => x.startsWith(COOKIE + '='));
  if (!c) return false;
  const [exp, sig] = c.slice(COOKIE.length + 1).split('.');
  if (!exp || !sig || +exp < Date.now() / 1000) return false;
  return safeEq(await sign(env, 'session|' + exp), sig);
}
