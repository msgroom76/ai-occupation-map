// 운영자용 집계 조회. 비밀값 STATS_KEY가 있어야 열린다.
// 키는 'Authorization: Bearer <키>' 헤더로 보내는 것을 권한다(주소창에 남지 않게). 예전처럼 ?k= 도 당분간 받는다.
// 더 안전하게는 Cloudflare Access로 /api/stats 를 보호한다(PIPELINE.md).
import { db, json, safeEq } from '../_db.js';
export async function onRequestGet({ request, env }) {
  const auth = (request.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  const k = auth || new URL(request.url).searchParams.get('k');
  if (!env.STATS_KEY || !safeEq(k, env.STATS_KEY)) return json({ ok: false }, 403);
  const d = await db(env); if (!d) return json({ ok: false, msg: 'DB 연결 전' }, 503);
  const ev = await d.prepare("SELECT name, label, SUM(n) AS n FROM events WHERE day >= date('now','-30 day') GROUP BY name, label ORDER BY n DESC LIMIT 300").all();
  const daily = await d.prepare("SELECT day, name, SUM(n) AS n FROM events WHERE day >= date('now','-30 day') GROUP BY day, name ORDER BY day").all();
  const subs = await d.prepare("SELECT COALESCE(status, 'unknown') AS status, COUNT(*) AS n FROM subscribers GROUP BY 1").all();
  const leads = await d.prepare("SELECT id, name, org, email, kind, msg, created FROM leads ORDER BY id DESC LIMIT 50").all();
  const fb = await d.prepare("SELECT COALESCE(sm, code) AS code, dir, COUNT(*) AS n, COUNT(DISTINCT COALESCE(ih, id) || substr(created, 1, 10)) AS people FROM feedback GROUP BY COALESCE(sm, code), dir ORDER BY 1").all();
  const fbn = await d.prepare("SELECT code, sm, title, dir, shown, note, created FROM feedback WHERE note IS NOT NULL AND note != '' ORDER BY id DESC LIMIT 50").all();
  const by = Object.fromEntries(subs.results.map(r => [r.status, r.n]));
  return json({ ok: true, feedback: fb.results, feedbackNotes: fbn.results, events: ev.results, daily: daily.results, subscribers: by.active || 0, subscriberStatus: by, leads: leads.results });
}
