// 1) 대표 주소는 aijido.org 하나로: www와 예전 pages.dev 주소로 들어오면 같은 경로로 영구 이동(301).
//    미리보기 배포(<해시>.ai-occupation-map.pages.dev)는 그대로 둔다.
// 2) 공개할 파일만 내보낸다: 저장소에는 파이프라인·도구·메일 원고·문서도 있는데, 이것들은 사이트로 열리지 않게 404로 막는다.
//    (큰 데이터 파일은 _routes.json에서 함수 호출을 건너뛰게 해 두었다 — 거기 적힌 경로도 여기 PUBLIC과 맞춰야 한다)
import { db } from './_db.js';
import { tick } from './_issue.js';
import { checkSources } from './_sources.js';
const MOVE = new Set(['www.aijido.org', 'ai-occupation-map.pages.dev']);
const PUBLIC_FILES = new Set(['/', '/index.html', '/404.html', '/robots.txt', '/sitemap.xml', '/og.png',
  '/city_index.png', '/city_roads.png', '/city_meta.json', '/config.json', '/feed.json', '/index.json',
  '/ksco_titles.json', '/ksco_soc_map.json', '/tasks.json', '/protect.json', '/favicon.ico', '/favicon.svg', '/apple-touch-icon.png',
  '/privacy', '/privacy.html', '/terms', '/terms.html', '/about', '/about.html', '/admin', '/admin.html',
  '/test', '/test.html', '/us_kr.json', '/labor.json',
  '/org', '/org.html', '/org_engine.js', '/org_bench.json']);
const PUBLIC_DIRS = ['/j/', '/w/', '/og/', '/mail/img/', '/img/', '/api/'];
const isPublic = p => PUBLIC_FILES.has(p) || PUBLIC_DIRS.some(d => p.startsWith(d)) || p === '/j' || p === '/w';

export async function onRequest(ctx) {
  const u = new URL(ctx.request.url);
  if (MOVE.has(u.hostname)) {
    u.hostname = 'aijido.org'; u.protocol = 'https:'; u.port = '';
    return Response.redirect(u.toString(), 301);
  }
  if (!isPublic(u.pathname)) {
    const nf = await ctx.env.ASSETS.fetch(new URL('/404.html', u.origin));
    return new Response(nf.body, { status: 404, headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-cache', 'x-robots-tag': 'noindex' } });
  }
  // 주간 메일 자동 흐름(승인 요청·이어서 발송)을 페이지 방문 때 조용히 돌린다. 페이지 응답은 기다리지 않는다.
  if (u.pathname === '/' && ctx.env.DB && ctx.env.MAIL_ENABLED === '1')
    ctx.waitUntil((async () => { try { await tick(ctx.env, await db(ctx.env), u.origin); } catch (e) { console.error(JSON.stringify({ at: 'tick', err: String(e) })); } })());
  // 자료 출처 새 판 확인: 하루 한 번, 사이트 방문 때 조용히(메일 설정과 무관)
  if (u.pathname === '/' && ctx.env.DB)
    ctx.waitUntil((async () => { try { await checkSources(ctx.env, await db(ctx.env), u.origin); } catch (e) { console.error(JSON.stringify({ at: 'sources', err: String(e) })); } })());
  return ctx.next();
}
