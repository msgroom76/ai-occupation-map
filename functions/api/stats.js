// 운영자용 집계 조회. 환경 변수 STATS_KEY와 같은 ?k= 값이 있어야 열린다.
import { db, json } from '../_db.js';
export async function onRequestGet({ request, env }) {
  const k = new URL(request.url).searchParams.get('k');
  if (!env.STATS_KEY || k !== env.STATS_KEY) return json({ ok: false }, 403);
  const d = await db(env); if (!d) return json({ ok: false, msg: 'DB 연결 전' }, 503);
  const ev = await d.prepare("SELECT name, label, SUM(n) AS n FROM events WHERE day >= date('now','-30 day') GROUP BY name, label ORDER BY n DESC LIMIT 300").all();
  const daily = await d.prepare("SELECT day, name, SUM(n) AS n FROM events WHERE day >= date('now','-30 day') GROUP BY day, name ORDER BY day").all();
  const subs = await d.prepare("SELECT COUNT(*) AS n FROM subscribers WHERE unsubscribed IS NULL").first();
  const leads = await d.prepare("SELECT id, name, org, email, kind, msg, created FROM leads ORDER BY id DESC LIMIT 50").all();
  const fb = await d.prepare("SELECT code, dir, COUNT(*) AS n FROM feedback GROUP BY code, dir ORDER BY code").all();
  const fbn = await d.prepare("SELECT code, sm, title, dir, shown, note, created FROM feedback WHERE note IS NOT NULL AND note != '' ORDER BY id DESC LIMIT 50").all();
  return json({ ok: true, feedback: fb.results, feedbackNotes: fbn.results, events: ev.results, daily: daily.results, subscribers: subs.n, leads: leads.results });
}
