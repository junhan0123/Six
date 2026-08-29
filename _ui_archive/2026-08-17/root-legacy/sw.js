/* 小6 · 移动伴随端 service worker（离线优先，PWA）
 * - install：预缓存核心静态资源
 * - fetch：同源 GET 走 cache-first，离线可用
 */
const CACHE = "zz-mobile-v1";
const ASSETS = [
  "mobile-app.html",
  "mobile-app.js",
  "device-client.js",
  "manifest.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((c) => c.addAll(ASSETS).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req)
        .then((res) => {
          try {
            if (res && res.ok && new URL(req.url).origin === self.location.origin) {
              const copy = res.clone();
              caches.open(CACHE).then((c) => c.put(req, copy));
            }
          } catch (e) {
            /* 忽略缓存异常 */
          }
          return res;
        })
        .catch(() => cached);
    })
  );
});
