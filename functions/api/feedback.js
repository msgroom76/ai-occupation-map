// "내 일과 비교하면?" 의견. 개인정보는 받지 않는다(직업 코드·방향·선택 메모만).
// 가짜·반복 의견 막기: 접속 주소를 그날만 쓰는 값으로 섞어 해시(ih)로만 남긴다(원래 주소는 저장하지 않음, 날이 바뀌면 같은 사람인지 알 수 없음).
// 같은 해시는 직업마다 하루 1번, 전체 하루 10번까지만 받는다. 의견은 숫자를 자동으로 바꾸지 않고, 점검 대상을 고르는 신호로만 쓴다.
import { db, json, kst, clip } from '../_db.js';
const DIRS = new Set(['higher', 'same', 'lower']);
async function hashIp(ip, day, salt) {
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${salt}|${day}|${ip}`));
  return [...new Uint8Array(b)].slice(0, 12).map(x => x.toString(16).padStart(2, '0')).join('');
}
export async function onRequestPost({ request, env }) {
  let b = {}; try { b = await request.json(); } catch (e) { return json({ ok: false }, 400); }
  if (b.website) return json({ ok: true });
  const code = clip(b.code, 3), dir = clip(b.dir, 8);
  if (!/^\d{2,3}$/.test(code) || !DIRS.has(dir)) return json({ ok: false, msg: '요청 형식이 잘못됐어요.' }, 400);
  const d = await db(env); if (!d) return json({ ok: false, msg: '잠시 후 다시 시도해 주세요.' }, 503);
  if (!globalThis.__fbIh) { try { await d.prepare("ALTER TABLE feedback ADD COLUMN ih TEXT").run(); } catch (e) { } globalThis.__fbIh = true; }
  const day = kst().slice(0, 10), ip = request.headers.get('cf-connecting-ip') || 'na';
  const ih = await hashIp(ip, day, env.STATS_KEY || 'aimap');
  const sm = /^\d{3}$/.test(clip(b.sm, 3)) ? clip(b.sm, 3) : null, key = sm || code;
  const c = await d.prepare("SELECT COUNT(*) AS all_n, SUM(CASE WHEN COALESCE(sm, code) = ?2 THEN 1 ELSE 0 END) AS same_n FROM feedback WHERE ih = ?1 AND substr(created, 1, 10) = ?3").bind(ih, key, day).first();
  if (c && c.same_n > 0) return json({ ok: true, msg: '이 직업에 대한 의견은 이미 받았어요. 고마워요.' });
  if (c && c.all_n >= 10) return json({ ok: false, msg: '오늘은 의견을 충분히 받았어요. 내일 다시 남겨 주세요.' }, 429);
  const shown = Number.isFinite(+b.shown) ? Math.max(0, Math.min(100, Math.round(+b.shown))) : null;
  await d.prepare("INSERT INTO feedback (code, sm, title, dir, shown, note, created, ih) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)")
    .bind(code, sm, clip(b.title, 40) || null, dir, shown, clip(b.note, 300) || null, kst(), ih).run();
  return json({ ok: true, msg: '고마워요. 의견은 직업별로 모아 매달 숫자를 점검할 때 살펴봐요.' });
}
