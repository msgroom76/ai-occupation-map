// 현직자 설문(/test 결과 화면의 '이 일을 하고 계세요?'). 개인정보는 받지 않는다.
// 받는 것: 직업 코드, 주요 업무 5개마다 'AI로 하는 몫'(0·25·50·75·100), 줄어든 시간 구간, 경력 구간, 응답에 걸린 초.
// 중복 막기: 접속 주소를 그날만 쓰는 값으로 섞은 해시(ih)만 남기고 이틀 뒤 지운다(_db.js). 같은 해시는 직업마다 하루 1번, 전체 하루 5번.
// 공개: 직업별 응답이 15명 이상일 때만 평균을 낸다(GET). 응답은 사이트 숫자를 자동으로 바꾸지 않는다 — 따로 '현직자 응답'으로 보여 주고 채점에 쓴다.
import { db, json, kst, clip, sameOrigin, ipHash, allow } from '../_db.js';
export const SURVEY_FROM = '2026-11-09';   // 개인정보처리방침 변경 시행일(2026-11-02 공지)부터 받는다
export const MIN_N = 15;
const RID = /^[A-D]\d{1,2}$/, VALS = new Set([0, 25, 50, 75, 100]);
const key = c => /^\d{3}$/.test(c) ? 'sm' : 'code';

export async function onRequestPost({ request, env }) {
  if (!sameOrigin(request)) return json({ ok: false }, 403);
  if (kst().slice(0, 10) < SURVEY_FROM && env.SURVEY_TEST !== '1') return json({ ok: false, msg: `설문은 ${SURVEY_FROM.slice(5).replace('-', '월 ')}일부터 받아요.` }, 403);
  let b = {}; try { b = await request.json(); } catch (e) { return json({ ok: false }, 400); }
  if (b.website) return json({ ok: true });
  const code = clip(b.code, 2), sm = /^\d{3}$/.test(clip(b.sm, 3)) ? clip(b.sm, 3) : null;
  const ans = Array.isArray(b.ans) ? b.ans.slice(0, 5).map(a => ({ r: clip(a?.r, 3), w: Math.max(0, Math.min(1, +a?.w || 0)), v: +a?.v })) : [];
  if (!/^\d{2}$/.test(code) || ans.length < 3 || ans.some(a => !RID.test(a.r) || !VALS.has(a.v))) return json({ ok: false, msg: '답이 빠졌어요. 업무마다 하나씩 골라 주세요.' }, 400);
  const saved = [0, 1, 2, 3].includes(+b.saved) ? +b.saved : null, tenure = [0, 1, 2, 3].includes(+b.tenure) ? +b.tenure : null;
  const secs = Math.max(0, Math.min(3600, Math.round(+b.secs || 0)));
  const d = await db(env); if (!d) return json({ ok: false, msg: '잠시 후 다시 시도해 주세요.' }, 503);
  const day = kst().slice(0, 10), ih = await ipHash(request, env, day);
  if (!ih) return json({ ok: false, msg: '잠시 후 다시 시도해 주세요.' }, 503);
  const k = sm || code;
  const dup = await d.prepare("SELECT 1 FROM survey WHERE ih = ?1 AND COALESCE(sm, code) = ?2 AND substr(created, 1, 10) = ?3").bind(ih, k, day).first();
  if (dup) return json({ ok: true, msg: '이 직업 응답은 이미 받았어요. 고마워요.' });
  if (!(await allow(d, request, env, 'sv', 5, 3000))) return json({ ok: false, msg: '오늘은 응답을 충분히 받았어요. 내일 다시 부탁해요.' }, 429);
  const z = ans.reduce((s, a) => s + a.w, 0), wt = a => z > 0 ? a.w / z : 1 / ans.length;   // 이 직업에서 그 업무가 차지하는 비중으로 가중
  const share = Math.round(ans.reduce((s, a) => s + wt(a) * a.v, 0));
  const ok = secs >= 15 ? 1 : 0;   // 너무 빨리 끝낸 응답은 저장하되 집계에서 뺀다
  await d.prepare("INSERT INTO survey (code, sm, ans, share, saved, tenure, secs, ok, created, ih) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)")
    .bind(code, sm, JSON.stringify(ans.map(a => [a.r, Math.round(a.w * 1000) / 1000, a.v])), share, saved, tenure, secs, ok, kst(), ih).run();
  return json({ ok: true, msg: '고마워요. 같은 일을 하는 분이 15명 모이면 평균을 이 화면에 보여 드려요.' });
}

// GET /api/survey?k=331 → { n, share?, tasks?, saved? } (n이 15 미만이면 n만)
export async function onRequestGet({ request, env }) {
  const k = clip(new URL(request.url).searchParams.get('k'), 3);
  if (!/^\d{2,3}$/.test(k)) return json({ ok: false }, 400);
  const d = await db(env); if (!d) return json({ ok: true, n: 0 });
  const rows = (await d.prepare(`SELECT ans, share, saved FROM survey WHERE ok = 1 AND ${key(k) === 'sm' ? 'sm' : 'code'} = ?1 ORDER BY id DESC LIMIT 2000`).bind(k).all()).results || [];
  const n = rows.length;
  if (n < MIN_N) return json({ ok: true, n, min: MIN_N, from: SURVEY_FROM }, 200);
  const T = {};
  for (const r of rows) for (const [rid, , v] of JSON.parse(r.ans)) { (T[rid] = T[rid] || [0, 0]); T[rid][0] += v; T[rid][1]++; }
  const S = [0, 0, 0, 0]; let sn = 0; for (const r of rows) if (r.saved != null) { S[r.saved]++; sn++; }
  return json({ ok: true, n, min: MIN_N, share: Math.round(rows.reduce((s, r) => s + r.share, 0) / n),
    tasks: Object.fromEntries(Object.entries(T).filter(([, x]) => x[1] >= MIN_N).map(([rid, x]) => [rid, Math.round(x[0] / x[1])])),
    saved: sn ? S.map(x => Math.round(x / sn * 100)) : null });
}
