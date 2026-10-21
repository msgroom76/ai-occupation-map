// D1 바인딩 이름: DB. 없으면 기록하지 않고 조용히 넘어간다.
// 표 구조는 SCHEMA(처음 만들 때)와 MIGRATIONS(바뀐 것, 번호 순서대로 한 번씩)로 관리한다. 적용한 번호는 meta 표의 schema 값에 남는다.
export const SCHEMA = [
  "CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)",
  "CREATE TABLE IF NOT EXISTS events (day TEXT NOT NULL, name TEXT NOT NULL, label TEXT NOT NULL DEFAULT '', n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, name, label))",
  "CREATE TABLE IF NOT EXISTS subscribers (email TEXT PRIMARY KEY, job TEXT, src TEXT, created TEXT NOT NULL, unsubscribed TEXT)",
  "CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, org TEXT, email TEXT NOT NULL, kind TEXT, msg TEXT, created TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL, sm TEXT, title TEXT, dir TEXT NOT NULL, shown INTEGER, note TEXT, created TEXT NOT NULL, ih TEXT)"
];
// 2026-10-21: 구독 이중 확인(확인 메일)·수신 거부 토큰·동의 기록
export const MIGRATIONS = [
  [],                                                     // 1: 처음 구조
  ["ALTER TABLE subscribers ADD COLUMN status TEXT",      // 2: pending(확인 전) · active · unsub
   "ALTER TABLE subscribers ADD COLUMN token TEXT",
   "ALTER TABLE subscribers ADD COLUMN consent_at TEXT",
   "ALTER TABLE subscribers ADD COLUMN consent_ver TEXT",
   "ALTER TABLE subscribers ADD COLUMN confirmed_at TEXT",
   "ALTER TABLE subscribers ADD COLUMN unsub_at TEXT",
   // 이전 구독 신청은 확인 메일을 거치지 않았으므로 '확인 전'으로 둔다(첫 발송 전에 확인 메일부터 보낸다)
   "UPDATE subscribers SET status = CASE WHEN unsubscribed IS NULL THEN 'pending' ELSE 'unsub' END, unsub_at = unsubscribed WHERE status IS NULL",
   "CREATE UNIQUE INDEX IF NOT EXISTS sub_token ON subscribers(token)",
   "CREATE INDEX IF NOT EXISTS fb_ih_day ON feedback(ih, created)"]
];
async function migrate(DB) {
  await DB.batch(SCHEMA.map(s => DB.prepare(s)));
  const row = await DB.prepare("SELECT v FROM meta WHERE k = 'schema'").first();
  let v = row ? +row.v : 0;
  if (!row) {  // meta가 새로 생긴 경우: 이미 있는 표에 status 열이 있는지로 판단
    const cols = (await DB.prepare("PRAGMA table_info(subscribers)").all()).results.map(c => c.name);
    v = cols.includes('status') ? MIGRATIONS.length : 1;
  }
  for (let i = v; i < MIGRATIONS.length; i++) {
    for (const s of MIGRATIONS[i]) { try { await DB.prepare(s).run(); } catch (e) { if (!/duplicate column/i.test(String(e))) throw e; } }
  }
  await DB.prepare("INSERT INTO meta (k, v) VALUES ('schema', ?1) ON CONFLICT(k) DO UPDATE SET v = excluded.v").bind(String(MIGRATIONS.length)).run();
}
export async function db(env) {
  if (!env.DB) return null;
  if (!globalThis.__schemaOk) { await migrate(env.DB); globalThis.__schemaOk = true; }
  await maintain(env.DB);
  return env.DB;
}
// 보관 기간 지키기(처리방침과 같은 기간). 하루에 한 번, 그날 첫 요청 때 실행한다(Pages에는 정해진 시각 실행 기능이 없어서).
async function maintain(DB) {
  const day = kst().slice(0, 10);
  if (globalThis.__cleanDay === day) return;
  const r = await DB.prepare("SELECT v FROM meta WHERE k = 'cleanup'").first();
  globalThis.__cleanDay = day;
  if (r && r.v === day) return;
  await DB.batch([
    DB.prepare("UPDATE feedback SET ih = NULL WHERE ih IS NOT NULL AND created < date('now', '+9 hours', '-2 day')"),       // 접속 해시: 이틀
    DB.prepare("UPDATE feedback SET note = NULL WHERE note IS NOT NULL AND created < date('now', '+9 hours', '-1 year')"),   // 의견 메모: 1년
    DB.prepare("DELETE FROM subscribers WHERE status = 'unsub' AND COALESCE(unsub_at, unsubscribed) < date('now', '+9 hours', '-30 day')"), // 해지: 30일 뒤 삭제
    DB.prepare("DELETE FROM subscribers WHERE status = 'pending' AND COALESCE(consent_at, created) < date('now', '+9 hours', '-30 day')"),  // 확인 안 한 신청: 30일 뒤 삭제
    DB.prepare("DELETE FROM leads WHERE created < date('now', '+9 hours', '-1 year')"),                                       // 문의: 1년
    DB.prepare("DELETE FROM events WHERE day < date('now', '+9 hours', '-400 day')"),
    DB.prepare("INSERT INTO meta (k, v) VALUES ('cleanup', ?1) ON CONFLICT(k) DO UPDATE SET v = excluded.v").bind(day)
  ]);
}
export const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
export const html = (title, body, status = 200) => new Response(`<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>${title} · AI 점령 지도</title><style>:root{--bg:#f3f3f6;--ink:#1c1c1e;--ink2:rgba(60,60,67,.78);--hot:#a3206f}@media (prefers-color-scheme:dark){:root{--bg:#0b0c10;--ink:#f5f5f7;--ink2:rgba(235,235,245,.7);--hot:#ff8ccd}}body{margin:0;background:var(--bg);color:var(--ink);font-family:"Pretendard Variable",Pretendard,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;font-size:15px;line-height:1.6;word-break:keep-all}main{max-width:560px;margin:0 auto;padding:40px 20px}h1{font-size:24px;letter-spacing:-.03em;border-top:2px solid var(--ink);padding-top:14px}p{color:var(--ink2)}a{color:inherit}.b{display:inline-flex;align-items:center;min-height:44px;padding:0 18px;border:1px solid var(--ink);background:var(--ink);color:var(--bg);font:inherit;font-weight:600;text-decoration:none;cursor:pointer}</style></head><body><main><p><a href="/"><b style="color:var(--hot)">AI</b> 점령 지도</a></p><h1>${title}</h1>${body}</main></body></html>`, { status, headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' } });
export const kst = () => new Date(Date.now() + 9 * 3600e3).toISOString().replace('Z', '+09:00');
export const clip = (s, n) => String(s ?? '').replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, n);
export const isEmail = e => /^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,24}$/.test(e);
export const token = () => [...crypto.getRandomValues(new Uint8Array(24))].map(x => x.toString(16).padStart(2, '0')).join('');
// 다른 사이트에서 몰래 보내는 요청 막기: 우리 사이트(또는 미리보기·로컬)에서 온 요청만 받는다.
export function sameOrigin(request) {
  const o = request.headers.get('origin');
  if (!o) return false;
  try {
    const h = new URL(o).hostname, self = new URL(request.url).hostname;
    return h === self || h === 'aijido.org' || h.endsWith('.ai-occupation-map.pages.dev') || h === 'localhost' || h === '127.0.0.1';
  } catch (e) { return false; }
}
// 길이가 같을 때 걸리는 시간이 같은 비교(비밀값 비교용)
export function safeEq(a, b) {
  a = String(a || ''); b = String(b || '');
  if (!a || !b || a.length !== b.length) return false;
  let r = 0; for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}
