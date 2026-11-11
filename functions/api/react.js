// 독자 반응(/news): 진격 소식마다 감정 한 번, 쟁점 소식마다 찬반 한 번. 개인정보는 받지 않는다.
// 받는 것: 소식 id, 고른 답, (고르면) 내 직업 중분류 코드. 중복 막기: 접속 주소를 그날만 쓰는 값으로 섞은 해시(ih)만 남기고 이틀 뒤 지운다.
// 공개: 소식마다 응답이 MIN_N명 이상일 때만 비율을 낸다. 응답은 지수·숫자에 절대 쓰지 않는다(참여한 독자의 반응일 뿐, 여론이 아님).
import { db, json, kst, clip, sameOrigin, ipHash, allow } from '../_db.js';
export const REACT_FROM = '2026-11-18';   // 개인정보처리방침 변경 시행일(2026-11-11 공지)부터 받는다
export const MIN_N = 30, MIN_GROUP = 10;
const OPT = { feel: ['hope', 'worry', 'meh', 'unsure'], stance: ['yes', 'no', 'cond', 'unsure'] };
const NID = /^[0-9A-Za-z][0-9A-Za-z._-]{5,119}$/;

export async function onRequestPost({ request, env }) {
  if (!sameOrigin(request)) return json({ ok: false }, 403);
  if (kst().slice(0, 10) < REACT_FROM && env.SURVEY_TEST !== '1') return json({ ok: false, msg: `반응은 ${+REACT_FROM.slice(5, 7)}월 ${+REACT_FROM.slice(8)}일부터 받아요.` }, 403);
  let b = {}; try { b = await request.json(); } catch (e) { return json({ ok: false }, 400); }
  if (b.website) return json({ ok: true });
  const nid = clip(b.id, 120), kind = clip(b.kind, 8), v = clip(b.v, 8), code = /^\d{2}$/.test(clip(b.code, 2)) ? clip(b.code, 2) : null;
  if (!NID.test(nid) || !OPT[kind] || !OPT[kind].includes(v)) return json({ ok: false }, 400);
  const d = await db(env); if (!d) return json({ ok: false, msg: '잠시 후 다시 시도해 주세요.' }, 503);
  const day = kst().slice(0, 10), ih = await ipHash(request, env, day);
  if (!ih) return json({ ok: false, msg: '잠시 후 다시 시도해 주세요.' }, 503);
  const dup = await d.prepare("SELECT 1 FROM reacts WHERE ih = ?1 AND nid = ?2").bind(ih, nid).first();
  if (dup) return json({ ok: true, dup: true });
  if (!(await allow(d, request, env, 'rx', 60, 20000))) return json({ ok: false, msg: '오늘은 반응을 충분히 받았어요. 내일 다시 부탁해요.' }, 429);
  await d.prepare("INSERT INTO reacts (nid, kind, v, code, created, ih) VALUES (?1, ?2, ?3, ?4, ?5, ?6)").bind(nid, kind, v, code, kst(), ih).run();
  return json({ ok: true });
}

// GET /api/react?ids=a,b,c (최대 40개) → { r: { id: { n, p?: {답: %}, g?: { 대분류: { n, p } } } } }
// n이 MIN_N 미만이면 n만. 대분류(직업 코드 앞자리)별 비율은 그 묶음 응답이 MIN_GROUP명 이상일 때만.
export async function onRequestGet({ request, env }) {
  const ids = (new URL(request.url).searchParams.get('ids') || '').split(',').map(x => clip(x, 120)).filter(x => NID.test(x)).slice(0, 40);
  if (!ids.length) return json({ ok: false }, 400);
  const d = await db(env); if (!d) return json({ ok: true, r: {}, min: MIN_N });
  const q = ids.map((_, i) => `?${i + 1}`).join(',');
  const rows = (await d.prepare(`SELECT nid, v, substr(code, 1, 1) AS g, COUNT(*) AS c FROM reacts WHERE nid IN (${q}) GROUP BY nid, v, g`).bind(...ids).all()).results || [];
  const R = {};
  for (const x of rows) {
    const o = R[x.nid] = R[x.nid] || { n: 0, t: {}, gs: {} };
    o.n += x.c; o.t[x.v] = (o.t[x.v] || 0) + x.c;
    if (x.g) { const g = o.gs[x.g] = o.gs[x.g] || { n: 0, t: {} }; g.n += x.c; g.t[x.v] = (g.t[x.v] || 0) + x.c; }
  }
  const pct = (t, n) => Object.fromEntries(Object.entries(t).map(([k, c]) => [k, Math.round(c / n * 100)]));
  const out = {};
  for (const [nid, o] of Object.entries(R)) {
    if (o.n < MIN_N) { out[nid] = { n: o.n }; continue; }
    const g = Object.fromEntries(Object.entries(o.gs).filter(([, x]) => x.n >= MIN_GROUP).map(([k, x]) => [k, { n: x.n, p: pct(x.t, x.n) }]));
    out[nid] = { n: o.n, p: pct(o.t, o.n), ...(Object.keys(g).length ? { g } : {}) };
  }
  return json({ ok: true, r: out, min: MIN_N, from: REACT_FROM }, 200);
}
