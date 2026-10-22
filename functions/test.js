// 물때 테스트(/test). 공유 링크(/test?j=31&k=312)로 들어오면 미리보기(og) 제목·그림을 그 직업의 물때로 바꿔서 내보낸다.
// 숫자 계산은 페이지와 같다(지도 데이터 + 주간 지수 보정). 페이지 내용 자체는 그대로.
const ST = [['발목', 0], ['무릎', .2], ['허리', .35], ['가슴', .5], ['목까지', .65]];
let CACHE = null;
async function data(env, origin) {
  if (CACHE && Date.now() - CACHE.at < 10 * 60e3) return CACHE;
  const [cm, idx] = await Promise.all(['/city_meta.json', '/index.json'].map(p => env.ASSETS.fetch(new URL(p, origin)).then(r => r.json())));
  const W = idx.weeks || []; CACHE = { cm, adj: (W[W.length - 1] || {}).adj || {}, at: Date.now() }; return CACHE;
}
export async function onRequestGet({ request, env, next }) {
  const res = await next(), u = new URL(request.url), code = u.searchParams.get('j');
  if (!code || !/^\d{2}$/.test(code) || !(res.headers.get('content-type') || '').includes('text/html')) return res;
  try {
    const { cm, adj } = await data(env, u.origin), J = cm.jobs.find(j => j.code === code); if (!J) return res;
    const k = (u.searchParams.get('k') || '').slice(0, 3), sm = /^\d{3}$/.test(k) && k.startsWith(code) && cm.sm[k] && (J.smalls || []).length > 1 ? cm.sm[k] : null;
    const p = (r, y) => { const [m, kk, K] = cm.R[r]; return K / (1 + Math.exp(-kk * (y - m + (adj[r] || 0)))); };
    const D = sm || J, w = sm ? sm.w : J.w41; let a = 0; for (const r in w) a += w[r] * p(r, 2026);
    const v = Math.min(.99, D.cal * a); let s = 0; while (s < 4 && v >= ST[s + 1][1]) s++;
    const name = sm ? ((J.smalls.find(x => x[0] === k) || [, J.name])[1]) : J.name;
    const title = `${name}, AI 물때는 지금 '${ST[s][0]}' (${Math.round(v * 100)}%)`;
    const img = `${u.origin}/img/water/og-s${s + 1}.png`, url = `${u.origin}/test?j=${code}${sm ? '&k=' + k : ''}`;
    const set = (sel, val) => ({ element(e) { e.setAttribute('content', val); } });
    return new HTMLRewriter()
      .on('meta[property="og:title"]', set(0, title)).on('meta[property="og:image"]', set(0, img)).on('meta[property="og:url"]', set(0, url))
      .on('meta[property="og:description"]', set(0, '사라지는 날이 아니라, 차오르는 높이를 재요. 내 직업의 물때도 확인해 보세요.'))
      .on('title', { element(e) { e.setInnerContent(`${title} · 내 직업은 언제 소멸될까?`); } })
      .transform(res);
  } catch (e) { return res; }
}
