// "내 일과 비교하면?" 의견. 개인정보는 받지 않는다(직업 코드·방향·선택 메모만).
import { db, json, kst, clip } from '../_db.js';
const DIRS = new Set(['higher', 'same', 'lower']);
export async function onRequestPost({ request, env }) {
  let b = {}; try { b = await request.json(); } catch (e) { return json({ ok: false }, 400); }
  if (b.website) return json({ ok: true });
  const code = clip(b.code, 3), dir = clip(b.dir, 8);
  if (!/^\d{2,3}$/.test(code) || !DIRS.has(dir)) return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 400);
  const d = await db(env); if (!d) return json({ ok: false, msg: '잠시 후 다시 시도해 주세요.' }, 503);
  const sm = /^\d{3}$/.test(clip(b.sm, 3)) ? clip(b.sm, 3) : null;
  const shown = Number.isFinite(+b.shown) ? Math.max(0, Math.min(100, Math.round(+b.shown))) : null;
  await d.prepare("INSERT INTO feedback (code, sm, title, dir, shown, note, created) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)")
    .bind(code, sm, clip(b.title, 40) || null, dir, shown, clip(b.note, 300) || null, kst()).run();
  return json({ ok: true, msg: '고마워요. 의견은 직업별로 모아 매달 숫자를 점검할 때 살펴봐요.' });
}
