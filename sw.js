/* DOPE のオフライン対応（サービスワーカー）
   - ページ（HTML）と号の目録（JSON）は「ネット優先」：毎朝の更新をすぐ反映し、つながらないときだけ保存分を出す
   - 画像・フォント・地図データは「保存分を先に出し、裏で更新」：速く開くため
   キャッシュの中身を変えたいときは V の番号を上げる */
const V = "dope-v1";
const CORE = ["/", "/manifest.webmanifest", "/assets/icon-192.png", "/assets/apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(V).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

const withTimeout = (p, ms) => new Promise((ok, ng) => { const t = setTimeout(() => ng(new Error("timeout")), ms); p.then(r => { clearTimeout(t); ok(r); }, e => { clearTimeout(t); ng(e); }); });

async function networkFirst(req){
  const cache = await caches.open(V);
  try {
    const res = await withTimeout(fetch(req), 6000);
    if (res && res.ok) cache.put(req, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(req, {ignoreSearch: true});
    if (hit) return hit;
    if (req.mode === "navigate") { const home = await cache.match("/"); if (home) return home; }
    throw err;
  }
}
async function staleWhileRevalidate(req){
  const cache = await caches.open(V);
  const hit = await cache.match(req);
  const net = fetch(req).then(res => { if (res && (res.ok || res.type === "opaque")) cache.put(req, res.clone()); return res; }).catch(() => hit);
  return hit || net;
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const same = url.origin === self.location.origin;
  const isPage = req.mode === "navigate" || (same && (url.pathname.endsWith("/") || url.pathname.endsWith(".html") || url.pathname.endsWith(".json") || url.pathname.endsWith(".webmanifest")));
  if (same && isPage) { e.respondWith(networkFirst(req)); return; }
  const ext = /(^|\.)(fonts\.googleapis\.com|fonts\.gstatic\.com|cdn\.jsdelivr\.net|cdnjs\.cloudflare\.com)$/.test(url.hostname);
  if (same || ext) e.respondWith(staleWhileRevalidate(req));
});
