// 행동 집계: 날짜·이벤트·라벨별 횟수만 센다. 개인 식별 정보는 받지 않는다.
import { db, json, kst, clip, sameOrigin, allow } from '../_db.js';
const NAMES = new Set(['search', 'job', 'save', 'share', 'map', 'news', 'compare', 'task', 'sub', 'lead', 'jobpage', 'fold', 'menu', 'fb', 'tab', 'tk', 'join', 'test', 'org']);
export async function onRequestPost({ request, env }) {
  if (!sameOrigin(request)) return json({ ok: false }, 403);
  let b = {}; try { b = JSON.parse(await request.text() || '{}'); } catch (e) {}
  const name = clip(b.n, 20), label = clip(b.l, 40);
  if (!NAMES.has(name)) return json({ ok: false }, 400);
  const d = await db(env); if (!d) return json({ ok: true, stored: false }, 202);
  if (!(await allow(d, request, env, 'ev', 300, 30000))) return json({ ok: true, stored: false }, 202);   // 한 접속 하루 300번, 전체 3만 번까지만 센다
  await d.prepare("INSERT INTO events (day, name, label, n) VALUES (?1, ?2, ?3, 1) ON CONFLICT(day, name, label) DO UPDATE SET n = n + 1")
    .bind(kst().slice(0, 10), name, label).run();
  return json({ ok: true });
}
