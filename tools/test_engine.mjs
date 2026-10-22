// 웹 계산 엔진(org_engine.js)과 보고서 계산(tools/org_report.py)이 같은 숫자를 내는지 확인한다.
// 직무별 인건비는 파이썬 쪽이 반올림을 두 번 해(환산 전후) 0.01억까지 차이를 허용한다.
// 저장소 루트에서: python3 tools/build_report.py 로 metrics.json을 만든 뒤 node tools/test_engine.mjs
import fs from 'fs';
import { engine } from '../org_engine.js';
const J = f => JSON.parse(fs.readFileSync(f, 'utf8'));
const data = { cm: J('city_meta.json'), idx: J('index.json'), labor: J('labor.json'), protect: J('protect.json'), uskr: J('us_kr.json'), bench: J('org_bench.json') };
const E = engine(data); let bad = 0;
const close = (a, b, tol) => Math.abs(a - b) <= tol;
for (const id of ['janghan', 'musinsa', 'sfood', 'prain']) {
  const C = J(`reports/${id}.json`), M = J(`reports/out/${id}/metrics.json`);
  const ix = Object.fromEntries(C.roles.map((r, i) => [r.id, i]));
  const ind = fs.existsSync(`reports/${id}_peers.json`) ? J(`reports/${id}_peers.json`).industry[0] : null;
  const res = E.run({ roles: C.roles.map(r => ({ name: r.name, code: r.code, n: r.n })), office: (C.office || []).map(x => ix[x]), payroll: C.payroll_actual, industry: ind });
  const o = res.org, mo = M.org, errs = [];
  for (const [k, tol] of [['e26', 6e-5], ['e30', 6e-5], ['fte', .06], ['fte30', .06], ['cost', .06], ['sub', 6e-4], ['kr26', 6e-5]]) if (!close(o[k], mo[k], tol)) errs.push(`${k} ${o[k]} vs ${mo[k]}`);
  for (const r of res.rows) {
    const m = M.roles.find(x => x.name === r.name);
    for (const [k, mk, tol] of [['e26', 'e26', 6e-5], ['sub', 'sub', 6e-4], ['cost', 'cost_m', .012]]) if (!close(r[k], m[mk], tol)) errs.push(`${r.name}.${k} ${r[k]} vs ${m[mk]}`);
    if (r.tasks.map(t => t.id).join() !== m.tasks.map(t => t.id).join()) errs.push(`${r.name}.tasks`);
  }
  if (o.tasks.map(t => t.id).join() !== mo.tasks.map(t => t.id).join()) errs.push('org.tasks');
  if (o.ind) { const ref = J('reports/industry_bench.json').industry; const k = Object.keys(ref).find(x => x.startsWith(ind + '.')); if (!close(o.ind.e26, ref[k].e26, 2e-3)) errs.push(`industry ${o.ind.e26} vs ${ref[k].e26} (참고: 보고서 쪽은 저장된 값)`); }
  console.log(`${id}: ${errs.length ? '불일치 ' + errs.length : '일치'}  e26 ${(o.e26 * 100).toFixed(2)}% FTE ${o.fte.toFixed(1)} 인건비 ${o.cost.toFixed(1)}억` + (o.ind ? ` 업종 ${(o.ind.e26 * 100).toFixed(1)}%` : ''));
  errs.slice(0, 8).forEach(e => console.log('   ', e)); bad += errs.length;
}
process.exit(bad ? 1 : 0);
