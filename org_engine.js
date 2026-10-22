// 조직 AI 노출 계산 엔진(브라우저·Node 공용). tools/org_report.py와 같은 식이다 — 두 쪽 숫자가 같은지 tools/test_engine.mjs가 확인한다.
// 입력: data = {cm: city_meta.json, idx: index.json, labor: labor.json, protect: protect.json, uskr: us_kr.json, bench: org_bench.json}
//       org  = {roles: [{name, code(소분류 3자리 또는 직업명 사전의 4자리), n}], office?: [역할 번호], payroll?: 억 원, opProfit?: 억 원, industry?: 'C'}
// 출력: 직무별 노출도·대체형 비중·FTE·인건비, 조직 합계, 업종 비교, 두 집단, 노조 가입률(한·미).
export const SUB = new Set(['A5', 'B2', 'B9', 'C1', 'C2', 'C3', 'C4', 'C5', 'C9', 'D15', 'D3']);
export const TIER = ['낮음', '보통', '상당', '높음', '매우 높음'];
const CUT = [0, .2, .35, .5, .65];
export const stage = v => { let s = 0; while (s < 4 && v >= CUT[s + 1]) s++; return s; };

export function engine(data) {
  const { cm, idx } = data, R = cm.R, SM = cm.sm, JC = {};
  for (const j of cm.jobs) JC[j.code] = j;
  const wk = (idx && idx.weeks) || [], ADJ = (wk[wk.length - 1] || {}).adj || {};
  const p = (r, y) => { const [m, k, K] = R[r]; return K / (1 + Math.exp(-k * (y - m + (ADJ[r] || 0)))); };
  // 직무 코드 → 업무 가중치. 소분류(3자리)가 있으면 그것, 없으면 중분류(2자리)
  const prof = code => {
    const c3 = String(code).slice(0, 3);
    if (SM[c3]) return { w: SM[c3].w, cal: SM[c3].cal, sm: c3, mid: c3.slice(0, 2) };
    const j = JC[c3.slice(0, 2)]; if (!j) return null;
    return { w: j.w41, cal: j.cal, sm: null, mid: c3.slice(0, 2) };
  };
  const occ = (P, y) => { let s = 0; for (const r in P.w) s += P.w[r] * p(r, y); return Math.min(.99, P.cal * s); };
  const split = (P, y = 2026) => { let s = 0, a = 0; for (const r in P.w) { const v = P.w[r] * p(r, y); if (SUB.has(r)) s += v; else a += v; } return s / Math.max(s + a, 1e-9); };
  const tasks = (P, y = 2026, n = 4) => Object.keys(P.w).map(r => [P.w[r] * p(r, y) * P.cal, r])
    .sort((a, b) => b[0] - a[0] || (a[1] < b[1] ? 1 : a[1] > b[1] ? -1 : 0)).slice(0, n)
    .map(([x, r]) => ({ id: r, name: cm.RN[r][0], share: x, type: SUB.has(r) ? '대체형' : '보완형' }));
  const WS = cm.jobs.reduce((s, j) => s + j.ws, 0);
  const kr = y => cm.jobs.reduce((s, j) => s + j.ws * occ({ w: j.w41, cal: j.cal }, y), 0) / WS;
  // 직업 대분류별 전국 평균(업종 평균 계산에 씀)
  const major = y => { const a = {}, b = {}; for (const j of cm.jobs) { const k = j.code[0]; a[k] = (a[k] || 0) + j.ws * occ({ w: j.w41, cal: j.cal }, y); b[k] = (b[k] || 0) + j.ws; } const o = {}; for (const k in a) o[k] = a[k] / b[k]; return o; };
  const smName = c3 => { const j = JC[c3.slice(0, 2)]; const s = j && (j.smalls || []).find(x => x[0] === c3); return s ? s[1] : null; };

  function run(org) {
    const LB = data.labor.wage.major, UN = (data.protect.union || {}).major || {}, UK = data.uskr;
    const rows = [], skipped = [];
    org.roles.forEach((r, i) => {
      const n = Math.max(0, Math.round(+r.n || 0)); const P = r.code ? prof(r.code) : null;
      if (!P || !n) { skipped.push({ i, name: r.name, n, why: !P ? 'code' : 'n' }); return; }
      const mj = P.mid[0], e26 = occ(P, 2026), e30 = occ(P, 2030), wage = (LB[mj] && LB[mj].wage && LB[mj].wage.all) || 0;
      const ug = UK.us[UK.map[P.mid]];
      rows.push({ i, name: r.name || smName(P.sm || '') || P.mid, code: P.sm || P.mid, sm: P.sm, smName: P.sm ? smName(P.sm) : null, n, e26, e30, stage: stage(e26), stage30: stage(e30),
        sub: split(P), tasks: tasks(P), fte: n * e26, fte30: n * e30, cost: n * e26 * wage * 12 / 1e5, wage,
        unionKr: (UN[mj] || {}).all ?? null, unionUs: ug ? ug.union : null, usGroup: UK.map[P.mid] || null, _P: P });
    });
    const N = rows.reduce((s, r) => s + r.n, 0);
    const o = { n: N, roles: rows.length, skipped };
    if (!N) return { org: o, rows };
    o.e26 = rows.reduce((s, r) => s + r.n * r.e26, 0) / N; o.e30 = rows.reduce((s, r) => s + r.n * r.e30, 0) / N;
    o.kr26 = kr(2026); o.kr30 = kr(2030);
    o.fte = rows.reduce((s, r) => s + r.fte, 0); o.fte30 = rows.reduce((s, r) => s + r.fte30, 0);
    o.payrollEst = rows.reduce((s, r) => s + r.n * r.wage * 12 / 1e5, 0);
    o.cost = rows.reduce((s, r) => s + r.cost, 0); o.payroll = o.payrollEst; o.payrollBasis = 'est';
    if (+org.payroll > 0) { const k = org.payroll / Math.max(o.payrollEst, 1e-9); rows.forEach(r => r.cost *= k); o.cost *= k; o.payroll = +org.payroll; o.payrollBasis = 'actual'; }
    o.sub = rows.reduce((s, r) => s + r.fte * r.sub, 0) / Math.max(o.fte, 1e-9);
    o.stage = stage(o.e26); o.stage30 = stage(o.e30);
    const mix = {}; rows.forEach(r => { const k = r.code[0]; mix[k] = (mix[k] || 0) + r.n; }); for (const k in mix) mix[k] /= N; o.mix = mix;
    const agg = {}; rows.forEach(r => { for (const t in r._P.w) agg[t] = (agg[t] || 0) + r.n * r._P.w[t] * p(t, 2026) * r._P.cal; });
    o.tasks = Object.entries(agg).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([t, v]) => ({ id: t, name: cm.RN[t][0], fte: v, type: SUB.has(t) ? '대체형' : '보완형' }));
    // 같은 소분류로 묶여 같은 값이 나오는 직무
    const byCode = {}; rows.forEach(r => (byCode[r.code] = byCode[r.code] || []).push(r.name)); o.same = Object.values(byCode).filter(v => v.length > 1);
    // 두 집단: 지정이 없으면 대분류 1~3(관리자·전문가·사무)과 그 외
    const off = org.office ? new Set(org.office) : null;
    const inA = r => off ? off.has(r.i) : '123'.includes(r.code[0]);
    o.groups = [rows.filter(inA), rows.filter(r => !inA(r))].map(S => { const n = S.reduce((s, r) => s + r.n, 0), f = S.reduce((s, r) => s + r.fte, 0), f30 = S.reduce((s, r) => s + r.fte30, 0); return { n, fte: f, fte30: f30, e: n ? f / n : 0, e30: n ? f30 / n : 0, roles: S.map(r => r.i) }; });
    // 업종 비교: 업종 직업 구성 × 대분류 전국 평균(이번 주 보정 반영)
    const B = data.bench && org.industry && data.bench.industry[org.industry];
    if (B) { const m26 = major(2026), m30 = major(2030); let a = 0, b = 0, w = 0; for (const k in B.mix) { a += B.mix[k] * (m26[k] || 0); b += B.mix[k] * (m30[k] || 0); w += B.mix[k]; } o.ind = { code: org.industry, name: B.name, e26: a / w, e30: b / w, mix: B.mix }; }
    if (+org.opProfit) o.opProfit = +org.opProfit;
    rows.forEach(r => delete r._P);
    return { org: o, rows };
  }
  return { run, prof, occ, smName };
}
