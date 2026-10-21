// 대표 주소는 aijido.org 하나로: www와 예전 pages.dev 주소로 들어오면 같은 경로로 영구 이동(301).
// 미리보기 배포(<해시>.ai-occupation-map.pages.dev)는 그대로 둔다.
const MOVE = new Set(['www.aijido.org', 'ai-occupation-map.pages.dev']);
export async function onRequest(ctx) {
  const u = new URL(ctx.request.url);
  if (MOVE.has(u.hostname)) {
    u.hostname = 'aijido.org'; u.protocol = 'https:'; u.port = '';
    return Response.redirect(u.toString(), 301);
  }
  return ctx.next();
}
