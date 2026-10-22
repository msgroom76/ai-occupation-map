// 자료 출처 관리: 사이트 숫자가 기대는 자료마다 '지금 쓰는 판'과 확인 방법을 적어 두고,
// 하루 한 번(사이트 방문 때 조용히) 새 판이 나왔는지 API·공개 페이지로 확인한다. 결과는 운영 화면과 승인 요청 메일에 보인다.
// 자료를 실제로 새 판으로 바꾼 뒤에는 여기의 have(와 due)를 고친다.
//
// 확인 방법(check)
//   onet  : O*NET 데이터베이스 안내 페이지의 최신 판 번호 (열쇠 필요 없음)
//   hf    : Hugging Face 데이터셋 API의 release_YYYY_MM_DD 폴더 중 가장 새것 (열쇠 필요 없음)
//   gh    : GitHub 저장소 API의 마지막 반영 시각, 처음 본 값을 기준으로 바뀌면 알림 (열쇠 필요 없음)
//   kosis : KOSIS 오픈API의 수록 기간 중 가장 새것 (Cloudflare 비밀값 KOSIS_KEY 필요)
//   law   : 국가법령정보 오픈API로 protect.json의 법령이 개정됐는지 (Cloudflare 환경변수 LAW_OC 필요, 하루 15개씩 돌아가며)
//   없음  : 날짜(due)가 되면 '확인할 때'로 알림. every개월마다 다시 알림
import { kst } from './_db.js';

export const SOURCES = [
  { id: 'aei', name: 'Anthropic 경제지수(실제 사용 확인)', used: '직업 화면의 실제 사용 확인 값', have: 'release_2026_03_24', every: 6, due: '2026-09-24',
    check: { type: 'hf', repo: 'Anthropic/EconomicIndex' }, url: 'https://huggingface.co/datasets/Anthropic/EconomicIndex',
    how: '새 release 폴더의 job_exposure를 pipeline/inputs/dl2/에 넣고 run.sh로 다시 계산' },
  { id: 'onet', name: 'O*NET 데이터베이스(업무·작업 목록)', used: '업무 41개 비중, 직업별 세부 작업', have: '30.0', every: 6, due: '2026-08-31',
    check: { type: 'onet' }, url: 'https://www.onetcenter.org/database.html',
    how: '새 판 텍스트 묶음에서 extract_onet.py로 쓰는 부분만 뽑아 dl_onet/에 넣고 run.sh. 업무 비중이 조금 바뀔 수 있어 변경 기록 필요' },
  { id: 'lfs', name: '지역별고용조사 직업 소분류 취업자', used: '지도 넓이(직업별 일하는 사람 수)', have: '202502', haveLabel: '2025년 하반기', every: 6, due: '2026-10-15',
    check: { type: 'kosis', org: '101', tbl: 'DT_1ES3B32J' }, url: 'https://kosis.kr/statHtml/statHtml.do?orgId=101&tblId=DT_1ES3B32J',
    how: '새 반기를 내려받아 dl_lfs/occ_YYYYhN.json으로 넣고 run.sh. 상반기 결과는 보통 10월, 하반기는 4월에 나와요' },
  { id: 'union', name: '직종별 노조 가입률(고용형태별근로실태조사)', used: "쟁점 탭 '노조 가입률'", have: '2025', every: 12, due: '2027-05-01',
    check: { type: 'kosis', org: '118', tbl: 'DT_118N_LCE310' }, url: 'https://kosis.kr/statHtml/statHtml.do?orgId=118&tblId=DT_118N_LCE310',
    how: 'KOSIS에서 직종별 표를 CSV로 내려받아 대화창에 첨부하면 protect.json union을 바꿔요' },
  { id: 'union_org', name: '노동조합 조직률(조직현황)', used: 'protect.json 전체 조직률', have: '2024', every: 12, due: '2026-12-15',
    url: 'https://www.index.go.kr/unify/idx-info.do?idxCd=1511', how: '보통 12월에 전년도 값이 나와요. 숫자 하나만 바꾸면 돼요' },
  { id: 'laws', name: '자격·업무 독점 법령과 AI 기본법', used: "쟁점 탭 '법으로 정한 보호막'", have: 'protect.json 2026-10-22 기준', every: 3, due: '2027-01-22',
    check: { type: 'law' }, url: 'https://www.law.go.kr',
    how: '개정된 법의 해당 조항을 읽고 protect.json의 조항·설명을 고치거나 그대로 둔다' },
  { id: 'gpts', name: 'GPTs are GPTs 노출도(미국 연구)', used: '노출도 절반(미국 연구 값)', have: '공개본', every: 0,
    check: { type: 'gh', repo: 'openai/GPTs-are-GPTs' }, url: 'https://github.com/openai/GPTs-are-GPTs',
    how: '논문 고정 자료라 보통 바뀌지 않아요. 바뀌면 바뀐 내용을 보고 반영 여부를 정해요' },
  { id: 'ilo', name: 'ILO 생성형 AI 노출 점수', used: '노출도 절반(국제노동기구 값)', have: 'WP140 (2025)', every: 12, due: '2026-05-20',
    url: 'https://www.ilo.org/publications', how: 'ILO가 새 점수를 내면 dl2/에 넣고 run.sh. 지수 전체가 움직이므로 변경 기록 필요' },
  { id: 'oews', name: '미국 직업별 고용(OEWS 2021.5)', used: '미국 직업을 한국 직업으로 묶을 때 가중치', have: '2021.5', every: 0,
    url: 'https://www.bls.gov/oes/', how: 'GPTs are GPTs 자료에 들어 있는 고정본이라 바꾸지 않아요(바꾸면 방법이 바뀜)' },
  { id: 'konet', name: '고용24 직업명 ↔ 직업분류 매핑', used: '검색(직업 이름 6,713개)', have: '2026.04.09', every: 12, due: '2027-04-09',
    url: 'https://www.work24.go.kr', how: '새 매핑을 dl_konet/konet.csv로 넣고 run.sh' },
  { id: 'ksco_isco', name: 'KSCO ↔ ISCO 공식 연계표', used: '한국 직업 ↔ 국제 분류 연결', have: '2025.11.03', every: 12, due: '2026-11-03',
    url: 'https://kssc.mods.go.kr', how: '새 연계표를 ksco_isco/에 넣고 run.sh' },
];

const UA = { 'user-agent': 'aijido.org source check (+https://aijido.org)', accept: 'application/json,text/html' };
const get = (url, type = 'json') => fetch(url, { headers: UA, signal: AbortSignal.timeout(8000) }).then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r[type](); });
const getMeta = async (d, k) => (await d.prepare("SELECT v FROM meta WHERE k = ?1").bind(k).first())?.v || null;
const setMeta = (d, k, v) => d.prepare("INSERT INTO meta (k, v) VALUES (?1, ?2) ON CONFLICT(k) DO UPDATE SET v = excluded.v").bind(k, v).run();
const jget = async (d, k) => { try { return JSON.parse(await getMeta(d, k) || 'null'); } catch (e) { return null; } };
// KOSIS 기간 표기를 비교할 수 있게: 2025 → 2025, 202502/20252/2025.2 → 202502
const prd = s => { const t = String(s || '').replace(/\D/g, ''); return t.length === 5 ? t.slice(0, 4) + '0' + t[4] : t; };

async function checkOne(env, d, s, origin) {
  const c = s.check || {};
  if (c.type === 'onet') {
    const h = await get('https://www.onetcenter.org/database.html', 'text');
    const v = [...h.matchAll(/O\*NET (\d+\.\d+) Database/g)].map(m => m[1]).sort((a, b) => parseFloat(b) - parseFloat(a))[0];
    if (!v) throw new Error('판 번호를 찾지 못함'); return { latest: v };
  }
  if (c.type === 'hf') {
    const j = await get(`https://huggingface.co/api/datasets/${c.repo}`);
    const v = [...new Set((j.siblings || []).map(x => x.rfilename.split('/')[0]).filter(x => /^release_\d{4}_\d{2}_\d{2}$/.test(x)))].sort().pop();
    if (!v) throw new Error('release 폴더가 없음'); return { latest: v };
  }
  if (c.type === 'gh') {
    const j = await get(`https://api.github.com/repos/${c.repo}`);
    const base = await getMeta(d, 'src_base:' + s.id); if (!base) await setMeta(d, 'src_base:' + s.id, j.pushed_at);
    return { latest: j.pushed_at, base: base || j.pushed_at };
  }
  if (c.type === 'kosis') {
    if (!env.KOSIS_KEY) throw new Error('KOSIS_KEY가 없어 자동 확인 꺼짐');
    const j = await get(`https://kosis.kr/openapi/statisticsData.do?method=getMeta&type=PRD&format=json&apiKey=${encodeURIComponent(env.KOSIS_KEY)}&orgId=${c.org}&tblId=${c.tbl}`);
    const rows = Array.isArray(j) ? j : []; if (!rows.length) throw new Error(j && (j.errMsg || j.err) ? `KOSIS: ${j.errMsg || j.err}` : '수록 기간이 비어 있음');
    const v = rows.map(r => prd(r.PRD_DE || r.prdDe)).filter(Boolean).sort((a, b) => a.length - b.length || (a < b ? -1 : 1)).pop();
    return { latest: v };
  }
  if (c.type === 'law') {
    if (!env.LAW_OC) throw new Error('LAW_OC가 없어 자동 확인 꺼짐');
    const P = await env.ASSETS.fetch(new URL('/protect.json', origin)).then(r => r.json());
    const names = [...new Set([...P.licenses.flatMap(l => l.law.split(' · ')), '인공지능 발전과 신뢰 기반 조성 등에 관한 기본법'])].sort();
    const per = 15, day = Math.floor(Date.now() / 864e5), start = (day * per) % names.length;
    const pick = Array.from({ length: Math.min(per, names.length) }, (_, i) => names[(start + i) % names.length]);
    const prev = (await jget(d, 'src:laws')) || {}; const changed = (prev.changed || []).filter(x => !pick.includes(x.name)); let n = 0;
    for (const name of pick) {
      try {
        const j = await get(`https://www.law.go.kr/DRF/lawSearch.do?OC=${encodeURIComponent(env.LAW_OC)}&target=law&type=JSON&display=20&query=${encodeURIComponent(name)}`);
        const nm = t => String(t || '').replace(/[·ㆍ・]/g, '·').replace(/\s/g, ''); const L = [].concat(j?.LawSearch?.law || []).find(x => nm(x['법령명한글']) === nm(name) || nm(x['법령약칭명']) === nm(name)); if (!L) continue; n++;
        const k = 'law:' + name, base = await getMeta(d, k), mst = L['법령일련번호'];
        if (!base) await setMeta(d, k, mst);
        else if (base !== mst) changed.push({ name, mst, ef: L['시행일자'], pub: L['공포일자'], kind: L['제개정구분명'] });
      } catch (e) { /* 한 법이 실패해도 나머지는 계속 */ }
    }
    if (!n) throw new Error('법령 API 응답 없음(LAW_OC·도메인 등록 확인)');
    return { latest: changed.length ? `개정 ${changed.length}건` : '변경 없음', changed, total: names.length, seen: n };
  }
  return null;
}

// 하루 한 번(또는 운영 화면의 [지금 확인]) 자동 확인할 수 있는 자료를 모두 확인한다
export async function checkSources(env, d, origin, force = false) {
  if (!d) return;
  const today = kst().slice(0, 10);
  if (!force) {
    if (globalThis.__srcTick && Date.now() - globalThis.__srcTick < 30 * 60e3) return;
    globalThis.__srcTick = Date.now();
    if (await getMeta(d, 'src_day') === today) return;
  }
  await setMeta(d, 'src_day', today);
  for (const s of SOURCES) {
    if (!s.check) continue;
    let r; try { r = { ok: true, ...(await checkOne(env, d, s, origin)) }; } catch (e) { r = { ok: false, err: String(e.message || e).slice(0, 160) }; }
    r.at = kst();
    await setMeta(d, 'src:' + s.id, JSON.stringify(r));
  }
}

const addM = (iso, m) => { const t = new Date(iso.slice(0, 10) + 'T00:00:00Z'); t.setUTCMonth(t.getUTCMonth() + m); return t.toISOString().slice(0, 10); };
// 상태: new(새 판 나옴) · due(확인할 때) · soon(30일 안) · wait(날짜 전, 자동 확인 없음) · ok(자동 확인으로 최신) · fixed(바꾸지 않는 고정본)
export async function sourceStatus(env, d) {
  const today = kst().slice(0, 10), out = [];
  for (const s of SOURCES) {
    const r = d ? await jget(d, 'src:' + s.id) : null, ack = d ? await jget(d, 'src_ack:' + s.id) : null;
    let st = 'ok', why = '', next = null;
    const autoOk = s.check && r && r.ok;
    if (autoOk && s.check.type === 'law') { if ((r.changed || []).length) { st = 'new'; why = r.changed.map(x => `${x.name}(${x.kind || '개정'}, ${x.ef ? x.ef.slice(0, 4) + '.' + x.ef.slice(4, 6) + '.' + x.ef.slice(6) + ' 시행' : ''})`).join(', '); } }
    else if (autoOk) {
      const fresh = s.check.type === 'gh' ? r.latest !== r.base : (s.check.type === 'kosis' ? prd(r.latest) > prd(s.have) : r.latest !== s.have);
      if (fresh && !(ack && ack.latest === r.latest)) { st = 'new'; why = `새 판 ${r.latest}`; }
    }
    if (st !== 'new' && !autoOk) {
      if (!s.every) st = 'fixed';
      else {
        next = ack && ack.at >= (s.due || '') ? addM(ack.at, s.every) : (s.due || addM(today, s.every));
        st = today >= next ? 'due' : (addM(today, 1) >= next ? 'soon' : 'wait');
        if (st === 'due') why = s.check ? '자동 확인이 안 돼서 직접 확인할 때예요' : '새 판이 나왔는지 직접 확인할 때예요';
      }
    }
    out.push({ id: s.id, name: s.name, used: s.used, have: s.haveLabel || s.have, url: s.url, how: s.how, auto: s.check ? s.check.type : null,
      st, why, next, at: r ? r.at : null, latest: r && r.ok ? r.latest : null, err: r && !r.ok ? r.err : null, ack: ack ? ack.at : null });
  }
  return out;
}

// [확인했어요]: 지금 본 새 판(또는 날짜 알림)을 넘긴다. 실제로 반영했다면 위 SOURCES의 have를 고쳐야 다음 판부터 다시 알린다.
export async function ackSource(env, d, id) {
  const s = SOURCES.find(x => x.id === id); if (!s || !d) return false;
  const r = await jget(d, 'src:' + id);
  if (s.check && s.check.type === 'law' && r && r.changed) { for (const x of r.changed) await setMeta(d, 'law:' + x.name, x.mst); r.changed = []; r.latest = '변경 없음'; await setMeta(d, 'src:' + id, JSON.stringify(r)); }
  if (s.check && s.check.type === 'gh' && r && r.ok) await setMeta(d, 'src_base:' + id, r.latest);
  await setMeta(d, 'src_ack:' + id, JSON.stringify({ at: kst().slice(0, 10), latest: r && r.ok ? r.latest : null }));
  return true;
}
