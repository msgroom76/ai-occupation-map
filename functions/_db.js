// D1 바인딩 이름: DB. 없으면 기록하지 않고 조용히 넘어간다.
export const SCHEMA = [
  "CREATE TABLE IF NOT EXISTS events (day TEXT NOT NULL, name TEXT NOT NULL, label TEXT NOT NULL DEFAULT '', n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (day, name, label))",
  "CREATE TABLE IF NOT EXISTS subscribers (email TEXT PRIMARY KEY, job TEXT, src TEXT, created TEXT NOT NULL, unsubscribed TEXT)",
  "CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, org TEXT, email TEXT NOT NULL, kind TEXT, msg TEXT, created TEXT NOT NULL)",
  "CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL, sm TEXT, title TEXT, dir TEXT NOT NULL, shown INTEGER, note TEXT, created TEXT NOT NULL)"
];
export async function db(env) {
  if (!env.DB) return null;
  if (!globalThis.__schemaOk) { await env.DB.batch(SCHEMA.map(s => env.DB.prepare(s))); globalThis.__schemaOk = true; }
  return env.DB;
}
export const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' } });
export const kst = () => new Date(Date.now() + 9 * 3600e3).toISOString().replace('Z', '+09:00');
export const clip = (s, n) => String(s ?? '').replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, n);
export const isEmail = e => /^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,24}$/.test(e);
