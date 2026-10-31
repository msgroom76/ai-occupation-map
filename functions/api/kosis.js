// 공개 통계(KOSIS) 중계: 사이트 서버가 KOSIS_KEY로 고용 통계표를 읽어 그대로 돌려준다. 열쇠는 밖으로 나가지 않는다.
// 남용 막기: 기관·표 번호를 고용 통계로 한정(고용노동부 118, 국가데이터처 101의 지역별고용조사·경제활동인구조사), 결과는 하루 동안 D1에 저장,
//           저장되지 않은 새 요청은 하루 80번까지.
// GET /api/kosis                         → 연결 상태(열쇠 유무, 오늘 쓴 횟수)
// GET /api/kosis?org=118&tbl=DT_..&type=meta  → 표 이름·수록 기간
// GET /api/kosis?org=118&tbl=DT_..&type=data  → 가장 최근 시점 자료(모든 항목·분류)
import { db, json, kst } from '../_db.js';
const OK_TBL = { '118': /^DT_118N_[A-Z0-9_]{2,16}$/, '101': /^DT_1(ES3|DA7|DE7)[A-Z0-9_]{1,16}$/ };
const DAY_CAP = 80;
const getMeta = async (d, k) => (await d.prepare("SELECT v FROM meta WHERE k = ?1").bind(k).first())?.v || null;
const setMeta = (d, k, v) => d.prepare("INSERT INTO meta (k, v) VALUES (?1, ?2) ON CONFLICT(k) DO UPDATE SET v = excluded.v").bind(k, v).run();

async function kosis(env, url) {
  const r = await fetch(url + '&apiKey=' + encodeURIComponent(env.KOSIS_KEY), { signal: AbortSignal.timeout(12000), headers: { accept: 'application/json' } });
  const t = await r.text(); let j; try { j = JSON.parse(t); } catch (e) { j = null; }
  // KOSIS가 보낸 글을 그대로 돌려주지 않는다(오류 글에 요청 주소·열쇠가 섞여 있을 수 있어서). 열쇠는 지우고, 원문은 로그에만.
  const hide = s => { const k = env.KOSIS_KEY || ''; let o = String(s || ''); if (k) { o = o.split(k).join('***').split(encodeURIComponent(k)).join('***'); } return o.replace(/apiKey=[^&\s"']*/gi, 'apiKey=***').slice(0, 200); };
  if (!j) { try { j = JSON.parse(t.replace(/([{,])\s*([A-Za-z_]\w*)\s*:/g, '$1"$2":')); } catch (e) { console.error(JSON.stringify({ at: 'kosis', status: r.status, body: hide(t) })); return { err: `KOSIS 응답을 읽지 못함(${r.status})` }; } }
  if (j && !Array.isArray(j) && (j.err || j.errMsg)) return { err: `KOSIS: ${hide(j.errMsg || j.err).slice(0, 120)}` };
  return { rows: j };
}

export async function onRequestGet(ctx) {
  try { return await handle(ctx); } catch (e) { console.error(JSON.stringify({ at: 'kosis', err: String(e && e.name || e) })); return json({ ok: false, msg: 'KOSIS 조회 중 오류가 났어요. 잠시 후 다시 시도해 주세요.' }, 502); }
}
async function handle({ request, env }) {
  const u = new URL(request.url), org = u.searchParams.get('org') || '', tbl = u.searchParams.get('tbl') || '', type = u.searchParams.get('type') || '';
  const d = await db(env); const today = kst().slice(0, 10);
  const used = d ? +((await getMeta(d, 'kosis_day')) || '').split('|')[1] || 0 : 0;
  const usedToday = d && ((await getMeta(d, 'kosis_day')) || '').startsWith(today) ? used : 0;
  if (!tbl) return json({ ok: !!env.KOSIS_KEY, key: !!env.KOSIS_KEY, usedToday, cap: DAY_CAP });
  if (!env.KOSIS_KEY) return json({ ok: false, msg: 'KOSIS_KEY가 설정되지 않았어요.' }, 503);
  if (!OK_TBL[org] || !OK_TBL[org].test(tbl) || !['meta', 'data'].includes(type)) return json({ ok: false, msg: '허용하지 않는 표예요.' }, 400);
  const ck = `kosis:${org}:${tbl}:${type}`;
  if (d) { const c = await getMeta(d, ck); if (c) { const o = JSON.parse(c); if (o.day === today) return json({ ok: true, cached: true, ...o }); } }
  if (d) { if (usedToday >= DAY_CAP) return json({ ok: false, msg: '오늘 조회 한도에 걸렸어요. 내일 다시 해 주세요.' }, 429); await setMeta(d, 'kosis_day', `${today}|${usedToday + 1}`); }
  const base = 'https://kosis.kr/openapi';
  let out;
  if (type === 'meta') {
    const [t1, t2] = await Promise.all([kosis(env, `${base}/statisticsData.do?method=getMeta&type=TBL&format=json&orgId=${org}&tblId=${tbl}`),
                                        kosis(env, `${base}/statisticsData.do?method=getMeta&type=PRD&format=json&orgId=${org}&tblId=${tbl}`)]);
    if (t1.err) return json({ ok: false, msg: t1.err }, 502);
    out = { day: today, tbl, name: (t1.rows || [])[0]?.TBL_NM || null, eng: (t1.rows || [])[0]?.TBL_NM_ENG || null, periods: (t2.rows || []).map(r => r.PRD_DE || r.prdDe).filter(Boolean) };
  } else {
    // 분류 개수를 모르므로 1~4개를 차례로 시도한다(KOSIS는 분류 수가 맞아야 응답한다)
    let res = null;
    for (const n of [2, 1, 3, 4]) {
      const objs = Array.from({ length: n }, (_, i) => `&objL${i + 1}=ALL`).join('');
      res = await kosis(env, `${base}/Param/statisticsParameterData.do?method=getList&format=json&jsonVD=Y&orgId=${org}&tblId=${tbl}&itmId=ALL&prdSe=Y&newEstPrdCnt=1${objs}`);
      if (!res.err && Array.isArray(res.rows) && res.rows.length) break;
    }
    if (!res || res.err || !Array.isArray(res.rows)) return json({ ok: false, msg: res?.err || '자료가 비어 있어요.' }, 502);
    out = { day: today, tbl, rows: res.rows.slice(0, 3000).map(r => ({ prd: r.PRD_DE, c1: r.C1_NM, c2: r.C2_NM, c3: r.C3_NM, item: r.ITM_NM, unit: r.UNIT_NM, v: r.DT })) };
  }
  if (d) await setMeta(d, ck, JSON.stringify(out));
  return json({ ok: true, ...out });
}
