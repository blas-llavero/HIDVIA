const CACHE='hidvia-demo-v2';
self.addEventListener('install', e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/patient','/patient.html','/styles.css','/patient.js','/i18n.js','/icon.svg']))));
self.addEventListener('fetch',e=>{if(e.request.method==='GET'&&!e.request.url.includes('/api/')){e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));}});
